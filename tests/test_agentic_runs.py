"""Tests for the agentic platform run commands.

`ac agentic runs` sits beside `ac agents runs` and replaces none of it. The two
stacks are branch isolated until the cutover, so the alias swap is Phase 7.
"""

import json
import uuid

import pytest

SAMPLE_RUN = {
    "id": "11111111-1111-4111-8111-111111111111",
    "kind": "agent",
    "definition_id": "22222222-2222-4222-8222-222222222222",
    "definition_name": "Weekly digest",
    "status": "running",
    "waiting_on": None,
    "source": "api",
    "root_run_id": "11111111-1111-4111-8111-111111111111",
    "parent_run_id": None,
    "created_at": "2026-08-23T10:00:00Z",
    "started_at": "2026-08-23T10:00:01Z",
    "ended_at": None,
    "input": {"q": "hello"},
    "result": None,
    "error": None,
    "usage": {
        "input_tokens": 10,
        "output_tokens": 20,
        "total_tokens": 30,
        "cost_cents": 4,
    },
    "child_count": 0,
    "pending_approval_id": None,
    "outcome": "started",
}

# Every key SpanNodeModel declares, and no key it does not. A hand-written
# fixture that omits a nullable field hides how the API really answers: the
# model always emits the key, so a test on a missing key tests nothing.
SAMPLE_SPAN = {
    "span_id": "33333333-3333-4333-8333-333333333333",
    "parent_span_id": None,
    "kind": "tool",
    "name": "crm.search",
    "status": "ok",
    "started_at": "2026-08-23T10:00:02Z",
    "updated_at": "2026-08-23T10:00:02Z",
    "duration_ms": 120,
    "usage_id": None,
    "no_call_reason": None,
    "error": None,
}


# --- start -----------------------------------------------------------------


def test_runs_start(invoke, mock_api):
    route = mock_api.post("/api/v1/agentic/runs").respond(200, json=SAMPLE_RUN)
    result = invoke(
        [
            "agentic",
            "runs",
            "start",
            "--definition",
            SAMPLE_RUN["definition_id"],
            "--input",
            '{"q": "hello"}',
        ]
    )
    assert result.exit_code == 0
    assert SAMPLE_RUN["id"] in result.output
    body = json.loads(route.calls[0].request.content)
    assert body == {
        "definition_id": SAMPLE_RUN["definition_id"],
        "input": {"q": "hello"},
    }


def test_runs_start_mints_an_idempotency_key(invoke, mock_api):
    """A caller that names no key still gets the duplicate guard."""
    route = mock_api.post("/api/v1/agentic/runs").respond(200, json=SAMPLE_RUN)
    invoke(["agentic", "runs", "start", "--definition", SAMPLE_RUN["definition_id"]])

    key = route.calls[0].request.headers["Idempotency-Key"]
    assert uuid.UUID(key)


def test_runs_start_sends_the_key_it_was_given(invoke, mock_api):
    route = mock_api.post("/api/v1/agentic/runs").respond(200, json=SAMPLE_RUN)
    invoke(
        [
            "agentic",
            "runs",
            "start",
            "--definition",
            SAMPLE_RUN["definition_id"],
            "--idempotency-key",
            "slack-message-42",
        ]
    )

    assert route.calls[0].request.headers["Idempotency-Key"] == "slack-message-42"


def test_two_starts_mint_two_keys(invoke, mock_api):
    """A fresh key per invocation. A stable one would make tomorrow's run a
    duplicate of today's."""
    route = mock_api.post("/api/v1/agentic/runs").respond(200, json=SAMPLE_RUN)
    invoke(["agentic", "runs", "start", "--definition", SAMPLE_RUN["definition_id"]])
    invoke(["agentic", "runs", "start", "--definition", SAMPLE_RUN["definition_id"]])

    first = route.calls[0].request.headers["Idempotency-Key"]
    second = route.calls[1].request.headers["Idempotency-Key"]
    assert first != second


def test_runs_start_default_input(invoke, mock_api):
    route = mock_api.post("/api/v1/agentic/runs").respond(200, json=SAMPLE_RUN)
    invoke(["agentic", "runs", "start", "--definition", SAMPLE_RUN["definition_id"]])

    assert json.loads(route.calls[0].request.content)["input"] == {}


