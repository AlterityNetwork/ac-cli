"""Tests for the agentic product capability commands.

`ac agentic capabilities` reads `/api/v1/agentic/capabilities`, which answers
the five stable product IDs of one tenant. Staging serves no `/api/v1/agentic/`
path until the cutover, so the audit for this group runs against a branch API.

The design cases are ac-docs, the file
engineering/system-design/agentic-platform/products/capability-scenarios.md,
row A14.
"""

import json

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
