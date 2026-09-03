"""Tests for the agentic saved-search commands."""

import json

BASE = "/api/v1/agentic/saved-searches"
SEARCH_ID = "11111111-1111-4111-8111-111111111111"
RUN_ID = "22222222-2222-4222-8222-222222222222"
DEFINITION_ID = "33333333-3333-4333-8333-333333333333"

SUMMARY = {
    "id": SEARCH_ID,
    "name": "UK fintech",
    "last_run_id": RUN_ID,
    "last_run_at": "2026-08-28T10:00:00Z",
    "created_at": "2026-08-28T09:00:00Z",
    "updated_at": "2026-08-28T10:00:00.123456Z",
}
BRIEF = {
    "icp": "UK fintech",
    "region": "UK",
    "persona": {"titles": ["CTO", "CEO"], "country_codes": ["GB"]},
}
DETAIL = {**SUMMARY, "brief": BRIEF}
RUN = {
    "id": RUN_ID,
    "definition_id": DEFINITION_ID,
    "definition_name": "Signals Search",
    "status": "queued",
    "outcome": "started",
}
PROSPECT = {
    "id": "44444444-4444-4444-8444-444444444444",
    "company_name": "Acme",
    "company_domain": "acme.test",
    "review_state": "new",
    "opportunity_score": 80,
    "opportunity_reason": "Good fit",
    "recommended_action": "Review",
    "people_state": "pending",
    "people_state_reason": None,
    "crm_company_id": None,
    "first_seen_at": "2026-08-28T10:00:00Z",
    "last_seen_at": "2026-08-28T10:00:00Z",
    "created_at": "2026-08-28T10:00:00Z",
    "updated_at": "2026-08-28T10:00:00Z",
}
DIFF_ITEM = {
    "change_kinds": ["new", "new_signals"],
    "first_seen_at": "2026-08-28T10:00:00Z",
    "last_seen_at": "2026-08-28T10:00:00Z",
    "prospect": PROSPECT,
}


def test_create_sends_name_and_full_brief(invoke, mock_api):
    route = mock_api.post(BASE).respond(201, json=DETAIL)

    result = invoke(
        [
            "agentic",
            "saved-searches",
            "create",
            "--name",
            "UK fintech",
            "--brief",
            json.dumps(BRIEF),
        ]
    )

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {"name": "UK fintech", "brief": BRIEF}
    assert "UK fintech" in result.output
    assert "region" in result.output


def test_create_json_keeps_the_detail(invoke, mock_api):
    mock_api.post(BASE).respond(201, json=DETAIL)

    result = invoke(
        [
            "agentic",
            "saved-searches",
            "create",
            "--name",
            "UK fintech",
            "--brief",
            json.dumps(BRIEF),
            "--json",
        ]
    )

    assert json.loads(result.output) == DETAIL


def test_create_refuses_non_object_brief_before_request(invoke, mock_api):
    route = mock_api.post(BASE).respond(201, json=DETAIL)

    result = invoke(
        [
            "agentic",
            "saved-searches",
            "create",
            "--name",
            "UK fintech",
            "--brief",
            "[]",
            "--json",
        ]
    )

    assert result.exit_code == 2
    assert json.loads(result.output)["detail"].startswith("--brief")
    assert not route.called


def test_create_refuses_invalid_json_before_request(invoke, mock_api):
    route = mock_api.post(BASE).respond(201, json=DETAIL)

    result = invoke(
        [
            "agentic",
            "saved-searches",
            "create",
            "--name",
            "UK fintech",
            "--brief",
            "not-json",
        ]
    )

    assert result.exit_code == 2
    assert "--brief is not valid JSON" in result.output
    assert not route.called


def test_list_sends_page_options_and_prints_summary(invoke, mock_api):
    route = mock_api.get(BASE).respond(200, json={"items": [SUMMARY], "next_cursor": "next"})

    result = invoke(
        [
            "agentic",
            "saved-searches",
            "list",
            "--cursor",
            "current",
            "--limit",
            "10",
        ]
    )

    assert result.exit_code == 0
    assert "UK fintech" in result.output
    assert "--limit 10 --cursor next" in result.output
    params = route.calls[0].request.url.params
    assert params["cursor"] == "current"
    assert params["limit"] == "10"


def test_list_forwards_an_empty_cursor_for_api_validation(invoke, mock_api):
    route = mock_api.get(BASE).respond(400, json={"detail": "cursor is empty"})

    result = invoke(["agentic", "saved-searches", "list", "--cursor", ""])

    assert result.exit_code == 1
    assert route.calls[0].request.url.params["cursor"] == ""