def test_runs_start_invalid_input(invoke, mock_api):
    result = invoke(
        [
            "agentic",
            "runs",
            "start",
            "--definition",
            SAMPLE_RUN["definition_id"],
            "--input",
            "{bad",
        ]
    )
    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


def test_runs_start_json(invoke, mock_api):
    mock_api.post("/api/v1/agentic/runs").respond(200, json=SAMPLE_RUN)
    result = invoke(
        [
            "agentic",
            "runs",
            "start",
            "--definition",
            SAMPLE_RUN["definition_id"],
            "--json",
        ]
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["id"] == SAMPLE_RUN["id"]


def test_runs_start_reports_a_duplicate(invoke, mock_api):
    """A duplicate is a success, and the caller is told which run it read."""
    mock_api.post("/api/v1/agentic/runs").respond(200, json={**SAMPLE_RUN, "outcome": "duplicate"})
    result = invoke(
        [
            "agentic",
            "runs",
            "start",
            "--definition",
            SAMPLE_RUN["definition_id"],
            "--idempotency-key",
            "same",
        ]
    )
    assert result.exit_code == 0
    assert "duplicate" in result.output.lower()


def test_runs_start_refusal(invoke, mock_api):
    """A draft answers 409, and the CLI keeps the exit code of that status."""
    mock_api.post("/api/v1/agentic/runs").respond(409, json={"detail": "definition is a draft"})
    result = invoke(["agentic", "runs", "start", "--definition", SAMPLE_RUN["definition_id"]])
    assert result.exit_code == 5
    assert "draft" in result.output


def test_runs_start_over_budget(invoke, mock_api):
    """429 carries no code of its own, so it takes the general failure."""
    mock_api.post("/api/v1/agentic/runs").respond(
        429, json={"detail": "the organization day cap is spent"}
    )
    result = invoke(["agentic", "runs", "start", "--definition", SAMPLE_RUN["definition_id"]])
    assert result.exit_code == 1
    assert "day cap" in result.output


# --- get -------------------------------------------------------------------


def test_runs_get(invoke, mock_api):
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}").respond(200, json=SAMPLE_RUN)
    result = invoke(["agentic", "runs", "get", SAMPLE_RUN["id"]])
    assert result.exit_code == 0
    assert "Weekly digest" in result.output
    assert "30 tokens, 4 cents" in result.output


def test_runs_get_json(invoke, mock_api):
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}").respond(200, json=SAMPLE_RUN)
    result = invoke(["agentic", "runs", "get", SAMPLE_RUN["id"], "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["child_count"] == 0


def test_runs_get_prints_that_an_unread_usage_is_unknown(invoke, mock_api):
    """A null usage is a total the meter did not answer, and never a free run."""
    run = {**SAMPLE_RUN, "usage": None}
    mock_api.get(f"/api/v1/agentic/runs/{run['id']}").respond(200, json=run)
    result = invoke(["agentic", "runs", "get", run["id"]])
    assert result.exit_code == 0
    assert "unknown" in result.output
    assert "0 cents" not in result.output


def test_runs_get_not_found(invoke, mock_api):
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}").respond(
        404, json={"detail": "run not found"}
    )
    result = invoke(["agentic", "runs", "get", SAMPLE_RUN["id"]])
    assert result.exit_code == 3


# --- list ------------------------------------------------------------------


def test_runs_list(invoke, mock_api):
    mock_api.get("/api/v1/agentic/runs").respond(
        200, json={"items": [SAMPLE_RUN], "next_cursor": None}
    )
    result = invoke(["agentic", "runs", "list"])
    assert result.exit_code == 0
    assert "Weekly digest" in result.output


def test_runs_list_passes_every_filter(invoke, mock_api):
    route = mock_api.get("/api/v1/agentic/runs").respond(
        200, json={"items": [], "next_cursor": None}
    )
    parent = SAMPLE_RUN["id"]
    invoke(
        [
            "agentic",
            "runs",
            "list",
            "--parent",
            parent,
            "--definition",
            SAMPLE_RUN["definition_id"],
            "--status",
            "running",
            "--limit",
            "10",
            "--cursor",
            "abc",
        ]
    )
    params = route.calls[0].request.url.params
    assert params["parent_run_id"] == parent
    assert params["definition_id"] == SAMPLE_RUN["definition_id"]
    assert params["status"] == "running"
    assert params["limit"] == "10"
    assert params["cursor"] == "abc"


