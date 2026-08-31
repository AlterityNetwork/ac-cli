"""Tests for the agentic platform trigger commands.

`ac agentic triggers` drives the machine entry points of an organization. A row
starts Runs with no person watching, so the six commands are a list, a create,
an edit, a kill switch on and off, and a delete.
"""

import json

_BASE = "/api/v1/agentic/triggers"

SAMPLE_TRIGGER = {
    "id": "11111111-1111-4111-8111-111111111111",
    "name": "Weekly signals",
    "kind": "schedule",
    "event_type": None,
    "conditions": None,
    "cron": "0 9 * * 1",
    "timezone": "Europe/London",
    "target_definition_id": "22222222-2222-4222-8222-222222222222",
    "input_builder": "saved_search",
    "input_config": {"saved_search_id": "33333333-3333-4333-8333-333333333333"},
    "scopes": ["prospect.upsert"],
    "authored_by": "44444444-4444-4444-8444-444444444444",
    "enabled": False,
    "last_outcome": None,
    "last_outcome_at": None,
    "last_run_id": None,
    "created_at": "2026-08-31T09:00:00Z",
    "updated_at": "2026-08-31T10:00:00.123456+00:00",
}

SAMPLE_PAGE = {"items": [SAMPLE_TRIGGER], "next_cursor": None}

_ID = SAMPLE_TRIGGER["id"]
_DEFINITION = SAMPLE_TRIGGER["target_definition_id"]
_TOKEN = SAMPLE_TRIGGER["updated_at"]


# --- list ------------------------------------------------------------------