def test_list_refuses_invalid_limit_before_request(invoke, mock_api):
    route = mock_api.get(BASE).respond(200, json={"items": [], "next_cursor": None})

    result = invoke(["agentic", "saved-searches", "list", "--limit", "101", "--json"])

    assert result.exit_code == 2
    assert json.loads(result.output)["detail"].startswith("--limit")
    assert not route.called


def test_list_json_keeps_the_page(invoke, mock_api):
    page = {"items": [SUMMARY], "next_cursor": "next"}
    mock_api.get(BASE).respond(200, json=page)

    result = invoke(["agentic", "saved-searches", "list", "--json"])

    assert json.loads(result.output) == page


def test_list_without_a_next_cursor_prints_no_hint(invoke, mock_api):
    mock_api.get(BASE).respond(200, json={"items": [], "next_cursor": None})

    result = invoke(["agentic", "saved-searches", "list"])

    assert result.exit_code == 0
    assert "Next page" not in result.output


def test_get_prints_detail_and_full_brief(invoke, mock_api):
    mock_api.get(f"{BASE}/{SEARCH_ID}").respond(200, json=DETAIL)

    result = invoke(["agentic", "saved-searches", "get", SEARCH_ID])

    assert result.exit_code == 0
    assert "UK fintech" in result.output
    assert "region" in result.output


def test_get_json_keeps_detail(invoke, mock_api):
    mock_api.get(f"{BASE}/{SEARCH_ID}").respond(200, json=DETAIL)

    result = invoke(["agentic", "saved-searches", "get", SEARCH_ID, "--json"])

    assert json.loads(result.output) == DETAIL


def test_get_maps_not_found_to_exit_three(invoke, mock_api):
    mock_api.get(f"{BASE}/{SEARCH_ID}").respond(404, json={"detail": "saved search not found"})

    result = invoke(["agentic", "saved-searches", "get", SEARCH_ID])

    assert result.exit_code == 3


def test_patch_sends_only_named_fields_and_opaque_token(invoke, mock_api):
    route = mock_api.patch(f"{BASE}/{SEARCH_ID}").respond(200, json=DETAIL)

    result = invoke(
        [
            "agentic",
            "saved-searches",
            "patch",
            SEARCH_ID,
            "--expected-updated-at",
            "opaque-token",
            "--brief",
            '{"company_criteria":["fintech"]}',
        ]
    )

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {
        "expected_updated_at": "opaque-token",
        "brief": {"company_criteria": ["fintech"]},
    }


def test_patch_can_rename_without_replacing_brief(invoke, mock_api):
    route = mock_api.patch(f"{BASE}/{SEARCH_ID}").respond(200, json=DETAIL)

    result = invoke(
        [
            "agentic",
            "saved-searches",
            "patch",
            SEARCH_ID,
            "--expected-updated-at",
            "opaque-token",
            "--name",
            "New name",
            "--json",
        ]
    )

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {
        "expected_updated_at": "opaque-token",
        "name": "New name",
    }
    assert json.loads(result.output) == DETAIL


def test_patch_refuses_no_change_before_request(invoke, mock_api):
    route = mock_api.patch(f"{BASE}/{SEARCH_ID}").respond(200, json=DETAIL)

    result = invoke(
        [
            "agentic",
            "saved-searches",
            "patch",
            SEARCH_ID,
            "--expected-updated-at",
            "opaque-token",
            "--json",
        ]
    )

    assert result.exit_code == 2
    assert "--name or --brief" in json.loads(result.output)["detail"]
    assert not route.called


def test_delete_asks_for_confirmation(invoke, mock_api):
    route = mock_api.delete(f"{BASE}/{SEARCH_ID}").respond(204)

    result = invoke(["agentic", "saved-searches", "delete", SEARCH_ID], input="n\n")

    assert result.exit_code == 1
    assert not route.called


def test_delete_with_yes_and_json(invoke, mock_api):
    route = mock_api.delete(f"{BASE}/{SEARCH_ID}").respond(204)

    result = invoke(["agentic", "saved-searches", "delete", SEARCH_ID, "--yes", "--json"])

    assert route.called
    assert json.loads(result.output) == {"id": SEARCH_ID, "deleted": True}


def test_delete_with_yes_prints_success(invoke, mock_api):
    mock_api.delete(f"{BASE}/{SEARCH_ID}").respond(204)

    result = invoke(["agentic", "saved-searches", "delete", SEARCH_ID, "--yes"])

    assert result.exit_code == 0
    assert "Saved search deleted" in result.output


