"""Tests for workflow run-people commands."""

import json

SAMPLE_PERSON = {
    "id": "wrp-1",
    "full_name": "Jane Smith",
    "email": "jane@acme.com",
    "current_title": "CTO",
    "current_company_text": "Acme Corp",
    "created_at": "2026-01-01T00:00:00Z",
}


def test_run_people_list(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/people").respond(
        200,
        json={
            "data": [SAMPLE_PERSON],
            "total": 1,
            "limit": 50,
            "offset": 0,
            "has_more": False,
        },
    )
    result = invoke(["workflows", "run-people", "list", "wf-1"])
    assert result.exit_code == 0
    assert "Jane Smith" in result.output


def test_run_people_list_json(invoke, mock_api):
    payload = {"data": [SAMPLE_PERSON], "total": 1, "limit": 50, "offset": 0, "has_more": False}
    mock_api.get("/api/v1/workflows/wf-1/runs/people").respond(200, json=payload)
    result = invoke(["workflows", "run-people", "list", "wf-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["full_name"] == "Jane Smith"


def test_run_people_list_by_run(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/run-1/people").respond(200, json=[SAMPLE_PERSON])
    result = invoke(["workflows", "run-people", "list-by-run", "wf-1", "run-1"])
    assert result.exit_code == 0
    assert "Jane Smith" in result.output


def test_run_people_company_match_preview(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/runs/people/company-match-preview").respond(
        200,
        json={
            "matches": [
                {
                    "company_text": "Acme Corp",
                    "person_count": 3,
                    "match_source": "crm",
                    "match_type": "exact",
                },
            ],
            "no_company_person_ids": ["wrp-5"],
        },
    )
    result = invoke(
        ["workflows", "run-people", "company-match-preview", "wf-1", "--person-ids", "wrp-1,wrp-2"]
    )
    assert result.exit_code == 0
    assert "Acme Corp" in result.output
    assert "1 people have no company" in result.output


def test_run_people_company_match_preview_json(invoke, mock_api):
    payload = {"matches": [], "no_company_person_ids": []}
    mock_api.post("/api/v1/workflows/wf-1/runs/people/company-match-preview").respond(
        200, json=payload
    )
    result = invoke(
        [
            "workflows",
            "run-people",
            "company-match-preview",
            "wf-1",
            "--person-ids",
            "wrp-1",
            "--json",
        ]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "matches" in parsed


def test_run_people_company_search(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/company-search").respond(
        200,
        json={
            "results": [
                {
                    "source": "crm",
                    "name": "Acme Corp",
                    "industry": "SaaS",
                    "location": "SF",
                    "id": "c-1",
                },
            ],
        },
    )
    result = invoke(["workflows", "run-people", "company-search", "wf-1", "--query", "acme"])
    assert result.exit_code == 0
    assert "Acme Corp" in result.output


def test_run_people_company_search_json(invoke, mock_api):
    payload = {"results": []}
    mock_api.get("/api/v1/workflows/wf-1/company-search").respond(200, json=payload)
    result = invoke(["workflows", "run-people", "company-search", "wf-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "results" in parsed


def test_run_people_add_to_crm(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/runs/people/add-to-crm").respond(
        200,
        json={
            "added_count": 2,
            "skipped_count": 1,
            "person_ids": ["p-1", "p-2"],
        },
    )
    result = invoke(
        ["workflows", "run-people", "add-to-crm", "wf-1", "--person-ids", "wrp-1,wrp-2,wrp-3"]
    )
    assert result.exit_code == 0
    assert "Added 2 people" in result.output


def test_run_people_add_to_crm_json(invoke, mock_api):
    payload = {"added_count": 1, "skipped_count": 0, "person_ids": ["p-1"]}
    mock_api.post("/api/v1/workflows/wf-1/runs/people/add-to-crm").respond(200, json=payload)
    result = invoke(
        ["workflows", "run-people", "add-to-crm", "wf-1", "--person-ids", "wrp-1", "--json"]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["added_count"] == 1


def test_run_people_add_to_crm_with_overrides(invoke, mock_api, tmp_path):
    mock_api.post("/api/v1/workflows/wf-1/runs/people/add-to-crm").respond(
        200,
        json={
            "added_count": 1,
            "skipped_count": 0,
            "person_ids": ["p-1"],
        },
    )
    overrides_file = tmp_path / "overrides.json"
    overrides_file.write_text(
        json.dumps(
            {
                "Acme Corp": {"action": "use_existing", "company_id": "c-1"},
            }
        )
    )
    result = invoke(
        [
            "workflows",
            "run-people",
            "add-to-crm",
            "wf-1",
            "--person-ids",
            "wrp-1",
            "--overrides-file",
            str(overrides_file),
        ]
    )
    assert result.exit_code == 0
    assert "Added 1 people" in result.output


def test_run_people_crm_count(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/people/added-to-crm-count").respond(
        200, json={"count": 8}
    )
    result = invoke(["workflows", "run-people", "crm-count", "wf-1"])
    assert result.exit_code == 0
    assert "8" in result.output


def test_run_people_crm_count_json(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/people/added-to-crm-count").respond(
        200, json={"count": 8}
    )
    result = invoke(["workflows", "run-people", "crm-count", "wf-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["count"] == 8


def test_run_people_delete_with_yes(invoke, mock_api):
    mock_api.route(method="DELETE", url="/api/v1/workflows/wf-1/runs/people").respond(
        200, json={"deleted_count": 3}
    )
    result = invoke(
        ["workflows", "run-people", "delete", "wf-1", "--person-ids", "wrp-1,wrp-2,wrp-3", "--yes"]
    )
    assert result.exit_code == 0
    assert "Deleted 3" in result.output


def test_run_people_delete_aborted(invoke, mock_api):
    result = invoke(
        ["workflows", "run-people", "delete", "wf-1", "--person-ids", "wrp-1"],
        input="n\n",
    )
    assert result.exit_code == 1


def test_run_people_delete_json(invoke, mock_api):
    mock_api.route(method="DELETE", url="/api/v1/workflows/wf-1/runs/people").respond(
        200, json={"deleted_count": 1}
    )
    result = invoke(
        ["workflows", "run-people", "delete", "wf-1", "--person-ids", "wrp-1", "--yes", "--json"]
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["deleted_count"] == 1


def test_run_people_list_not_found(invoke, mock_api):
    """Workflow not found returns exit code 3."""
    mock_api.get("/api/v1/workflows/bad-wf/runs/people").respond(
        404, json={"detail": "Workflow not found"}
    )
    result = invoke(["workflows", "run-people", "list", "bad-wf"])
    assert result.exit_code == 3
    assert "404" in result.output


def test_run_people_list_not_found_json(invoke, mock_api):
    """Workflow not found with --json returns structured JSON error."""
    mock_api.get("/api/v1/workflows/bad-wf/runs/people").respond(
        404, json={"detail": "Workflow not found"}
    )
    result = invoke(["workflows", "run-people", "list", "bad-wf", "--json"])
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 404


def test_run_people_add_to_crm_error(invoke, mock_api):
    """API 422 returns exit code 2."""
    mock_api.post("/api/v1/workflows/wf-1/runs/people/add-to-crm").respond(
        422, json={"detail": "Invalid person IDs"}
    )
    result = invoke(["workflows", "run-people", "add-to-crm", "wf-1", "--person-ids", "bad"])
    assert result.exit_code == 2


def test_run_people_add_to_crm_overrides_not_found(invoke, mock_api):
    """Missing overrides file returns exit code 1."""
    result = invoke(
        [
            "workflows",
            "run-people",
            "add-to-crm",
            "wf-1",
            "--person-ids",
            "wrp-1",
            "--overrides-file",
            "/nonexistent/overrides.json",
        ]
    )
    assert result.exit_code == 1
    assert "File not found" in result.output


def test_run_people_add_to_crm_overrides_invalid_json(invoke, mock_api, tmp_path):
    """Invalid JSON in overrides file returns exit code 1."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json")
    result = invoke(
        [
            "workflows",
            "run-people",
            "add-to-crm",
            "wf-1",
            "--person-ids",
            "wrp-1",
            "--overrides-file",
            str(bad_file),
        ]
    )
    assert result.exit_code == 1
    assert "Invalid JSON" in result.output
