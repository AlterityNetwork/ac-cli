"""Start by key and the startable definitions: the commands on the new endpoints."""

import json

from tests.test_agentic_runs import SAMPLE_RUN

STARTABLE = "/api/v1/agentic/definitions/startable"
RUNS = "/api/v1/agentic/runs"

AVAILABLE = {
    "definition_key": "company.search",
    "availability": "available",
    "name": "Company Search",
    "description": "Finds companies.",
    "contract_version": 1,
    "input_schema": {"type": "object"},
    "output_schema": {"type": "object"},
    "required_scopes": ["run.start", "crm.get_company"],
    "executor_type": "workflow",
}
UNAVAILABLE = {
    "definition_key": "people.enrich",
    "availability": "unavailable",
    "reason": "not_installed",
}


def test_runs_start_by_key_posts_the_key_and_the_delivery_key(invoke, mock_api):
    route = mock_api.post(RUNS).respond(200, json={**SAMPLE_RUN, "outcome": "started"})

    result = invoke(
        [
            "agentic", "runs", "start", "--key", "company.search",
            "--input", '{"query":"acme"}', "--idempotency-key", "d-1",
            "--title", "Acme", "--saved-search-id", "s-1", "--json",
        ]
    )  # fmt: skip

    assert result.exit_code == 0, result.output
    request = route.calls[0].request
    assert json.loads(request.content) == {
        "key": "company.search",
        "input": {"query": "acme"},
        "title": "Acme",
        "saved_search_id": "s-1",
    }
    assert request.headers["Idempotency-Key"] == "d-1"


def test_runs_start_by_key_mints_a_delivery_key_when_none_is_given(invoke, mock_api):
    route = mock_api.post(RUNS).respond(200, json={**SAMPLE_RUN, "outcome": "started"})

    result = invoke(["agentic", "runs", "start", "--key", "company.search", "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(route.calls[0].request.content) == {"key": "company.search", "input": {}}
    assert route.calls[0].request.headers["Idempotency-Key"]


def test_runs_start_names_exactly_one_of_definition_and_key(invoke, mock_api):
    both = invoke(
        ["agentic", "runs", "start", "--key", "company.search", "--definition", "d", "--json"]
    )
    neither = invoke(["agentic", "runs", "start", "--json"])

    assert both.exit_code == 2 and neither.exit_code == 2
    assert not mock_api.calls


def test_runs_start_refuses_a_saved_search_id_with_a_definition(invoke, mock_api):
    result = invoke(
        ["agentic", "runs", "start", "--definition", "d", "--saved-search-id", "s", "--json"]
    )

    assert result.exit_code == 2
    assert not mock_api.calls


def test_runs_start_by_key_refuses_bad_input_without_http(invoke, mock_api):
    result = invoke(
        ["agentic", "runs", "start", "--key", "company.search", "--input", "[]", "--json"]
    )

    assert result.exit_code == 2
    assert not mock_api.calls


def test_definitions_startable_lists_available_keys_by_default(invoke, mock_api):
    route = mock_api.get(STARTABLE).respond(200, json={"items": [AVAILABLE]})

    result = invoke(["agentic", "definitions", "startable"])

    assert result.exit_code == 0, result.output
    assert "company.search" in result.output
    assert route.calls[0].request.url.params["available_only"] == "true"


def test_definitions_startable_all_shows_the_reason(invoke, mock_api):
    route = mock_api.get(STARTABLE).respond(200, json={"items": [UNAVAILABLE]})

    result = invoke(["agentic", "definitions", "startable", "--all"])

    assert result.exit_code == 0, result.output
    assert "not_installed" in result.output
    assert route.calls[0].request.url.params["available_only"] == "false"


def test_definitions_startable_show_reads_one_key_and_its_schemas(invoke, mock_api):
    mock_api.get(f"{STARTABLE}/company.search").respond(200, json=AVAILABLE)

    result = invoke(["agentic", "definitions", "startable-show", "company.search", "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == AVAILABLE


def test_definitions_startable_show_encodes_a_reserved_character(invoke, mock_api):
    route = mock_api.get(f"{STARTABLE}/a%2Fb").respond(404, json={"detail": "unknown"})

    invoke(["agentic", "definitions", "startable-show", "a/b", "--json"])

    assert route.called


def test_runs_start_refuses_an_empty_key_without_http(invoke, mock_api):
    for value in ("", "  "):
        result = invoke(["agentic", "runs", "start", "--key", value, "--json"])

        assert result.exit_code == 2
    assert not mock_api.calls


def test_runs_list_filters_on_the_definition_key_and_repeats(invoke, mock_api):
    route = mock_api.get(RUNS).respond(200, json={"items": [], "next_cursor": None})

    result = invoke(
        ["agentic", "runs", "list", "--key", "signals.search", "--key", "people.signals", "--json"]
    )

    assert result.exit_code == 0, result.output
    params = route.calls[0].request.url.params
    assert params.get_list("definition_key") == ["signals.search", "people.signals"]
    assert "capability_id" not in params
