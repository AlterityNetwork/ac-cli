"""Tests for CRM import commands."""

import json

from tests.conftest import WHOAMI_RESPONSE

# Items shaped as PreviewItemRequest {app_slug, entity_type, raw_item}.
SAMPLE_ITEMS = [
    {"app_slug": "csv", "entity_type": "company", "raw_item": {"name": "Acme Corp"}},
    {"app_slug": "csv", "entity_type": "company", "raw_item": {"name": "Beta Inc"}},
]

# PreviewResponse {preview_id, items:[PreviewItemResponse]}.
SAMPLE_PREVIEW = {
    "preview_id": "prev-123",
    "items": [
        {
            "preview_item_id": "item-1",
            "app_slug": "csv",
            "entity_type": "company",
            "normalized_payload": {"name": "Acme Corp"},
            "proposed_action": "create",
            "action_reason": None,
            "match_info": {"match_status": "none", "matched_id": None},
            "fields_to_fill": [],
        },
        {
            "preview_item_id": "item-2",
            "app_slug": "csv",
            "entity_type": "company",
            "normalized_payload": {"name": "Beta Inc"},
            "proposed_action": "merge",
            "action_reason": "name match",
            "match_info": {"match_status": "exact", "matched_id": "company-99"},
            "fields_to_fill": ["website"],
        },
    ],
}

# CommitResponse {results:[CommitItemResult]}.
SAMPLE_COMMIT = {
    "results": [
        {"preview_item_id": "item-1", "status": "created", "id": "company-1"},
        {"preview_item_id": "item-2", "status": "merged", "id": "company-99"},
    ],
}


def test_import_preview(invoke, mock_api, tmp_path):
    items_file = tmp_path / "items.json"
    items_file.write_text(json.dumps(SAMPLE_ITEMS))
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/crm/import/preview").respond(200, json=SAMPLE_PREVIEW)
    result = invoke(["crm", "import", "preview", "--file", str(items_file)])
    assert result.exit_code == 0
    assert "prev-123" in result.output
    assert "Create: 1" in result.output
    assert "Merge: 1" in result.output


def test_import_preview_wraps_request(invoke, mock_api, tmp_path):
    """The bare item list is wrapped into {organization_id, flow_run_id, items}
    (previously posted a bare array → 422)."""
    items_file = tmp_path / "items.json"
    items_file.write_text(json.dumps(SAMPLE_ITEMS))
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    route = mock_api.post("/api/v1/crm/import/preview").respond(200, json=SAMPLE_PREVIEW)
    result = invoke(
        ["crm", "import", "preview", "--file", str(items_file), "--flow-run-id", "flow-7"]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["organization_id"] == WHOAMI_RESPONSE["organization_id"]
    assert body["flow_run_id"] == "flow-7"
    assert body["items"] == SAMPLE_ITEMS


def test_import_preview_generates_flow_run_id(invoke, mock_api, tmp_path):
    """When --flow-run-id is omitted a UUID is generated so the request validates."""
    items_file = tmp_path / "items.json"
    items_file.write_text(json.dumps(SAMPLE_ITEMS))
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    route = mock_api.post("/api/v1/crm/import/preview").respond(200, json=SAMPLE_PREVIEW)
    result = invoke(["crm", "import", "preview", "--file", str(items_file)])
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["flow_run_id"]  # non-empty generated UUID


def test_import_preview_json(invoke, mock_api, tmp_path):
    items_file = tmp_path / "items.json"
    items_file.write_text(json.dumps(SAMPLE_ITEMS))
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/crm/import/preview").respond(200, json=SAMPLE_PREVIEW)
    result = invoke(["crm", "import", "preview", "--file", str(items_file), "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["preview_id"] == "prev-123"


def test_import_preview_file_not_found(invoke, mock_api):
    result = invoke(["crm", "import", "preview", "--file", "/nonexistent/file.json"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_import_commit(invoke, mock_api, tmp_path):
    preview_file = tmp_path / "preview.json"
    preview_file.write_text(json.dumps(SAMPLE_PREVIEW))
    mock_api.post("/api/v1/crm/import/commit").respond(200, json=SAMPLE_COMMIT)
    result = invoke(["crm", "import", "commit", "--preview-file", str(preview_file)])
    assert result.exit_code == 0
    assert "1 created" in result.output
    assert "1 merged" in result.output


def test_import_commit_builds_decisions(invoke, mock_api, tmp_path):
    """Commit builds a decisions list from the preview items (previously sent a
    dead {preview_id, auto_accept} body → 422)."""
    preview_file = tmp_path / "preview.json"
    preview_file.write_text(json.dumps(SAMPLE_PREVIEW))
    route = mock_api.post("/api/v1/crm/import/commit").respond(200, json=SAMPLE_COMMIT)
    result = invoke(["crm", "import", "commit", "--preview-file", str(preview_file)])
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["preview_id"] == "prev-123"
    assert body["decisions"] == [
        {"preview_item_id": "item-1", "final_action": "create"},
        {"preview_item_id": "item-2", "final_action": "merge", "target_id": "company-99"},
    ]


def test_import_commit_json(invoke, mock_api, tmp_path):
    preview_file = tmp_path / "preview.json"
    preview_file.write_text(json.dumps(SAMPLE_PREVIEW))
    mock_api.post("/api/v1/crm/import/commit").respond(200, json=SAMPLE_COMMIT)
    result = invoke(["crm", "import", "commit", "--preview-file", str(preview_file), "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["results"][0]["status"] == "created"


def test_import_commit_file_not_found(invoke, mock_api):
    result = invoke(["crm", "import", "commit", "--preview-file", "/nonexistent/preview.json"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()