def test_runs_list_sends_no_root_only_by_default(invoke, mock_api):
    """The endpoint defaults to roots, and naming a parent is enough."""
    route = mock_api.get("/api/v1/agentic/runs").respond(
        200, json={"items": [], "next_cursor": None}
    )
    invoke(["agentic", "runs", "list"])

    assert "root_only" not in route.calls[0].request.url.params


def test_runs_list_all_asks_for_every_run(invoke, mock_api):
    route = mock_api.get("/api/v1/agentic/runs").respond(
        200, json={"items": [], "next_cursor": None}
    )
    invoke(["agentic", "runs", "list", "--all"])

    assert route.calls[0].request.url.params["root_only"] == "false"


def test_runs_list_shows_the_next_cursor(invoke, mock_api):
    mock_api.get("/api/v1/agentic/runs").respond(
        200, json={"items": [SAMPLE_RUN], "next_cursor": "next-page"}
    )
    result = invoke(["agentic", "runs", "list"])
    assert "next-page" in result.output


def test_runs_list_json(invoke, mock_api):
    mock_api.get("/api/v1/agentic/runs").respond(
        200, json={"items": [SAMPLE_RUN], "next_cursor": None}
    )
    result = invoke(["agentic", "runs", "list", "--json"])
    assert json.loads(result.output)["items"][0]["id"] == SAMPLE_RUN["id"]


# --- spans -----------------------------------------------------------------


def test_runs_spans(invoke, mock_api):
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [SAMPLE_SPAN], "next_cursor": None}
    )
    result = invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"]])
    assert result.exit_code == 0
    assert "crm.search" in result.output


def test_runs_spans_json(invoke, mock_api):
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [SAMPLE_SPAN], "next_cursor": None}
    )
    result = invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"], "--json"])
    assert json.loads(result.output)["items"][0]["name"] == "crm.search"


def test_runs_spans_pages(invoke, mock_api):
    route = mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [], "next_cursor": None}
    )
    invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"], "--cursor", "c1", "--limit", "5"])
    params = route.calls[0].request.url.params
    assert params["cursor"] == "c1"
    assert params["limit"] == "5"


def test_runs_spans_sends_since(invoke, mock_api):
    """The reconnect read after a dropped stream.

    The stream keeps no backlog, so a client that lost its connection asks for
    the spans that moved while it was away. Without this parameter the CLI
    cannot drive the route the API serves.
    """
    route = mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [], "next_cursor": None}
    )

    invoke(
        [
            "agentic",
            "runs",
            "spans",
            SAMPLE_RUN["id"],
            "--since",
            "2026-08-26T10:00:00+00:00",
        ]
    )

    assert route.calls[0].request.url.params["since"] == "2026-08-26T10:00:00+00:00"


def test_runs_spans_omits_since_when_absent(invoke, mock_api):
    """A plain read orders the page on `started_at`.

    Sending an empty `since` would name a filter the caller did not choose,
    and it would flip the page order the cursor is tagged for.
    """
    route = mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [], "next_cursor": None}
    )

    invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"]])

    assert "since" not in route.calls[0].request.url.params


# --- cancel ----------------------------------------------------------------


def test_runs_cancel_asks_first(invoke, mock_api):
    mock_api.post(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/cancel").respond(
        200, json={**SAMPLE_RUN, "status": "cancelled"}
    )
    result = invoke(["agentic", "runs", "cancel", SAMPLE_RUN["id"]], input="n\n")
    assert result.exit_code != 0


def test_runs_cancel_with_yes(invoke, mock_api):
    route = mock_api.post(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/cancel").respond(
        200, json={**SAMPLE_RUN, "status": "cancelled"}
    )
    result = invoke(["agentic", "runs", "cancel", SAMPLE_RUN["id"], "--yes"])
    assert result.exit_code == 0
    assert route.called
    assert "cancelled" in result.output


def test_runs_cancel_json(invoke, mock_api):
    mock_api.post(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/cancel").respond(
        200, json={**SAMPLE_RUN, "status": "cancelled"}
    )
    result = invoke(["agentic", "runs", "cancel", SAMPLE_RUN["id"], "--yes", "--json"])
    assert json.loads(result.output)["status"] == "cancelled"


