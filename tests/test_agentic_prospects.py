"""Tests for the agentic prospect review commands."""

import json

BASE = "/api/v1/agentic/prospects"
PROSPECT_ID = "11111111-1111-4111-8111-111111111111"

SUMMARY = {
    "id": PROSPECT_ID,
    "company_name": None,
    "company_domain": "acme.test",
    "review_state": "new",
    "opportunity_score": None,
    "opportunity_reason": None,
    "recommended_action": None,
    "people_state": "pending",
    "people_state_reason": None,
    "crm_company_id": None,
    "first_seen_at": "2026-08-28T10:00:00Z",
    "last_seen_at": "2026-08-28T10:00:00Z",
    "created_at": "2026-08-28T10:00:00Z",
    "updated_at": "2026-08-28T10:00:00Z",
}
DETAIL = {
    **SUMMARY,
    "company": {
        "id": "22222222-2222-4222-8222-222222222222",
        "linkedin_url": None,
        "website": "https://acme.test",
        "industry": "Software",
        "sub_industry": None,
        "business_model": "B2B",
        "location": "London",
        "employee_count_exact": None,
        "employee_count_band": "51-200",
        "annual_revenue": None,
        "revenue_band": None,
        "revenue_currency": None,
        "revenue_year": None,
        "funding_round": None,
        "funding_amount": None,
        "fetched_cold_at": None,
        "fetched_warm_at": None,
        "fetched_hot_at": None,
        "last_enriched_at": "2026-08-28T10:00:00Z",
    },
}
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
        "linkedin_url": "https://linkedin.com/in/alice",
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
SIGNAL = {
    "id": "55555555-5555-4555-8555-555555555555",
    "prospect_id": PROSPECT_ID,
    "signal_score": None,
    "signal_reason": None,
    "first_seen_at": "2026-08-28T10:00:00Z",
    "created_at": "2026-08-28T10:00:00Z",
    "updated_at": "2026-08-28T10:00:00Z",
    "signal": {
        "id": "66666666-6666-4666-8666-666666666666",
        "subject_type": "company",
        "subject_id": "22222222-2222-4222-8222-222222222222",
        "signal_type": "funding",
        "description": "Raised a Series A",
        "observed_at": "2026-08-28T10:00:00Z",
        "ingested_at": "2026-08-28T10:00:00Z",
        "source": None,
    },
}


def test_list_defaults_to_new_and_prints_partial_rows(invoke, mock_api):
    route = mock_api.get(BASE).respond(200, json={"items": [SUMMARY], "next_cursor": None})

    result = invoke(["agentic", "prospects", "list"])

    assert result.exit_code == 0
    assert "acme.test" in result.output
    assert route.calls[0].request.url.params["review_state"] == "new"
    assert route.calls[0].request.url.params["limit"] == "50"


def test_list_forwards_filter_cursor_and_limit(invoke, mock_api):
    route = mock_api.get(BASE).respond(200, json={"items": [], "next_cursor": "next"})

    result = invoke(
        [
            "agentic",
            "prospects",
            "list",
            "--review-state",
            "watching",
            "--cursor",
            "current",
            "--limit",
            "10",
        ]
    )

    params = route.calls[0].request.url.params
    assert params["review_state"] == "watching"
    assert params["cursor"] == "current"
    assert params["limit"] == "10"
    assert "--review-state watching --limit 10 --cursor next" in result.output


def test_list_json_keeps_the_page(invoke, mock_api):
    page = {"items": [SUMMARY], "next_cursor": "next"}
    mock_api.get(BASE).respond(200, json=page)

    result = invoke(["agentic", "prospects", "list", "--json"])

    assert json.loads(result.output) == page


def test_list_refuses_a_limit_before_the_request(invoke, mock_api):
    route = mock_api.get(BASE).respond(200, json={"items": [], "next_cursor": None})

    result = invoke(["agentic", "prospects", "list", "--limit", "0", "--json"])

    assert result.exit_code == 2
    assert json.loads(result.output)["detail"].startswith("--limit")
    assert not route.called