def test_triggers_list(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    result = invoke(["agentic", "triggers", "list"])

    assert result.exit_code == 0
    assert "Weekly signals" in result.output
    assert route.called


def test_triggers_list_json_carries_the_write_token(invoke, mock_api):
    """There is no detail route, so the list is where `patch` reads the token."""
    mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    result = invoke(["agentic", "triggers", "list", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output)["items"][0]["updated_at"] == _TOKEN


def test_triggers_list_filters_on_enabled(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    result = invoke(["agentic", "triggers", "list", "--enabled"])

    assert result.exit_code == 0
    assert route.calls[0].request.url.params["enabled"] == "true"


def test_triggers_list_filters_on_disabled(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    result = invoke(["agentic", "triggers", "list", "--disabled"])

    assert result.exit_code == 0
    assert route.calls[0].request.url.params["enabled"] == "false"


def test_triggers_list_refuses_both_state_flags(invoke, mock_api):
    result = invoke(["agentic", "triggers", "list", "--enabled", "--disabled"])

    assert result.exit_code == 1


def test_triggers_list_next_page_hint_repeats_the_filter(invoke, mock_api):
    """A cursor is a keyset position and carries no filter.

    A hint naming the cursor alone pages the unfiltered set from that position
    and answers 200: page one filtered and page two not, with nothing to say
    so.
    """
    page = {"items": [SAMPLE_TRIGGER], "next_cursor": "opaque-cursor"}
    mock_api.get(_BASE).respond(200, json=page)
    result = invoke(["agentic", "triggers", "list", "--enabled"])

    assert result.exit_code == 0
    assert "--enabled" in result.output
    assert "opaque-cursor" in result.output


def test_triggers_list_next_page_hint_names_no_filter_when_none_was_set(invoke, mock_api):
    page = {"items": [SAMPLE_TRIGGER], "next_cursor": "opaque-cursor"}
    mock_api.get(_BASE).respond(200, json=page)
    result = invoke(["agentic", "triggers", "list"])

    assert result.exit_code == 0
    assert "--enabled" not in result.output
    assert "--disabled" not in result.output


def test_triggers_list_sends_the_cursor_it_was_given(invoke, mock_api):
    route = mock_api.get(_BASE).respond(200, json=SAMPLE_PAGE)
    result = invoke(["agentic", "triggers", "list", "--cursor", "opaque-cursor"])

    assert result.exit_code == 0
    assert route.calls[0].request.url.params["cursor"] == "opaque-cursor"


def test_triggers_create_reports_a_row_that_could_never_fire(invoke, mock_api):
    """The API proves the schedule, the zone, the builder and the tree."""
    mock_api.post(_BASE).respond(422, json={"detail": "croniter cannot read 'every monday'"})
    result = invoke(
        [
            "agentic",
            "triggers",
            "create",
            "--name",
            "Bad schedule",
            "--schedule",
            "every monday",
            "--definition",
            _DEFINITION,
            "--scope",
            "prospect.upsert",
        ]
    )

    assert result.exit_code == 2
    assert "croniter" in result.output


def test_triggers_create_shows_the_input_config_it_wrote(invoke, mock_api):
    """A scheduled saved search is the flagship non-default create.

    Without the field in the detail block there is no way to confirm the
    saved-search id landed, short of reading the list back as JSON.
    """
    mock_api.post(_BASE).respond(201, json=SAMPLE_TRIGGER)
    result = invoke(
        [
            "agentic",
            "triggers",
            "create",
            "--name",
            "Weekly signals",
            "--schedule",
            "0 9 * * 1",
            "--definition",
            _DEFINITION,
            "--scope",
            "prospect.upsert",
            "--input-builder",
            "saved_search",
            "--input-config",
            '{"saved_search_id": "33333333-3333-4333-8333-333333333333"}',
        ]
    )

    assert result.exit_code == 0
    assert "33333333-3333-4333-8333-333333333333" in result.output


def test_triggers_list_shows_the_last_outcome(invoke, mock_api):
    """A skip writes no Run, so this column is where a person reads why."""
    page = {
        "items": [{**SAMPLE_TRIGGER, "last_outcome": "budget"}],
        "next_cursor": None,
    }
    mock_api.get(_BASE).respond(200, json=page)
    result = invoke(["agentic", "triggers", "list"])

    assert result.exit_code == 0
    assert "budget" in result.output


# --- create ----------------------------------------------------------------


def test_triggers_create_schedule(invoke, mock_api):
    route = mock_api.post(_BASE).respond(201, json=SAMPLE_TRIGGER)
    result = invoke(
        [
            "agentic",
            "triggers",
            "create",
            "--name",
            "Weekly signals",
            "--schedule",
            "0 9 * * 1",
            "--timezone",
            "Europe/London",
            "--definition",
            _DEFINITION,
            "--scope",
            "prospect.upsert",
        ]
    )

    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert body == {
        "name": "Weekly signals",
        "kind": "schedule",
        "cron": "0 9 * * 1",
        "timezone": "Europe/London",
        "target_definition_id": _DEFINITION,
        "input_builder": "static",
        "input_config": {},
        "scopes": ["prospect.upsert"],
    }


def test_triggers_create_event(invoke, mock_api):
    route = mock_api.post(_BASE).respond(201, json=SAMPLE_TRIGGER)
    result = invoke(
        [
            "agentic",
            "triggers",
            "create",
            "--name",
            "Qualified company",
            "--on",
            "crm.company.updated",
            "--definition",
            _DEFINITION,
            "--scope",
            "crm.get_company",
            "--conditions",
            '{"op": "eq", "path": "data.lifecycle", "value": "qualified"}',
        ]
    )

    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert body["kind"] == "event"
    assert body["event_type"] == "crm.company.updated"
    assert "cron" not in body
    assert body["conditions"]["path"] == "data.lifecycle"


def test_triggers_create_takes_more_than_one_scope(invoke, mock_api):
    route = mock_api.post(_BASE).respond(201, json=SAMPLE_TRIGGER)
    result = invoke(
        [
            "agentic",
            "triggers",
            "create",
            "--name",
            "Weekly signals",
            "--schedule",
            "0 9 * * 1",
            "--definition",
            _DEFINITION,
            "--scope",
            "prospect.upsert",
            "--scope",
            "crm.get_company",
        ]
    )

    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert body["scopes"] == ["prospect.upsert", "crm.get_company"]


def test_triggers_create_refuses_neither_shape(invoke, mock_api):
    """A row that names no schedule and no event is a row nothing starts."""
    result = invoke(
        [
            "agentic",
            "triggers",
            "create",
            "--name",
            "Neither",
            "--definition",
            _DEFINITION,
            "--scope",
            "prospect.upsert",
        ]
    )

    assert result.exit_code == 1
    assert "--schedule" in result.output


def test_triggers_create_refuses_both_shapes(invoke, mock_api):
    result = invoke(
        [
            "agentic",
            "triggers",
            "create",
            "--name",
            "Both",
            "--schedule",
            "0 9 * * 1",
            "--on",
            "crm.company.updated",
            "--definition",
            _DEFINITION,
            "--scope",
            "prospect.upsert",
        ]
    )

    assert result.exit_code == 1


def test_triggers_create_refuses_conditions_that_are_not_an_object(invoke, mock_api):
    result = invoke(
        [
            "agentic",
            "triggers",
            "create",
            "--name",
            "Bad tree",
            "--on",
            "crm.company.updated",
            "--definition",
            _DEFINITION,
            "--scope",
            "prospect.upsert",
            "--conditions",
            "[1, 2]",
        ]
    )

    assert result.exit_code == 1


def test_triggers_create_says_the_row_starts_disabled(invoke, mock_api):
    mock_api.post(_BASE).respond(201, json=SAMPLE_TRIGGER)
    result = invoke(
        [
            "agentic",
            "triggers",
            "create",
            "--name",
            "Weekly signals",
            "--schedule",
            "0 9 * * 1",
            "--definition",
            _DEFINITION,
            "--scope",
            "prospect.upsert",
        ]
    )

    assert result.exit_code == 0
    assert "enable" in result.output.lower()


def test_triggers_create_reports_a_scope_the_author_does_not_hold(invoke, mock_api):
    mock_api.post(_BASE).respond(403, json={"detail": "you do not hold crm.upsert_company"})
    result = invoke(
        [
            "agentic",
            "triggers",
            "create",
            "--name",
            "Too wide",
            "--schedule",
            "0 9 * * 1",
            "--definition",
            _DEFINITION,
            "--scope",
            "crm.upsert_company",
        ]
    )

    assert result.exit_code == 4


# --- patch -----------------------------------------------------------------


def test_triggers_patch(invoke, mock_api):
    route = mock_api.patch(f"{_BASE}/{_ID}").respond(200, json=SAMPLE_TRIGGER)
    result = invoke(
        [
            "agentic",
            "triggers",
            "patch",
            _ID,
            "--expected-updated-at",
            _TOKEN,
            "--patch",
            '{"name": "Renamed"}',
        ]
    )

    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert body == {"expected_updated_at": _TOKEN, "name": "Renamed"}


def test_triggers_patch_reports_a_stale_token(invoke, mock_api):
    mock_api.patch(f"{_BASE}/{_ID}").respond(
        409, json={"detail": "the trigger changed since you read it"}
    )
    result = invoke(
        [
            "agentic",
            "triggers",
            "patch",
            _ID,
            "--expected-updated-at",
            _TOKEN,
            "--patch",
            '{"name": "Renamed"}',
        ]
    )

    assert result.exit_code == 5


def test_triggers_patch_refuses_a_patch_that_is_not_an_object(invoke, mock_api):
    result = invoke(
        [
            "agentic",
            "triggers",
            "patch",
            _ID,
            "--expected-updated-at",
            _TOKEN,
            "--patch",
            '"Renamed"',
        ]
    )

    assert result.exit_code == 1


# --- enable and disable ----------------------------------------------------


def test_triggers_enable(invoke, mock_api):
    route = mock_api.post(f"{_BASE}/{_ID}/enable").respond(
        200, json={**SAMPLE_TRIGGER, "enabled": True}
    )
    result = invoke(["agentic", "triggers", "enable", _ID])

    assert result.exit_code == 0
    assert route.called


def test_triggers_disable_needs_no_token(invoke, mock_api):
    """The kill switch must not answer stale at 02:00."""
    route = mock_api.post(f"{_BASE}/{_ID}/disable").respond(200, json=SAMPLE_TRIGGER)
    result = invoke(["agentic", "triggers", "disable", _ID])

    assert result.exit_code == 0
    assert route.calls[0].request.content in (b"", b"null")


def test_triggers_disable_says_it_stops_no_running_work(invoke, mock_api):
    mock_api.post(f"{_BASE}/{_ID}/disable").respond(200, json=SAMPLE_TRIGGER)
    result = invoke(["agentic", "triggers", "disable", _ID])

    assert result.exit_code == 0
    assert "cancel" in result.output.lower()


def test_triggers_enable_reports_a_row_this_organization_does_not_own(invoke, mock_api):
    mock_api.post(f"{_BASE}/{_ID}/enable").respond(404, json={"detail": "trigger not found"})
    result = invoke(["agentic", "triggers", "enable", _ID])

    assert result.exit_code == 3


# --- delete ----------------------------------------------------------------


def test_triggers_delete_asks_first(invoke, mock_api):
    route = mock_api.delete(f"{_BASE}/{_ID}").respond(204)
    result = invoke(["agentic", "triggers", "delete", _ID], input="n\n")

    assert result.exit_code != 0
    assert not route.called


def test_triggers_delete_with_yes(invoke, mock_api):
    route = mock_api.delete(f"{_BASE}/{_ID}").respond(204)
    result = invoke(["agentic", "triggers", "delete", _ID, "--yes"])

    assert result.exit_code == 0
    assert route.called


def test_triggers_delete_json(invoke, mock_api):
    mock_api.delete(f"{_BASE}/{_ID}").respond(204)
    result = invoke(["agentic", "triggers", "delete", _ID, "--yes", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == {"id": _ID, "deleted": True}