def test_runs_cancel_not_found(invoke, mock_api):
    mock_api.post(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/cancel").respond(
        404, json={"detail": "run not found"}
    )
    result = invoke(["agentic", "runs", "cancel", SAMPLE_RUN["id"], "--yes"])
    assert result.exit_code == 3


# --- coexistence -----------------------------------------------------------


def test_the_live_agents_commands_are_untouched(invoke, mock_api):
    """ac agentic runs sits beside ac agents runs. The alias swap is Phase 7."""
    mock_api.get("/api/v1/agents/runs").respond(200, json=[])
    result = invoke(["agents", "runs", "list"])
    assert result.exit_code == 0


def test_runs_start_renders_a_close_tag_in_the_definition_name(invoke, mock_api):
    """The author writes the definition name, as they write a definition."""
    mock_api.post("/api/v1/agentic/runs").respond(
        201,
        json={"id": "run-1", "definition_name": "Acme [/beta] agent", "status": "queued"},
    )
    result = invoke(["agentic", "runs", "start", "--definition", "def-1"])

    assert result.exit_code == 0
    assert "[/beta]" in result.output


def test_runs_start_renders_a_close_tag_on_the_duplicate_path(invoke, mock_api):
    mock_api.post("/api/v1/agentic/runs").respond(
        200,
        json={
            "id": "run[/x]",
            "definition_name": "a",
            "status": "running",
            "outcome": "duplicate",
        },
    )
    result = invoke(["agentic", "runs", "start", "--definition", "def-1"])

    assert result.exit_code == 0
    assert "run[/x]" in result.output


def test_runs_spans_shows_why_a_span_made_no_call(invoke, mock_api):
    """A `tool` span that reads `ok` is not always a call.

    A gate that stopped for a person and a call answered from the journal both
    close `ok` and both carry the tool name, so a person reading the table
    needs the column that tells them apart.
    """
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200,
        json={
            "items": [{**SAMPLE_SPAN, "no_call_reason": "gated"}],
            "next_cursor": None,
        },
    )

    result = invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"]])

    assert "gated" in result.output


def test_runs_spans_leaves_the_no_call_cell_empty_for_a_real_call(invoke, mock_api):
    """The span that did make the call carries a null, and null reads blank.

    The API always emits the key, so the cell renders the null itself. Printed
    as `None` it reads as a reason, and the column then names every row a
    non-call, which inverts what a person counts with it.
    """
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [SAMPLE_SPAN], "next_cursor": None}
    )

    result = invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"]])

    assert SAMPLE_SPAN["no_call_reason"] is None
    assert "None" not in result.output


def test_runs_spans_next_page_hint_repeats_since(invoke, mock_api):
    """The hint is a command a person pastes.

    A cursor from a `--since` page is tagged `updated_at`. Pasted without
    `--since` it pages `started_at` and answers 400, so the hint carries both.
    """
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [SAMPLE_SPAN], "next_cursor": "abc123"}
    )

    result = invoke(
        [
            "agentic",
            "runs",
            "spans",
            SAMPLE_RUN["id"],
            "--since",
            "2026-08-26T10:00:00+00:00",
        ]
    )

    assert "--since 2026-08-26T10:00:00+00:00 --cursor abc123" in result.output


def test_runs_spans_next_page_hint_omits_since_on_a_plain_read(invoke, mock_api):
    """A plain page is tagged `started_at`, so its hint names no `--since`."""
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [SAMPLE_SPAN], "next_cursor": "abc123"}
    )

    result = invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"]])

    assert "--since" not in result.output
    assert "--cursor abc123" in result.output


def test_runs_spans_end_of_drain_names_the_next_since(invoke, mock_api):
    """The reconnect loop reads `updated_at` off the page it just drained.

    A table cell cannot carry it: a timestamp beside a span id truncates at 80
    columns, so the value a person pastes prints on a line of its own. The page
    is ordered ascending, so the last row is the newest.
    """
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200,
        json={
            "items": [
                {**SAMPLE_SPAN, "updated_at": "2026-08-23T10:00:04Z"},
                {**SAMPLE_SPAN, "updated_at": "2026-08-23T10:00:09Z"},
            ],
            "next_cursor": None,
        },
    )

    result = invoke(
        [
            "agentic",
            "runs",
            "spans",
            SAMPLE_RUN["id"],
            "--since",
            "2026-08-26T10:00:00+00:00",
        ]
    )

    assert "Reconnect with: --since 2026-08-23T10:00:09Z" in result.output