def test_list_forwards_an_explicit_empty_cursor_for_api_validation(invoke, mock_api):
    route = mock_api.get(BASE).respond(400, json={"detail": "cursor is empty"})

    result = invoke(["agentic", "prospects", "list", "--cursor", ""])

    assert result.exit_code == 1
    assert "cursor" in route.calls[0].request.url.params
    assert route.calls[0].request.url.params["cursor"] == ""


def test_get_prints_the_prospect_and_company(invoke, mock_api):
    route = mock_api.get(f"{BASE}/{PROSPECT_ID}").respond(200, json=DETAIL)

    result = invoke(["agentic", "prospects", "get", PROSPECT_ID])

    assert result.exit_code == 0
    assert route.called
    assert "Software" in result.output
    assert "acme.test" in result.output


def test_get_json_keeps_the_nested_company(invoke, mock_api):
    mock_api.get(f"{BASE}/{PROSPECT_ID}").respond(200, json=DETAIL)

    result = invoke(["agentic", "prospects", "get", PROSPECT_ID, "--json"])

    assert json.loads(result.output) == DETAIL


def test_get_maps_not_found_to_exit_three(invoke, mock_api):
    mock_api.get(f"{BASE}/{PROSPECT_ID}").respond(404, json={"detail": "prospect not found"})

    assert invoke(["agentic", "prospects", "get", PROSPECT_ID]).exit_code == 3


def test_people_prints_nested_person_fields(invoke, mock_api):
    route = mock_api.get(f"{BASE}/{PROSPECT_ID}/people").respond(
        200, json={"items": [PERSON], "next_cursor": "next"}
    )

    result = invoke(
        [
            "agentic",
            "prospects",
            "people",
            PROSPECT_ID,
            "--cursor",
            "current",
            "--limit",
            "5",
        ]
    )

    assert "Alice Doe" in result.output
    assert "CFO" in result.output
    assert route.calls[0].request.url.params["cursor"] == "current"
    assert "--limit 5 --cursor next" in result.output


def test_people_json_keeps_the_page(invoke, mock_api):
    page = {"items": [PERSON], "next_cursor": None}
    mock_api.get(f"{BASE}/{PROSPECT_ID}/people").respond(200, json=page)

    result = invoke(["agentic", "prospects", "people", PROSPECT_ID, "--json"])

    assert json.loads(result.output) == page


def test_signals_prints_a_signal_with_no_source(invoke, mock_api):
    route = mock_api.get(f"{BASE}/{PROSPECT_ID}/signals").respond(
        200, json={"items": [SIGNAL], "next_cursor": "next"}
    )

    result = invoke(["agentic", "prospects", "signals", PROSPECT_ID, "--limit", "5"])

    assert result.exit_code == 0
    assert "funding" in result.output
    assert "Raised a Series A" in result.output
    assert route.calls[0].request.url.params["limit"] == "5"
    assert "--limit 5 --cursor next" in result.output


def test_signals_json_keeps_the_page(invoke, mock_api):
    page = {"items": [SIGNAL], "next_cursor": None}
    mock_api.get(f"{BASE}/{PROSPECT_ID}/signals").respond(200, json=page)

    result = invoke(["agentic", "prospects", "signals", PROSPECT_ID, "--json"])

    assert json.loads(result.output) == page


def test_watch_posts_the_intent_and_prints_durable_state(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{PROSPECT_ID}/watch").respond(
        200, json={**DETAIL, "review_state": "watching"}
    )

    result = invoke(["agentic", "prospects", "watch", PROSPECT_ID])

    assert result.exit_code == 0
    assert "watching" in result.output
    assert "Idempotency-Key" not in route.calls[0].request.headers


def test_dismiss_json_keeps_the_durable_detail(invoke, mock_api):
    detail = {**DETAIL, "review_state": "dismissed"}
    mock_api.post(f"{BASE}/{PROSPECT_ID}/dismiss").respond(200, json=detail)

    result = invoke(["agentic", "prospects", "dismiss", PROSPECT_ID, "--json"])

    assert json.loads(result.output) == detail


