"""The three `ac agentic capabilities` commands.

`start` keeps the API contract and the delivery key intact. `list` and `get`
mirror the two read endpoints. All three sit on one Typer group, so one file
holds them.

Staging serves no `/api/v1/agentic/` path until the cutover, so the audit for
this group runs against a branch API.
"""

import json

import pytest

from tests.test_agentic_runs import SAMPLE_RUN

ARGS = [
    "agentic",
    "capabilities",
    "start",
    "company.search",
    "--contract-version",
    "1",
    "--input",
    '{"query":"acme"}',
    "--idempotency-key",
    "delivery-42",
]
PATH = "/api/v1/agentic/capabilities/company.search/runs"


@pytest.mark.parametrize(
    "outcome,status",
    [
        ("started", "queued"),
        ("duplicate", "succeeded"),
        ("started", "waiting"),
        ("started", "failed"),
    ],
)
def test_start_preserves_request_and_run_response(invoke, mock_api, outcome, status):
    run = {
        **SAMPLE_RUN,
        "outcome": outcome,
        "status": status,
        "capability_id": "company.search",
        "contract_version": 1,
    }
    route = mock_api.post(PATH).respond(200, json=run)
    result = invoke([*ARGS, "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == run
    request = route.calls[0].request
    assert json.loads(request.content) == {"contract_version": 1, "input": {"query": "acme"}}
    assert request.headers["Idempotency-Key"] == "delivery-42"


def test_human_response_shows_capability_and_status(invoke, mock_api):
    mock_api.post(PATH).respond(
        200,
        json={
            **SAMPLE_RUN,
            "status": "waiting",
            "capability_id": "company.search",
            "contract_version": 1,
        },
    )
    result = invoke(ARGS)
    assert result.exit_code == 0, result.output
    assert "company.search" in result.output
    assert "waiting" in result.output


@pytest.mark.parametrize("flag", ["--contract-version", "--input", "--idempotency-key"])
def test_required_flags_cannot_default(invoke, mock_api, flag):
    args = ARGS.copy()
    index = args.index(flag)
    del args[index : index + 2]
    result = invoke(args)
    assert result.exit_code == 2
    assert not mock_api.calls


@pytest.mark.parametrize(
    "flag,value",
    [
        ("--input", '{"query":"\\ud800"}'),
        ("--input", "[]"),
        ("--input", "null"),
        ("--input", "{"),
        ("--input", ""),
        ("--input", '{"limit":NaN}'),
        ("--input", '{"limit":Infinity}'),
        ("--idempotency-key", " "),
        ("--idempotency-key", "x" * 201),
        ("--idempotency-key", "line\nbreak"),
        ("--idempotency-key", "é"),
    ],
)
def test_bad_local_input_is_a_json_error_without_http(invoke, mock_api, flag, value):
    args = ARGS.copy()
    args[args.index(flag) + 1] = value
    result = invoke([*args, "--json"])
    assert result.exit_code == 2, result.output
    assert json.loads(result.output)["error"] is True
    assert not mock_api.calls


@pytest.mark.parametrize("value", ["0", "-1", "1.5", "true"])
def test_version_is_a_positive_integer(invoke, mock_api, value):
    args = ARGS.copy()
    args[args.index("--contract-version") + 1] = value
    assert invoke(args).exit_code == 2
    assert not mock_api.calls


@pytest.mark.parametrize(
    "status,code,exit_code",
    [
        (400, "invalid_key", 1),
        (403, "capability_unauthorized", 4),
        (404, "capability_not_found", 3),
        (409, "capability_unavailable", 5),
        (409, "idempotency_conflict", 5),
        (409, "contract_version_conflict", 5),
        (413, "input_too_large", 1),
        (422, "invalid_input", 2),
        (429, "budget_denied", 1),
        (503, "principal_unavailable", 1),
    ],
)
def test_api_errors_keep_code_and_semantic_exit(invoke, mock_api, status, code, exit_code):
    detail = {"code": code}
    mock_api.post(PATH).respond(status, json={"detail": detail})
    result = invoke([*ARGS, "--json"])
    assert result.exit_code == exit_code, result.output
    assert json.loads(result.output) == {"error": True, "status_code": status, "detail": detail}


# ---------------------------------------------------------------------------
# The read half. `ac agentic capabilities list` and `get` mirror the two read
# endpoints; the start tests above cover the third route of the same group.
# ---------------------------------------------------------------------------

BASE = "/api/v1/agentic/capabilities"

AVAILABLE = {
    "capability_id": "company.search",
    "availability": "available",
    "name": "Company Search",
    "description": "Finds companies and returns selectable references.",
    "contract_version": 1,
    "input_schema": {
        "type": "object",
        "properties": {"sources": {"type": "array"}},
        "additionalProperties": False,
    },
    "output_schema": {
        "type": "object",
        "properties": {"items": {"type": "array"}},
        "additionalProperties": False,
    },
    "required_scopes": ["run.start", "crm.get_company"],
    "executor_type": "workflow",
}

UNAVAILABLE = {
    "capability_id": "people.enrich",
    "availability": "unavailable",
    "reason": "not_installed",
}


def test_capabilities_list(invoke, mock_api):
    mock_api.get(BASE).respond(200, json={"items": [AVAILABLE]})

    result = invoke(["agentic", "capabilities", "list"])

    assert result.exit_code == 0
    assert "company.search" in result.output
    assert "Capabilities (1)" in result.output


def test_capabilities_list_asks_for_available_only_by_default(invoke, mock_api):
    """The default hides a refusal, so the common read carries none."""
    route = mock_api.get(BASE).respond(200, json={"items": []})

    invoke(["agentic", "capabilities", "list"])

    assert route.called
    assert route.calls[0].request.url.params.multi_items() == [("available_only", "true")]


def test_capabilities_list_all_asks_for_every_record(invoke, mock_api):
    """`--all` is the only way to read why a capability is missing."""
    route = mock_api.get(BASE).respond(200, json={"items": [UNAVAILABLE]})

    result = invoke(["agentic", "capabilities", "list", "--all"])

    assert route.calls[0].request.url.params.multi_items() == [("available_only", "false")]
    assert result.exit_code == 0
    assert "not_installed" in result.output


def test_capabilities_list_sends_no_page_argument(invoke, mock_api):
    """The catalogue is not paginated. A cursor or a limit would 422."""
    route = mock_api.get(BASE).respond(200, json={"items": []})

    invoke(["agentic", "capabilities", "list"])

    sent = dict(route.calls[0].request.url.params.multi_items())
    assert "cursor" not in sent
    assert "limit" not in sent


def test_capabilities_list_explains_an_empty_default_answer(invoke, mock_api):
    """An empty list carries no reason, so the command names the flag.

    The same empty list answers a caller with no run right and a tenant that
    installed nothing. Without the hint a reader reads it as "none exist".
    """
    mock_api.get(BASE).respond(200, json={"items": []})

    result = invoke(["agentic", "capabilities", "list"])

    assert result.exit_code == 0
    assert "--all" in result.output


def test_capabilities_list_json_carries_both_schemas(invoke, mock_api):
    """The table drops the schemas, so `--json` is the only way to read them."""
    mock_api.get(BASE).respond(200, json={"items": [AVAILABLE]})

    result = invoke(["agentic", "capabilities", "list", "--json"])

    assert result.exit_code == 0
    row = json.loads(result.output)["items"][0]
    assert row["input_schema"]["properties"] == {"sources": {"type": "array"}}
    assert row["output_schema"]["properties"] == {"items": {"type": "array"}}
    assert row["required_scopes"] == ["run.start", "crm.get_company"]


def test_capabilities_get(invoke, mock_api):
    route = mock_api.get(f"{BASE}/company.search").respond(200, json=AVAILABLE)

    result = invoke(["agentic", "capabilities", "get", "company.search"])

    assert route.called
    assert result.exit_code == 0
    assert "Company Search" in result.output
    # The scopes are a list, so `print_detail` cannot render them.
    assert "crm.get_company" in result.output


def test_capabilities_get_renders_an_unavailable_record(invoke, mock_api):
    """An unavailable record carries no contract, and that is not an error."""
    mock_api.get(f"{BASE}/people.enrich").respond(200, json=UNAVAILABLE)

    result = invoke(["agentic", "capabilities", "get", "people.enrich"])

    assert result.exit_code == 0
    assert "not_installed" in result.output


def test_capabilities_get_json_answers_the_whole_record(invoke, mock_api):
    mock_api.get(f"{BASE}/company.search").respond(200, json=AVAILABLE)

    result = invoke(["agentic", "capabilities", "get", "company.search", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == AVAILABLE


def test_capabilities_get_reports_an_unknown_id(invoke, mock_api):
    """404 is a client fault, and the vocabulary is case-sensitive.

    The exit code is asserted, and not `!= 0`. `_EXIT_CODES` maps 404 to 3, so
    a script tells an unknown ID from the 403 below without reading stdout.
    """
    mock_api.get(f"{BASE}/Company.Search").respond(404, json={"detail": "unknown capability id"})

    result = invoke(["agentic", "capabilities", "get", "Company.Search"])

    assert result.exit_code == 3
    assert "unknown capability id" in result.output


def test_capabilities_get_reports_a_refusal(invoke, mock_api):
    """403 means this caller may not start it, whatever the tenant installed.

    `_EXIT_CODES` maps 403 to 4. A refusal and an unknown ID exit differently,
    because one is fixed by asking for a right and the other by fixing the ID.
    """
    mock_api.get(f"{BASE}/company.search").respond(
        403, json={"detail": "this caller may not start this capability"}
    )

    result = invoke(["agentic", "capabilities", "get", "company.search"])

    assert result.exit_code == 4
    assert "may not start" in result.output


def test_capabilities_get_encodes_a_reserved_character(invoke, mock_api):
    """A slash in the argument must not become a second path segment.

    `capabilities start` encodes its ID and this command must agree. Unencoded,
    `a/b` reads a two-segment path that names another route.

    ⚠️ **The assertion reads `raw_path` and not `path`.** httpx decodes `path`,
    and respx matches on the decoded form, so a route registered for `a%2Fb`
    matches an unencoded request too. Only the raw bytes tell the two apart.
    """
    route = mock_api.get(url__regex=r".*/capabilities/.*").respond(
        404, json={"detail": "unknown capability id"}
    )

    result = invoke(["agentic", "capabilities", "get", "a/b"])

    assert route.called
    assert route.calls[0].request.url.raw_path.endswith(b"/capabilities/a%2Fb")
    assert result.exit_code == 3


def test_capabilities_get_reports_a_server_refusal(invoke, mock_api):
    """`list` guarded its 5xx path and `get` did not.

    The stdout assertion is what separates a handled refusal from a crash. A
    `MarkupError` inside the renderer also exits 1, and it prints nothing.
    """
    mock_api.get(f"{BASE}/company.search").respond(
        500, json={"detail": "the rights read did not answer"}
    )

    result = invoke(["agentic", "capabilities", "get", "company.search"])

    assert result.exit_code == 1
    assert "the rights read did not answer" in result.output


def test_capabilities_list_reports_a_server_refusal(invoke, mock_api):
    """Exit 1 and the reason on stdout.

    The stdout assertion is what separates a handled refusal from a crash. A
    `MarkupError` inside the renderer also exits 1, and it prints nothing, so
    the exit code alone answers the same for both.
    """
    mock_api.get(BASE).respond(500, json={"detail": "the rights read did not answer"})

    result = invoke(["agentic", "capabilities", "list"])

    assert result.exit_code == 1
    assert "the rights read did not answer" in result.output


def test_capabilities_list_renders_foreign_text_as_text(invoke, mock_api):
    """A product name is server text, and square brackets are not markup.

    `print_table` sends every value through `as_text`. A name that rich read
    as markup would raise `MarkupError` and print nothing.
    """
    named = dict(AVAILABLE, name="Company Search [beta]")
    mock_api.get(BASE).respond(200, json={"items": [named]})

    result = invoke(["agentic", "capabilities", "list"])

    assert result.exit_code == 0
    assert "beta" in result.output


def test_capabilities_list_all_does_not_repeat_the_hint(invoke, mock_api):
    """A caller who already asked for the reasons must not be told to ask.

    `--all` with an empty answer means this tenant reads no record at all. The
    default-only guard is what keeps the hint off that path.
    """
    mock_api.get(BASE).respond(200, json={"items": []})

    result = invoke(["agentic", "capabilities", "list", "--all"])

    assert result.exit_code == 0
    assert "--all" not in result.output