def test_runs_spans_names_no_reconnect_before_the_drain_ends(invoke, mock_api):
    """A `>=` filter re-answers its boundary, so `--since` moves last.

    One `UPDATE` stamps every span of a batch alike. A reader that moved
    `--since` while a cursor remained would re-read that group and never pass
    it, so the line prints only when the cursor is spent.
    """
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [SAMPLE_SPAN], "next_cursor": "abc123"}
    )

    result = invoke(
        [
            "agentic",
            "runs",
            "spans",
            SAMPLE_RUN["id"],
            "--since",
            "2026-08-26T10:00:00+00:00",
        ]
    )

    assert "Reconnect with" not in result.output
    assert "--since 2026-08-26T10:00:00+00:00 --cursor abc123" in result.output


def test_runs_spans_plain_read_names_no_reconnect(invoke, mock_api):
    """A plain read pages `started_at`, and it drives no reconnect loop."""
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [SAMPLE_SPAN], "next_cursor": None}
    )

    result = invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"]])

    assert "Reconnect with" not in result.output


def test_runs_spans_idle_poll_keeps_the_since_it_carried(invoke, mock_api):
    """An empty page is the steady state of the loop, not the end of it.

    Nothing moved, so the boundary stays where it is. Without the line a
    script extracts an empty `--since`, which answers 422 and stops the poll.
    """
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [], "next_cursor": None}
    )

    result = invoke(
        [
            "agentic",
            "runs",
            "spans",
            SAMPLE_RUN["id"],
            "--since",
            "2026-08-26T10:00:00+00:00",
        ]
    )

    assert "Reconnect with: --since 2026-08-26T10:00:00+00:00" in result.output


def test_runs_spans_reconnects_against_an_api_that_omits_updated_at(invoke, mock_api):
    """The CLI ships to PyPI on its own cadence, so it meets an older API.

    A subscript would raise KeyError under a table it already printed. The
    boundary stays where it is instead.
    """
    older = {key: value for key, value in SAMPLE_SPAN.items() if key != "updated_at"}
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [older], "next_cursor": None}
    )

    result = invoke(
        [
            "agentic",
            "runs",
            "spans",
            SAMPLE_RUN["id"],
            "--since",
            "2026-08-26T10:00:00+00:00",
        ]
    )

    assert result.exit_code == 0
    assert "Traceback" not in result.output
    assert "Reconnect with: --since 2026-08-26T10:00:00+00:00" in result.output
    assert "--since cannot advance" in result.output


def test_runs_spans_hint_keeps_a_long_cursor_on_one_line(invoke, mock_api):
    """The hint is pasted, so the cursor must survive the copy.

    A real cursor is about 108 characters and the line runs past 80. Hard
    wrapped, it pastes back cut in three and answers 400.
    """
    cursor = (
        "dXBkYXRlZF9hdHwyMDI2LTA4LTI2VDEwOjAwOjAwLjEyMzQ1NiswMDowMHwzMzMzMzMzMy0z"
        "MzMzLTQzMzMtODMzMy0zMzMzMzMzMzMzMzM"
    )
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [SAMPLE_SPAN], "next_cursor": cursor}
    )

    result = invoke(
        [
            "agentic",
            "runs",
            "spans",
            SAMPLE_RUN["id"],
            "--since",
            "2026-08-26T10:00:00+00:00",
        ]
    )

    assert f"--cursor {cursor}" in result.output


def test_runs_spans_warns_on_a_stamp_that_cannot_move_the_boundary(invoke, mock_api):
    """An empty stamp moves the poll no further than a missing one.

    Printed bare it names an empty `--since`, which answers 422 and stops the
    loop this line exists to keep running. It takes the same fallback as a
    null, so it takes the same warning.
    """
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200,
        json={"items": [{**SAMPLE_SPAN, "updated_at": ""}], "next_cursor": None},
    )

    result = invoke(
        [
            "agentic",
            "runs",
            "spans",
            SAMPLE_RUN["id"],
            "--since",
            "2026-08-26T10:00:00+00:00",
        ]
    )

    assert "--since cannot advance" in result.output
    assert "Reconnect with: --since 2026-08-26T10:00:00+00:00" in result.output


