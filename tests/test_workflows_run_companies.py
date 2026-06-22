"""Tests for workflow run-companies commands."""

import json

SAMPLE_COMPANY = {
    "id": "wrc-1",
    "name": "Acme Corp",
    "industry": "SaaS",
    "location": "San Francisco",
    "website": "https://acme.com",
    "created_at": "2026-01-01T00:00:00Z",
}


def test_run_companies_list(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/companies").respond(
        200,
        json={
            "data": [SAMPLE_COMPANY],
            "total": 1,
            "limit": 50,
            "offset": 0,
            "has_more": False,
        },
    )
    result = invoke(["workflows", "run-companies", "list", "wf-1"])
    assert result.exit_code == 0
    assert "Acme Corp" in result.output


def test_run_companies_list_json(invoke, mock_api):
    payload = {"data": [SAMPLE_COMPANY], "total": 1, "limit": 50, "offset": 0, "has_more": False}
    mock_api.get("/api/v1/workflows/wf-1/runs/companies").respond(200, json=payload)
    result = invoke(["workflows", "run-companies", "list", "wf-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["name"] == "Acme Corp"


def test_run_companies_list_by_run(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/run-1/companies").respond(200, json=[SAMPLE_COMPANY])
    result = invoke(["workflows", "run-companies", "list-by-run", "wf-1", "run-1"])
    assert result.exit_code == 0
    assert "Acme Corp" in result.output


def test_run_companies_list_sort_by_lead_score(invoke, mock_api):
    """--sort-by lead_score passes through as query param."""
    route = mock_api.get("/api/v1/workflows/wf-1/runs/companies").respond(
        200, json={"data": [], "total": 0, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(
        ["workflows", "run-companies", "list", "wf-1", "--sort-by", "lead_score", "--json"]
    )
    assert result.exit_code == 0
    assert "sort_by=lead_score" in str(route.calls.last.request.url)


def test_run_companies_add_to_crm(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/runs/companies/add-to-crm").respond(
        200,
        json={
            "added_count": 2,
            "updated_count": 0,
            "skipped_count": 1,
            "synced_count": 2,
            "company_ids": ["c-1", "c-2"],
        },
    )
    result = invoke(
        ["workflows", "run-companies", "add-to-crm", "wf-1", "--company-ids", "wrc-1,wrc-2,wrc-3"]
    )
    assert result.exit_code == 0
    assert "Synced 2 companies" in result.output


def test_run_companies_add_to_crm_reports_synced_when_existing_unlinked(invoke, mock_api):
    # ENG-1506: companies already in the CRM but unlinked are merged + linked
    # (counted in updated_count), so the headline must be the synced total,
    # not added_count (0).
    mock_api.post("/api/v1/workflows/wf-1/runs/companies/add-to-crm").respond(
        200,
        json={
            "added_count": 0,
            "updated_count": 2,
            "skipped_count": 0,
            "synced_count": 2,
            "company_ids": ["c-1", "c-2"],
        },
    )
    result = invoke(
        ["workflows", "run-companies", "add-to-crm", "wf-1", "--company-ids", "wrc-1,wrc-2"]
    )
    assert result.exit_code == 0
    assert "Synced 2 companies" in result.output


def test_run_companies_add_to_crm_json(invoke, mock_api):
    payload = {
        "added_count": 1,
        "updated_count": 0,
        "skipped_count": 0,
        "synced_count": 1,
        "company_ids": ["c-1"],
    }
    mock_api.post("/api/v1/workflows/wf-1/runs/companies/add-to-crm").respond(200, json=payload)
    result = invoke(
        ["workflows", "run-companies", "add-to-crm", "wf-1", "--company-ids", "wrc-1", "--json"]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["added_count"] == 1
    assert parsed["synced_count"] == 1


def test_run_companies_add_to_list(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/runs/companies/add-to-list").respond(
        200,
        json={
            "synced_count": 1,
            "added_count": 2,
            "already_member_count": 0,
            "skipped_deleted_ids": [],
        },
    )
    result = invoke(
        [
            "workflows",
            "run-companies",
            "add-to-list",
            "wf-1",
            "--company-ids",
            "wrc-1,wrc-2",
            "--list-id",
            "list-1",
        ]
    )
    assert result.exit_code == 0
    assert "Added 2 companies to list" in result.output


def test_run_companies_add_to_list_json(invoke, mock_api):
    payload = {
        "synced_count": 1,
        "added_count": 1,
        "already_member_count": 0,
        "skipped_deleted_ids": ["wrc-x"],
    }
    mock_api.post("/api/v1/workflows/wf-1/runs/companies/add-to-list").respond(200, json=payload)
    result = invoke(
        [
            "workflows",
            "run-companies",
            "add-to-list",
            "wf-1",
            "--company-ids",
            "wrc-1",
            "--list-id",
            "list-1",
            "--json",
        ]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["skipped_deleted_ids"] == ["wrc-x"]


def test_run_companies_add_to_list_error(invoke, mock_api):
    """API 422 returns exit code 2."""
    mock_api.post("/api/v1/workflows/wf-1/runs/companies/add-to-list").respond(
        422, json={"detail": "Invalid company IDs"}
    )
    result = invoke(
        [
            "workflows",
            "run-companies",
            "add-to-list",
            "wf-1",
            "--company-ids",
            "bad",
            "--list-id",
            "list-1",
        ]
    )
    assert result.exit_code == 2


def test_run_companies_crm_count(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/companies/added-to-crm-count").respond(
        200, json={"count": 5}
    )
    result = invoke(["workflows", "run-companies", "crm-count", "wf-1"])
    assert result.exit_code == 0
    assert "5" in result.output


def test_run_companies_crm_count_json(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/companies/added-to-crm-count").respond(
        200, json={"count": 5}
    )
    result = invoke(["workflows", "run-companies", "crm-count", "wf-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["count"] == 5


def test_run_companies_delete_with_yes(invoke, mock_api):
    mock_api.route(method="DELETE", url="/api/v1/workflows/wf-1/runs/companies").respond(
        200, json={"deleted_count": 2}
    )
    result = invoke(
        ["workflows", "run-companies", "delete", "wf-1", "--company-ids", "wrc-1,wrc-2", "--yes"]
    )
    assert result.exit_code == 0
    assert "Deleted 2" in result.output


def test_run_companies_delete_aborted(invoke, mock_api):
    result = invoke(
        ["workflows", "run-companies", "delete", "wf-1", "--company-ids", "wrc-1"],
        input="n\n",
    )
    assert result.exit_code == 1


def test_run_companies_delete_json(invoke, mock_api):
    mock_api.route(method="DELETE", url="/api/v1/workflows/wf-1/runs/companies").respond(
        200, json={"deleted_count": 1}
    )
    result = invoke(
        [
            "workflows",
            "run-companies",
            "delete",
            "wf-1",
            "--company-ids",
            "wrc-1",
            "--yes",
            "--json",
        ]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["deleted_count"] == 1


def test_run_companies_list_not_found(invoke, mock_api):
    """Workflow not found returns exit code 3."""
    mock_api.get("/api/v1/workflows/bad-wf/runs/companies").respond(
        404, json={"detail": "Workflow not found"}
    )
    result = invoke(["workflows", "run-companies", "list", "bad-wf"])
    assert result.exit_code == 3
    assert "404" in result.output


def test_run_companies_list_not_found_json(invoke, mock_api):
    """Workflow not found with --json returns structured JSON error."""
    mock_api.get("/api/v1/workflows/bad-wf/runs/companies").respond(
        404, json={"detail": "Workflow not found"}
    )
    result = invoke(["workflows", "run-companies", "list", "bad-wf", "--json"])
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 404


def test_run_companies_add_to_crm_error(invoke, mock_api):
    """API 422 returns exit code 2."""
    mock_api.post("/api/v1/workflows/wf-1/runs/companies/add-to-crm").respond(
        422, json={"detail": "Invalid company IDs"}
    )
    result = invoke(["workflows", "run-companies", "add-to-crm", "wf-1", "--company-ids", "bad"])
    assert result.exit_code == 2
