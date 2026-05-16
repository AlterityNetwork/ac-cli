"""Tests for `ac admin searches` commands."""

import json

SAMPLE_SUMMARY = {
    "total_runs": 12,
    "completed_runs": 10,
    "failed_runs": 2,
    "success_rate": 83.3,
    "total_companies": 80,
    "total_people": 30,
    "avg_lead_score": 72.5,
    "avg_relevance_score": 65.0,
    "by_day": [],
    "by_source": {
        "sonar": {
            "total_runs": 8,
            "completed_runs": 8,
            "failed_runs": 0,
            "total_companies": 80,
            "total_people": 0,
        },
        "headhunter": {
            "total_runs": 4,
            "completed_runs": 2,
            "failed_runs": 2,
            "total_companies": 0,
            "total_people": 30,
        },
    },
    "change_total_runs": 25.0,
    "change_total_companies": 10.0,
    "change_total_people": 50.0,
}


SAMPLE_RUNS_PAGE_FULL = {
    "items": [
        {
            "id": f"run-{i}",
            "workflow_id": "wf-1",
            "organization_id": "org-1",
            "user_id": "user-1",
            "source": "sonar",
            "status": "completed",
            "started_at": "2026-04-20T10:00:00Z",
            "companies_count": 5,
            "people_count": 0,
        }
        for i in range(100)
    ],
    "total_count": 250,
    "page": 1,
    "page_size": 100,
}


SAMPLE_RUNS_PAGE_SHORT = {
    "items": [
        {
            "id": f"run-{i}",
            "workflow_id": "wf-1",
            "organization_id": "org-1",
            "user_id": "user-1",
            "source": "sonar",
            "status": "completed",
            "started_at": "2026-04-20T10:00:00Z",
            "companies_count": 1,
            "people_count": 0,
        }
        for i in range(20)
    ],
    "total_count": 220,
    "page": 2,
    "page_size": 100,
}


SAMPLE_RUN_DETAIL = {
    "id": "run-1",
    "workflow_id": "wf-1",
    "organization_id": "org-1",
    "user_id": "user-1",
    "source": "headhunter",
    "status": "completed",
    "started_at": "2026-04-20T10:00:00Z",
    "completed_at": "2026-04-20T10:02:30Z",
    "duration_ms": 150000,
    "companies_count": 12,
    "people_count": 45,
    "error_message": None,
    "trigger_data": {"search_query": "VPs of Eng"},
    "snapshot_definition": {"nodes": [], "edges": []},
}


SAMPLE_COMPANIES = {
    "items": [
        {
            "id": "c1",
            "workflow_run_id": "r1",
            "workflow_id": "w1",
            "organization_id": "org-1",
            "user_id": "user-1",
            "source_workflow_type": "sonar",
            "name": "Acme",
            "website": "acme.com",
            "lead_score": 85,
            "country": "US",
            "discovered_at": "2026-04-20T10:01:00Z",
        }
    ],
    "total_count": 1,
    "page": 1,
    "page_size": 25,
}


SAMPLE_PEOPLE = {
    "items": [
        {
            "id": "p1",
            "workflow_run_id": "r1",
            "workflow_id": "w1",
            "organization_id": "org-1",
            "user_id": "user-1",
            "current_title": "VP Engineering",
            "current_company_text": "Acme",
            "country": "US",
            "relevance_score": 90,
            "email_score": 85,
            "discovered_at": "2026-04-20T10:01:00Z",
        }
    ],
    "total_count": 1,
    "page": 1,
    "page_size": 25,
}


def test_summary(invoke, mock_api):
    mock_api.get("/api/v1/admin/searches/summary").respond(200, json=SAMPLE_SUMMARY)
    result = invoke(["admin", "searches", "summary"])
    assert result.exit_code == 0
    assert "12" in result.output
    assert "Sonar" in result.output or "sonar" in result.output