def test_runs_spans_takes_the_newest_usable_stamp_of_the_page(invoke, mock_api):
    """A last row with no stamp must not discard the progress of the page.

    The rows are ordered, so the first usable stamp from the end is the newest
    one. Reading the last row alone would send the caller back to the boundary
    it started from and re-read every row the page just answered.
    """
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200,
        json={
            "items": [
                {**SAMPLE_SPAN, "updated_at": "2026-08-26T11:00:00Z"},
                {**SAMPLE_SPAN, "updated_at": None},
            ],
            "next_cursor": None,
        },
    )

    result = invoke(
        [
            "agentic",
            "runs",
            "spans",
            SAMPLE_RUN["id"],
            "--since",
            "2026-08-26T10:00:00+00:00",
        ]
    )

    assert "Reconnect with: --since 2026-08-26T11:00:00Z" in result.output
    assert "cannot advance" not in result.output


def test_runs_spans_hint_repeats_a_page_size_the_caller_chose(invoke, mock_api):
    """The hint is pasted, so it carries the whole read and not part of it.

    A drain that starts at 200 rows a page and continues at the default reads
    the run in four times the requests, and the pasted line says nothing.
    """
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [SAMPLE_SPAN], "next_cursor": "abc123"}
    )

    result = invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"], "--limit", "100"])

    assert "--limit 100 --cursor abc123" in result.output


def test_runs_spans_hint_omits_the_default_page_size(invoke, mock_api):
    """The default needs no flag, and a hint reads better without one."""
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [SAMPLE_SPAN], "next_cursor": "abc123"}
    )

    result = invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"]])

    assert "--limit" not in result.output
    assert "--cursor abc123" in result.output


def test_runs_spans_refuses_a_page_size_the_api_refuses(invoke, mock_api):
    """The route is `Query(50, ge=1, le=100)`, so the flag carries its bounds.

    Unbounded, the read reached the API and answered 422 after a round trip.
    """
    result = invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"], "--limit", "200"])

    assert result.exit_code != 0
    assert "100" in result.output


def test_runs_spans_reconnect_line_repeats_a_page_size_the_caller_chose(invoke, mock_api):
    """This is the line a poll loop re-reads on every cycle.

    Dropped here, a loop started at 100 rows a page runs at 50 for the rest of
    its life, which is the failure the next-page echo already prevents.
    """
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200,
        json={
            "items": [{**SAMPLE_SPAN, "updated_at": "2026-08-26T11:00:00Z"}],
            "next_cursor": None,
        },
    )

    result = invoke(
        [
            "agentic",
            "runs",
            "spans",
            SAMPLE_RUN["id"],
            "--since",
            "2026-08-26T10:00:00+00:00",
            "--limit",
            "100",
        ]
    )

    assert "Reconnect with: --since 2026-08-26T11:00:00Z --limit 100" in result.output


def test_runs_spans_refuses_a_naive_since_before_the_request(invoke, mock_api):
    """A stamp with no offset names no instant, and the API answers 400.

    Refused here it costs no authenticated round trip, and the message names
    the flag and the value.
    """
    result = invoke(
        ["agentic", "runs", "spans", SAMPLE_RUN["id"], "--since", "2026-08-26T10:00:00"]
    )

    assert result.exit_code == 2
    assert "time zone" in result.output


def test_runs_spans_refuses_a_since_that_is_not_a_stamp(invoke, mock_api):
    """`--since yesterday` is not ISO 8601, and the flag says ISO 8601."""
    result = invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"], "--since", "yesterday"])

    assert result.exit_code == 2
    assert "ISO 8601" in result.output


def test_runs_list_hint_repeats_a_page_size_the_caller_chose(invoke, mock_api):
    """Every cursor hint of this file repeats the size, not the spans one alone.

    A walk started at 100 rows a page that continues at the default reads the
    set in twice the requests, and the pasted line says nothing.
    """
    mock_api.get("/api/v1/agentic/runs").respond(
        200, json={"items": [SAMPLE_RUN], "next_cursor": "abc123"}
    )

    result = invoke(["agentic", "runs", "list", "--limit", "100"])

    assert "--limit 100 --cursor abc123" in result.output


