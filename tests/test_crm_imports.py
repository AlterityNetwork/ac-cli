"""Tests for CRM import commands."""

import json


SAMPLE_PREVIEW = {
    "preview_id": "prev-123",
    "summary": {"new": 3, "updates": 1, "skipped": 0, "errors": 0},
    "records": [
        {"action": "create", "entity_type": "company", "name": "Acme Corp", "reason": None},
        {"action": "update", "entity_type": "company", "name": "Beta Inc", "reason": "name match"},
    ],
}

SAMPLE_COMMIT = {
    "created": 3,
    "updated": 1,
}


def test_import_preview(invoke, mock_api, tmp_path):
    items_file = tmp_path / "items.json"
    items_file.write_text(json.dumps([{"name": "Acme Corp"}]))
    mock_api.post("/api/v1/crm/import/preview").respond(200, json=SAMPLE_PREVIEW)
    result = invoke(["crm", "import", "preview", "--file", str(items_file)])
    assert result.exit_code == 0
    assert "prev-123" in result.output
    assert "New records: 3" in result.output


def test_import_preview_json(invoke, mock_api, tmp_path):
    items_file = tmp_path / "items.json"
    items_file.write_text(json.dumps([{"name": "Acme Corp"}]))
    mock_api.post("/api/v1/crm/import/preview").respond(200, json=SAMPLE_PREVIEW)
    result = invoke(["crm", "--json", "import", "preview", "--file", str(items_file)])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["preview_id"] == "prev-123"


def test_import_preview_file_not_found(invoke, mock_api):
    result = invoke(["crm", "import", "preview", "--file", "/nonexistent/file.json"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or result.exit_code == 1


def test_import_commit(invoke, mock_api):
    mock_api.post("/api/v1/crm/import/commit").respond(200, json=SAMPLE_COMMIT)
    result = invoke(["crm", "import", "commit", "--preview-id", "prev-123"])
    assert result.exit_code == 0
    assert "3 created" in result.output
    assert "1 updated" in result.output


def test_import_commit_json(invoke, mock_api):
    mock_api.post("/api/v1/crm/import/commit").respond(200, json=SAMPLE_COMMIT)
    result = invoke(["crm", "--json", "import", "commit", "--preview-id", "prev-123"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["created"] == 3


def test_import_commit_auto_accept(invoke, mock_api):
    mock_api.post("/api/v1/crm/import/commit").respond(200, json=SAMPLE_COMMIT)
    result = invoke(["crm", "import", "commit", "--preview-id", "prev-123", "--auto-accept"])
    assert result.exit_code == 0
    assert "committed" in result.output.lower()