def test_watch_json_keeps_the_durable_detail(invoke, mock_api):
    detail = {**DETAIL, "review_state": "watching"}
    mock_api.post(f"{BASE}/{PROSPECT_ID}/watch").respond(200, json=detail)

    result = invoke(["agentic", "prospects", "watch", PROSPECT_ID, "--json"])

    assert json.loads(result.output) == detail


def test_dismiss_prints_the_durable_state(invoke, mock_api):
    mock_api.post(f"{BASE}/{PROSPECT_ID}/dismiss").respond(
        200, json={**DETAIL, "review_state": "dismissed"}
    )

    result = invoke(["agentic", "prospects", "dismiss", PROSPECT_ID])

    assert result.exit_code == 0
    assert "dismissed" in result.output


def test_curation_maps_promoted_to_exit_five(invoke, mock_api):
    mock_api.post(f"{BASE}/{PROSPECT_ID}/watch").respond(
        409, json={"detail": "a promoted prospect cannot be watched or dismissed"}
    )

    assert invoke(["agentic", "prospects", "watch", PROSPECT_ID]).exit_code == 5


def test_prospects_help_lists_the_six_commands(invoke):
    result = invoke(["agentic", "prospects", "--help"])

    assert result.exit_code == 0
    for command in ("list", "get", "people", "signals", "watch", "dismiss"):
        assert command in result.output


PROMOTION = {
    "prospect_id": PROSPECT_ID,
    "review_state": "promoted",
    "crm_company_id": "55555555-5555-4555-8555-555555555555",
    "people": [
        {
            "prospect_person_id": "33333333-3333-4333-8333-333333333333",
            "intel_person_id": "44444444-4444-4444-8444-444444444444",
            "crm_person_id": "66666666-6666-4666-8666-666666666666",
        }
    ],
    "list_id": None,
}


def test_promote_posts_the_selection_and_prints_the_references(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{PROSPECT_ID}/promote").respond(200, json=PROMOTION)

    result = invoke(
        [
            "agentic",
            "prospects",
            "promote",
            PROSPECT_ID,
            "--person",
            "33333333-3333-4333-8333-333333333333",
            "--yes",
        ]
    )

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {
        "person_ids": ["33333333-3333-4333-8333-333333333333"],
        "list_id": None,
    }
    assert "promoted" in result.output


def test_promote_sends_the_list_and_an_empty_selection(invoke, mock_api):
    list_id = "77777777-7777-4777-8777-777777777777"
    route = mock_api.post(f"{BASE}/{PROSPECT_ID}/promote").respond(
        200, json={**PROMOTION, "people": [], "list_id": list_id}
    )

    result = invoke(["agentic", "prospects", "promote", PROSPECT_ID, "--list", list_id, "--yes"])

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {
        "person_ids": [],
        "list_id": list_id,
    }


def test_promote_json_keeps_the_whole_answer(invoke, mock_api):
    mock_api.post(f"{BASE}/{PROSPECT_ID}/promote").respond(200, json=PROMOTION)

    result = invoke(["agentic", "prospects", "promote", PROSPECT_ID, "--yes", "--json"])

    assert json.loads(result.output) == PROMOTION


def test_promote_asks_before_it_writes_crm(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{PROSPECT_ID}/promote").respond(200, json=PROMOTION)

    result = invoke(["agentic", "prospects", "promote", PROSPECT_ID], input="n\n")

    assert result.exit_code != 0
    assert not route.calls


def test_promote_reports_a_conflict(invoke, mock_api):
    mock_api.post(f"{BASE}/{PROSPECT_ID}/promote").respond(
        409, json={"detail": "The person cannot resolve"}
    )

    result = invoke(["agentic", "prospects", "promote", PROSPECT_ID, "--yes"])

    assert result.exit_code != 0
    assert "cannot resolve" in result.output