def test_runs_spans_accepts_the_since_it_printed(invoke, mock_api):
    """The round trip the whole flag exists for.

    The API writes `Z` and the `Reconnect with:` line prints what it wrote, so
    the value this command answers must be one it takes back. `fromisoformat`
    reads a `Z` only from Python 3.11, and this package supports 3.10, so a
    test that only ever passes `+00:00` would stay green while the loop is
    dead on the oldest interpreter the package claims.
    """
    stamp = "2026-08-23T10:00:09Z"
    route = mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200,
        json={"items": [{**SAMPLE_SPAN, "updated_at": stamp}], "next_cursor": None},
    )

    printed = invoke(
        ["agentic", "runs", "spans", SAMPLE_RUN["id"], "--since", "2026-08-26T10:00:00+00:00"]
    )
    assert f"Reconnect with: --since {stamp}" in printed.output

    replayed = invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"], "--since", stamp])

    assert replayed.exit_code == 0
    assert route.calls[-1].request.url.params["since"] == "2026-08-23T10:00:09+00:00"


def test_runs_spans_reports_a_bad_since_as_json_when_asked(invoke, mock_api):
    """A poll drives this command with --json, and parses what it prints."""
    result = invoke(
        ["agentic", "runs", "spans", SAMPLE_RUN["id"], "--since", "yesterday", "--json"]
    )

    assert result.exit_code == 2
    body = json.loads(result.output)
    assert body["error"] is True
    assert "--since" in body["detail"]


def test_runs_list_hint_repeats_the_filters_the_read_carried(invoke, mock_api):
    """A cursor is a keyset position and carries no filter.

    Pasted without them the read answers page two of the unfiltered set, with
    a 200 and nothing to say the filter was lost.
    """
    mock_api.get("/api/v1/agentic/runs").respond(
        200, json={"items": [SAMPLE_RUN], "next_cursor": "abc123"}
    )

    result = invoke(["agentic", "runs", "list", "--status", "failed", "--all"])

    assert "--status failed --all --cursor abc123" in result.output


def test_runs_list_hint_quotes_a_value_a_shell_would_read(invoke, mock_api):
    """The hint is pasted into a shell, so a glob must not reach it.

    `crm.*` unquoted dies in zsh as `no matches found`, and in bash it matches
    a file and pages a filter the caller never named.
    """
    mock_api.get("/api/v1/agentic/runs").respond(
        200, json={"items": [SAMPLE_RUN], "next_cursor": "abc123"}
    )

    result = invoke(["agentic", "runs", "list", "--status", "crm.*"])

    assert "--status 'crm.*'" in result.output


def test_runs_spans_reports_a_limit_the_api_refuses_as_json(invoke, mock_api):
    """A range on the Option renders a usage box, and a poll cannot parse one.

    The bound is checked in the command, so `--json` answers the shape
    _handle_error answers.
    """
    result = invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"], "--limit", "200", "--json"])

    assert result.exit_code == 2
    body = json.loads(result.output)
    assert body["error"] is True
    assert "--limit" in body["detail"]


def test_runs_spans_warns_when_the_api_reports_no_no_call_reason(invoke, mock_api):
    """An absent key is not a null one.

    A null says this span was the call. No key says the API does not report
    the fact, so the column is blank on every row and reads as a run that
    gated nothing.
    """
    older = {key: value for key, value in SAMPLE_SPAN.items() if key != "no_call_reason"}
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [older], "next_cursor": None}
    )

    result = invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"]])

    assert "does not report no_call_reason" in result.output


def test_runs_spans_stays_quiet_when_a_span_was_the_call(invoke, mock_api):
    """A null is the common answer, and it is not a warning."""
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [SAMPLE_SPAN], "next_cursor": None}
    )

    result = invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"]])

    assert "does not report" not in result.output


def test_runs_spans_idle_poll_warns_of_nothing(invoke, mock_api):
    """An empty page repeats the boundary, and that is the correct answer.

    It reads like the stuck poll on the line below, so only the stuck one
    carries the warning.
    """
    mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [], "next_cursor": None}
    )

    result = invoke(
        [
            "agentic",
            "runs",
            "spans",
            SAMPLE_RUN["id"],
            "--since",
            "2026-08-26T10:00:00+00:00",
        ]
    )

    assert "cannot advance" not in result.output