def test_start_sends_contract_version_and_given_key(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{SEARCH_ID}/runs").respond(200, json=RUN)

    result = invoke(
        [
            "agentic",
            "saved-searches",
            "start",
            SEARCH_ID,
            "--contract-version",
            "1",
            "--idempotency-key",
            "delivery-1",
        ]
    )

    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {"contract_version": 1}
    assert route.calls[0].request.headers["Idempotency-Key"] == "delivery-1"
    assert RUN_ID in result.output


def test_start_requires_version_and_key(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{SEARCH_ID}/runs").respond(200, json=RUN)

    missing_version = invoke(
        ["agentic", "saved-searches", "start", SEARCH_ID, "--idempotency-key", "key"]
    )
    missing_key = invoke(
        ["agentic", "saved-searches", "start", SEARCH_ID, "--contract-version", "1"]
    )

    assert missing_version.exit_code == 2
    assert missing_key.exit_code == 2
    assert not route.called


def test_start_refuses_invalid_version_and_key_before_request(invoke, mock_api):
    route = mock_api.post(f"{BASE}/{SEARCH_ID}/runs").respond(200, json=RUN)
    base = [
        "agentic",
        "saved-searches",
        "start",
        SEARCH_ID,
        "--contract-version",
        "1",
        "--idempotency-key",
        "delivery-1",
        "--json",
    ]

    for flag, value in (
        ("--contract-version", "0"),
        ("--idempotency-key", " "),
        ("--idempotency-key", " delivery-1"),
        ("--idempotency-key", "delivery-1 "),
        ("--idempotency-key", "x" * 201),
        ("--idempotency-key", "é"),
    ):
        args = base.copy()
        args[args.index(flag) + 1] = value
        result = invoke(args)
        assert result.exit_code == 2
        assert json.loads(result.output)["error"] is True
    assert not route.called


def test_start_json_keeps_run_detail(invoke, mock_api):
    mock_api.post(f"{BASE}/{SEARCH_ID}/runs").respond(200, json=RUN)

    result = invoke(
        [
            "agentic",
            "saved-searches",
            "start",
            SEARCH_ID,
            "--contract-version",
            "1",
            "--idempotency-key",
            "delivery-1",
            "--json",
        ]
    )

    assert json.loads(result.output) == RUN


def test_start_reports_duplicate_run(invoke, mock_api):
    mock_api.post(f"{BASE}/{SEARCH_ID}/runs").respond(200, json={**RUN, "outcome": "duplicate"})

    result = invoke(
        [
            "agentic",
            "saved-searches",
            "start",
            SEARCH_ID,
            "--contract-version",
            "1",
            "--idempotency-key",
            "delivery-1",
        ]
    )

    assert "Duplicate" in result.output


def test_start_maps_in_progress_to_conflict_exit(invoke, mock_api):
    mock_api.post(f"{BASE}/{SEARCH_ID}/runs").respond(
        409, json={"detail": {"code": "start_in_progress"}}
    )

    result = invoke(
        [
            "agentic",
            "saved-searches",
            "start",
            SEARCH_ID,
            "--contract-version",
            "1",
            "--idempotency-key",
            "delivery-1",
            "--json",
        ]
    )

    assert result.exit_code == 5
    assert json.loads(result.output)["detail"]["code"] == "start_in_progress"


def test_diff_prints_nested_prospect_and_change_reasons(invoke, mock_api, table_column):
    route = mock_api.get(f"{BASE}/{SEARCH_ID}/diff").respond(
        200,
        json={"run_id": RUN_ID, "items": [DIFF_ITEM], "next_cursor": "next"},
    )

    result = invoke(
        [
            "agentic",
            "saved-searches",
            "diff",
            SEARCH_ID,
            "--cursor",
            "current",
            "--limit",
            "5",
        ]
    )

    assert result.exit_code == 0
    assert "Acme" in result.output
    assert "new_signals" in table_column(result.output, 3)
    assert RUN_ID in result.output
    assert "--limit 5 --cursor next" in result.output
    assert route.calls[0].request.url.params["cursor"] == "current"


def test_diff_prints_no_publish_state(invoke, mock_api):
    mock_api.get(f"{BASE}/{SEARCH_ID}/diff").respond(
        200, json={"run_id": None, "items": [], "next_cursor": None}
    )

    result = invoke(["agentic", "saved-searches", "diff", SEARCH_ID])

    assert result.exit_code == 0
    assert "No published run" in result.output


def test_diff_json_keeps_nested_page(invoke, mock_api):
    page = {"run_id": RUN_ID, "items": [DIFF_ITEM], "next_cursor": None}
    mock_api.get(f"{BASE}/{SEARCH_ID}/diff").respond(200, json=page)

    result = invoke(["agentic", "saved-searches", "diff", SEARCH_ID, "--json"])

    assert json.loads(result.output) == page


def test_diff_maps_changed_snapshot_to_conflict_exit(invoke, mock_api):
    mock_api.get(f"{BASE}/{SEARCH_ID}/diff").respond(
        409, json={"detail": "the latest diff changed"}
    )

    result = invoke(["agentic", "saved-searches", "diff", SEARCH_ID])

    assert result.exit_code == 5