def test_summary_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/searches/summary").respond(200, json=SAMPLE_SUMMARY)
    result = invoke(["admin", "searches", "summary", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["total_runs"] == 12
    assert parsed["by_source"]["sonar"]["total_runs"] == 8


def test_summary_passes_source_filter(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/searches/summary").respond(200, json=SAMPLE_SUMMARY)
    result = invoke(["admin", "searches", "summary", "--source", "headhunter"])
    assert result.exit_code == 0
    assert route.calls.last.request.url.params["source"] == "headhunter"


def test_runs_table(invoke, mock_api):
    mock_api.get("/api/v1/admin/searches/runs").respond(
        200, json={**SAMPLE_RUNS_PAGE_FULL, "items": SAMPLE_RUNS_PAGE_FULL["items"][:1]}
    )
    result = invoke(["admin", "searches", "runs"])
    assert result.exit_code == 0
    assert "run-0" in result.output


def test_runs_json_with_multi_value_filters(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/searches/runs").respond(
        200, json={**SAMPLE_RUNS_PAGE_FULL, "items": SAMPLE_RUNS_PAGE_FULL["items"][:2]}
    )
    result = invoke(
        [
            "admin",
            "searches",
            "runs",
            "--json",
            "--org-id",
            "org-a",
            "--org-id",
            "org-b",
            "--user-id",
            "u1",
            "--status",
            "completed",
            "-q",
            "VP",
        ]
    )
    assert result.exit_code == 0
    params = route.calls.last.request.url.params
    # Multi-value filters: respx exposes them as a multi-dict.
    assert params.get_list("organization_id") == ["org-a", "org-b"]
    assert params["user_id"] == "u1"
    assert params["status"] == "completed"
    assert params["q"] == "VP"


def test_runs_all_walks_pages(invoke, mock_api):
    """--all paginates until a short page is returned."""
    mock_api.get("/api/v1/admin/searches/runs", params={"page": "1", "page_size": "100"}).respond(
        200, json=SAMPLE_RUNS_PAGE_FULL
    )
    mock_api.get("/api/v1/admin/searches/runs", params={"page": "2", "page_size": "100"}).respond(
        200, json=SAMPLE_RUNS_PAGE_SHORT
    )

    result = invoke(["admin", "searches", "runs", "--all"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert len(parsed) == 120  # 100 + 20
    assert parsed[0]["id"] == "run-0"


def test_run_detail(invoke, mock_api):
    mock_api.get("/api/v1/admin/searches/runs/run-1").respond(200, json=SAMPLE_RUN_DETAIL)
    result = invoke(["admin", "searches", "run", "run-1"])
    assert result.exit_code == 0
    assert "run-1" in result.output
    assert "headhunter" in result.output


def test_run_detail_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/searches/runs/run-1").respond(200, json=SAMPLE_RUN_DETAIL)
    result = invoke(["admin", "searches", "run", "run-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "run-1"
    assert parsed["companies_count"] == 12


def test_companies(invoke, mock_api):
    mock_api.get("/api/v1/admin/searches/companies").respond(200, json=SAMPLE_COMPANIES)
    result = invoke(["admin", "searches", "companies", "--source", "sonar"])
    assert result.exit_code == 0
    assert "Acme" in result.output


def test_companies_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/searches/companies").respond(200, json=SAMPLE_COMPANIES)
    result = invoke(["admin", "searches", "companies", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["items"][0]["name"] == "Acme"


def test_people_excludes_pii(invoke, mock_api):
    mock_api.get("/api/v1/admin/searches/people").respond(200, json=SAMPLE_PEOPLE)
    result = invoke(["admin", "searches", "people", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    item = parsed["items"][0]
    # No PII keys.
    for forbidden in ("full_name", "email", "linkedin_url", "avatar_url"):
        assert forbidden not in item
    # Useful analysis fields are present.
    assert item["current_title"] == "VP Engineering"
    assert item["relevance_score"] == 90


def test_people_table(invoke, mock_api):
    mock_api.get("/api/v1/admin/searches/people").respond(200, json=SAMPLE_PEOPLE)
    result = invoke(["admin", "searches", "people"])
    assert result.exit_code == 0
    # Rich may wrap "VP Engineering" — match the company instead.
    assert "Acme" in result.output


def test_summary_403_returns_exit_4(invoke, mock_api):
    mock_api.get("/api/v1/admin/searches/summary").respond(403, json={"detail": "Superadmin only"})
    result = invoke(["admin", "searches", "summary", "--json"])
    assert result.exit_code == 4
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 403