def test_runs_spans_refuses_an_empty_since_rather_than_dropping_it(invoke, mock_api):
    """An empty value is a failed extraction, and it must not read silently.

    A poll builds `--since` from the last page. Dropped, the read loses its
    filter and its order, and the loop re-reads the whole run on every poll
    with nothing to say so. It is refused instead, and no request is made.
    """
    route = mock_api.get(f"/api/v1/agentic/runs/{SAMPLE_RUN['id']}/spans").respond(
        200, json={"items": [], "next_cursor": None}
    )

    result = invoke(["agentic", "runs", "spans", SAMPLE_RUN["id"], "--since", ""])

    assert result.exit_code == 2
    assert not route.calls


def test_runs_get_shows_capability_identity(invoke, mock_api):
    run = {**SAMPLE_RUN, "capability_id": "company.search", "contract_version": 7}
    mock_api.get(f"/api/v1/agentic/runs/{run['id']}").respond(200, json=run)
    result = invoke(["agentic", "runs", "get", run["id"]])
    assert result.exit_code == 0
    assert "company.search" in result.output
    assert "Contract version" in result.output


def test_runs_get_preserves_null_capability(invoke, mock_api):
    run = {**SAMPLE_RUN, "capability_id": None, "contract_version": None}
    mock_api.get(f"/api/v1/agentic/runs/{run['id']}").respond(200, json=run)
    result = invoke(["agentic", "runs", "get", run["id"], "--json"])
    body = json.loads(result.output)
    assert body["capability_id"] is None
    assert body["contract_version"] is None


def test_run_list_json_keeps_identity(invoke, mock_api):
    run = {**SAMPLE_RUN, "capability_id": "signals.search", "contract_version": 4}
    mock_api.get("/api/v1/agentic/runs").respond(200, json={"items": [run], "next_cursor": None})
    result = invoke(["agentic", "runs", "list", "--json"])
    item = json.loads(result.output)["items"][0]
    assert item["capability_id"] == "signals.search"
    assert item["contract_version"] == 4


# -- the idempotency key the caller names --------------------------------------

UNSENDABLE_KEYS = [
    "",
    " ",
    " delivery-42",
    "delivery-42 ",
    "x" * 201,
    "line\nbreak",
    "carriage\rreturn",
    "nul\x00byte",
    "tab\there",
    "del\x7f",
    "é",
]


@pytest.mark.parametrize("key", UNSENDABLE_KEYS)
def test_runs_start_refuses_a_key_the_header_refuses(invoke, mock_api, key):
    """A key that cannot travel is refused before any HTTP call."""
    mock_api.post("/api/v1/agentic/runs").respond(200, json=SAMPLE_RUN)

    result = invoke(
        [
            "agentic",
            "runs",
            "start",
            "--definition",
            SAMPLE_RUN["definition_id"],
            "--idempotency-key",
            key,
            "--json",
        ]
    )

    assert result.exit_code == 2, result.output
    body = json.loads(result.output)
    assert body["error"] is True
    assert body["status_code"] is None
    assert "--idempotency-key" in body["detail"]
    assert not mock_api.calls


def test_runs_start_never_mints_a_key_for_an_empty_flag(invoke, mock_api):
    """An unset shell variable must not silently disable the duplicate guard."""
    mock_api.post("/api/v1/agentic/runs").respond(200, json=SAMPLE_RUN)

    result = invoke(
        [
            "agentic",
            "runs",
            "start",
            "--definition",
            SAMPLE_RUN["definition_id"],
            "--idempotency-key",
            "",
        ]
    )

    assert result.exit_code == 2
    assert not mock_api.calls


def test_runs_start_sends_a_key_at_the_length_bound(invoke, mock_api):
    """200 characters is the last length the header check accepts."""
    route = mock_api.post("/api/v1/agentic/runs").respond(200, json=SAMPLE_RUN)
    key = "x" * 200

    result = invoke(
        [
            "agentic",
            "runs",
            "start",
            "--definition",
            SAMPLE_RUN["definition_id"],
            "--idempotency-key",
            key,
        ]
    )

    assert result.exit_code == 0, result.output
    assert route.calls[0].request.headers["Idempotency-Key"] == key
