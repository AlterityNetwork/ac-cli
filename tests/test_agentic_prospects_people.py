"""Tests for the commands that add people to an agentic prospect."""

import json

BASE = "/api/v1/agentic/prospects"
PROSPECT_ID = "11111111-1111-4111-8111-111111111111"
RUN_ID = "77777777-7777-4777-8777-777777777777"
LINKEDIN = "https://linkedin.com/in/alice"

PERSON = {
    "id": "33333333-3333-4333-8333-333333333333",
    "prospect_id": PROSPECT_ID,
    "crm_person_id": None,
    "persona_fit_score": None,
    "persona_fit_reason": None,
    "contact_state": "unavailable",
    "first_seen_at": "2026-08-28T10:00:00Z",
    "last_seen_at": "2026-08-28T10:00:00Z",
    "created_at": "2026-08-28T10:00:00Z",
    "updated_at": "2026-08-28T10:00:00Z",
    "person": {
        "id": "44444444-4444-4444-8444-444444444444",
        "linkedin_url": LINKEDIN,
        "full_name": "Alice Doe",
        "avatar_url": None,
        "current_title": "CFO",
        "current_company_text": "Acme",
        "location": None,
        "country": None,
        "email": None,
        "last_enriched_at": "2026-08-28T10:00:00Z",
    },
}
RUN = {
    "id": RUN_ID,
    "status": "queued",
    "outcome": "started",
    "definition_name": "people.search",
    "input": {},
    "result": None,
    "error": None,
    "usage": None,
    "child_count": 0,
}
SEARCH_RUNNING = "A people search for this company is already running"


def _add(*extra: str) -> list[str]:
    return [
        "agentic",
        "prospects",
        "add-person",
        PROSPECT_ID,
        "--name",
        "Alice Doe",
        "--linkedin-url",
        LINKEDIN,
        *extra,
    ]


def test_add_person_posts_the_two_required_fields_and_prints_the_row(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{PROSPECT_ID}/people").respond(200, json=PERSON)

    result = invoke(_add())

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {
        "full_name": "Alice Doe",
        "linkedin_url": LINKEDIN,
    }
    assert "Alice Doe" in result.output
    assert "CFO" in result.output
    assert "Acme" in result.output


def test_add_person_sends_the_title_and_the_email_when_given(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{PROSPECT_ID}/people").respond(200, json=PERSON)

    result = invoke(_add("--title", "CFO", "--email", "alice@acme.test"))

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {
        "full_name": "Alice Doe",
        "linkedin_url": LINKEDIN,
        "current_title": "CFO",
        "email": "alice@acme.test",
    }


def test_add_person_json_keeps_the_row(invoke, mock_api):
    mock_api.post(f"{BASE}/{PROSPECT_ID}/people").respond(200, json=PERSON)

    result = invoke(_add("--json"))

    assert result.exit_code == 0
    assert json.loads(result.output) == PERSON


def test_add_person_needs_a_name_and_a_profile(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{PROSPECT_ID}/people").respond(200, json=PERSON)

    result = invoke(["agentic", "prospects", "add-person", PROSPECT_ID, "--name", "Alice Doe"])

    assert result.exit_code == 2
    assert not route.calls


def test_add_person_maps_not_found_to_exit_three(invoke, mock_api):
    mock_api.post(f"{BASE}/{PROSPECT_ID}/people").respond(
        404, json={"detail": "prospect not found"}
    )

    result = invoke(_add())

    assert result.exit_code == 3
    assert "prospect not found" in result.output


def test_add_person_maps_a_person_prospect_to_exit_five(invoke, mock_api):
    mock_api.post(f"{BASE}/{PROSPECT_ID}/people").respond(
        409, json={"detail": "a person prospect cannot take people"}
    )

    result = invoke(_add())

    assert result.exit_code == 5
    assert "a person prospect cannot take people" in result.output


def test_add_person_json_error_names_the_refusal(invoke, mock_api):
    mock_api.post(f"{BASE}/{PROSPECT_ID}/people").respond(
        422, json={"detail": "linkedin_url must name a LinkedIn profile (/in/)"}
    )

    result = invoke(_add("--json"))

    assert result.exit_code == 2
    error = json.loads(result.output)
    assert error["error"] is True
    assert error["status_code"] == 422


def test_find_people_posts_no_body_and_prints_the_run(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{PROSPECT_ID}/people/search").respond(200, json=RUN)

    result = invoke(["agentic", "prospects", "find-people", PROSPECT_ID])

    assert result.exit_code == 0
    request = route.calls[0].request
    assert request.content == b""
    assert "Idempotency-Key" not in request.headers
    assert RUN_ID in result.output
    assert "queued" in result.output
    assert f"ac agentic prospects people {PROSPECT_ID}" in result.output


def test_find_people_names_a_replayed_run(invoke, mock_api):
    mock_api.post(f"{BASE}/{PROSPECT_ID}/people/search").respond(
        200, json={**RUN, "outcome": "duplicate", "status": "running"}
    )

    result = invoke(["agentic", "prospects", "find-people", PROSPECT_ID])

    assert result.exit_code == 0
    assert "already started" in result.output
    assert RUN_ID in result.output
    assert "running" in result.output


def test_find_people_json_keeps_the_run(invoke, mock_api):
    mock_api.post(f"{BASE}/{PROSPECT_ID}/people/search").respond(200, json=RUN)

    result = invoke(["agentic", "prospects", "find-people", PROSPECT_ID, "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == RUN


def test_find_people_maps_a_running_search_to_exit_five(invoke, mock_api):
    mock_api.post(f"{BASE}/{PROSPECT_ID}/people/search").respond(
        409, json={"detail": SEARCH_RUNNING}
    )

    result = invoke(["agentic", "prospects", "find-people", PROSPECT_ID])

    assert result.exit_code == 5
    assert SEARCH_RUNNING in result.output


def test_find_people_maps_not_found_to_exit_three(invoke, mock_api):
    mock_api.post(f"{BASE}/{PROSPECT_ID}/people/search").respond(
        404, json={"detail": "prospect not found"}
    )

    result = invoke(["agentic", "prospects", "find-people", PROSPECT_ID])

    assert result.exit_code == 3
    assert "prospect not found" in result.output


def test_get_names_the_people_search_while_it_runs(invoke, mock_api):
    detail = {
        "id": PROSPECT_ID,
        "company_domain": "acme.test",
        "review_state": "new",
        "people_state": "pending",
        "people_search_run_id": RUN_ID,
    }
    mock_api.get(f"{BASE}/{PROSPECT_ID}").respond(200, json=detail)

    result = invoke(["agentic", "prospects", "get", PROSPECT_ID])

    assert result.exit_code == 0
    assert RUN_ID in result.output
