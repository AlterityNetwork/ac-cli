"""Tests for CRM people bulk commands."""

import json


def test_people_bulk_upsert(invoke, mock_api, tmp_path):
    mock_api.put("/api/v1/crm/people/bulk").respond(200, json={"count": 2})
    data_file = tmp_path / "people.json"
    data_file.write_text(json.dumps([
        {"email": "a@example.com", "full_name": "Alice"},
        {"email": "b@example.com", "full_name": "Bob"},
    ]))
    result = invoke(["crm", "people", "bulk-upsert", "--file", str(data_file)])
    assert result.exit_code == 0
    assert "Upserted 2 people" in result.output


def test_people_bulk_upsert_json(invoke, mock_api, tmp_path):
    payload = {"count": 3}
    mock_api.put("/api/v1/crm/people/bulk").respond(200, json=payload)
    data_file = tmp_path / "people.json"
    data_file.write_text(json.dumps([{"email": "a@example.com"}]))
    result = invoke(["crm", "people", "bulk-upsert", "--file", str(data_file), "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["count"] == 3


def test_people_bulk_upsert_file_not_found(invoke, mock_api):
    result = invoke(["crm", "people", "bulk-upsert", "--file", "/nonexistent/file.json"])
    assert result.exit_code == 1
    assert "File not found" in result.output


def test_people_bulk_upsert_invalid_json(invoke, mock_api, tmp_path):
    data_file = tmp_path / "bad.json"
    data_file.write_text("not json")
    result = invoke(["crm", "people", "bulk-upsert", "--file", str(data_file)])
    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


def test_people_bulk_upsert_not_array(invoke, mock_api, tmp_path):
    data_file = tmp_path / "obj.json"
    data_file.write_text(json.dumps({"email": "a@example.com"}))
    result = invoke(["crm", "people", "bulk-upsert", "--file", str(data_file)])
    assert result.exit_code == 1
    assert "JSON array" in result.output


def test_people_bulk_upsert_api_error(invoke, mock_api, tmp_path):
    """API 422 returns exit code 2."""
    mock_api.put("/api/v1/crm/people/bulk").respond(422, json={"detail": "Validation error"})
    data_file = tmp_path / "people.json"
    data_file.write_text(json.dumps([{"email": "bad"}]))
    result = invoke(["crm", "people", "bulk-upsert", "--file", str(data_file)])
    assert result.exit_code == 2
    assert "422" in result.output


def test_people_bulk_upsert_api_error_json(invoke, mock_api, tmp_path):
    """API error with --json returns structured JSON error."""
    mock_api.put("/api/v1/crm/people/bulk").respond(422, json={"detail": "Validation error"})
    data_file = tmp_path / "people.json"
    data_file.write_text(json.dumps([{"email": "bad"}]))
    result = invoke(["crm", "people", "bulk-upsert", "--file", str(data_file), "--json"])
    assert result.exit_code == 2
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 422


def test_people_bulk_delete_with_yes(invoke, mock_api):
    mock_api.post("/api/v1/crm/people/bulk-delete").respond(204)
    result = invoke(["crm", "people", "bulk-delete", "--ids", "p1,p2,p3", "--yes"])
    assert result.exit_code == 0
    assert "Deleted 3 people" in result.output


def test_people_bulk_delete_json(invoke, mock_api):
    mock_api.post("/api/v1/crm/people/bulk-delete").respond(204)
    result = invoke(["crm", "people", "bulk-delete", "--ids", "p1,p2,p3", "--yes", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed == {
        "ok": True,
        "ids": ["p1", "p2", "p3"],
        "count": 3,
        "action": "bulk-delete",
    }


def test_people_bulk_delete_aborted(invoke, mock_api):
    result = invoke(["crm", "people", "bulk-delete", "--ids", "p1,p2"], input="n\n")
    assert result.exit_code == 1


def test_people_bulk_delete_api_error(invoke, mock_api):
    """API 403 returns exit code 4."""
    mock_api.post("/api/v1/crm/people/bulk-delete").respond(403, json={"detail": "Forbidden"})
    result = invoke(["crm", "people", "bulk-delete", "--ids", "p1", "--yes"])
    assert result.exit_code == 4
