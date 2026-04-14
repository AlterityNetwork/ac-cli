"""Tests for admin resource management commands."""

import json


SAMPLE_RESOURCE = {"id": "r-1", "name": "Guide.pdf", "status": "processed", "type": "pdf"}
SAMPLE_CHUNK = {"id": "ch-1", "index": 0, "token_count": 128}


def test_resources_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/resources").respond(200, json={"data": [SAMPLE_RESOURCE]})
    result = invoke(["admin", "resources", "list"])
    assert result.exit_code == 0
    assert "Guide.pdf" in result.output


def test_resources_list_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/resources").respond(200, json={"data": [SAMPLE_RESOURCE]})
    result = invoke(["admin", "resources", "list", "--json"])
    assert result.exit_code == 0
    json.loads(result.output)


def test_resources_get(invoke, mock_api):
    mock_api.get("/api/v1/admin/resources/r-1").respond(200, json=SAMPLE_RESOURCE)
    result = invoke(["admin", "resources", "get", "r-1"])
    assert result.exit_code == 0
    assert "Guide.pdf" in result.output


def test_resources_get_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/resources/r-1").respond(200, json=SAMPLE_RESOURCE)
    result = invoke(["admin", "resources", "get", "r-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "r-1"


def test_resources_chunks(invoke, mock_api):
    mock_api.get("/api/v1/admin/resources/r-1/chunks").respond(200, json={"chunks": [SAMPLE_CHUNK]})
    result = invoke(["admin", "resources", "chunks", "r-1"])
    assert result.exit_code == 0


def test_resources_chunks_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/resources/r-1/chunks").respond(200, json={"chunks": [SAMPLE_CHUNK]})
    result = invoke(["admin", "resources", "chunks", "r-1", "--json"])
    assert result.exit_code == 0
    json.loads(result.output)


def test_resources_preview_url(invoke, mock_api):
    mock_api.get("/api/v1/admin/resources/r-1/preview-url").respond(200, json={"url": "https://example.com/preview"})
    result = invoke(["admin", "resources", "preview-url", "r-1"])
    assert result.exit_code == 0
    assert "preview" in result.output.lower()


def test_resources_preview_url_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/resources/r-1/preview-url").respond(200, json={"url": "https://example.com/preview"})
    result = invoke(["admin", "resources", "preview-url", "r-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "url" in parsed


def test_resources_update(invoke, mock_api):
    mock_api.patch("/api/v1/admin/resources/r-1").respond(200, json={**SAMPLE_RESOURCE, "name": "Updated.pdf"})
    result = invoke(["admin", "resources", "update", "r-1", "--name", "Updated.pdf"])
    assert result.exit_code == 0
    assert "Updated" in result.output


def test_resources_update_no_fields(invoke, mock_api):
    result = invoke(["admin", "resources", "update", "r-1"])
    assert result.exit_code == 1


def test_resources_delete(invoke, mock_api):
    mock_api.delete("/api/v1/admin/resources/r-1").respond(204)
    result = invoke(["admin", "resources", "delete", "r-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_resources_delete_abort(invoke, mock_api):
    result = invoke(["admin", "resources", "delete", "r-1"], input="n\n")
    assert result.exit_code != 0


def test_resources_reprocess(invoke, mock_api):
    mock_api.post("/api/v1/admin/resources/r-1/reprocess").respond(200, json={"status": "processing"})
    result = invoke(["admin", "resources", "reprocess", "r-1"])
    assert result.exit_code == 0
    assert "Reprocessing" in result.output


def test_resources_reprocess_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/resources/r-1/reprocess").respond(200, json={"status": "processing"})
    result = invoke(["admin", "resources", "reprocess", "r-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "processing"


def test_resources_get_404(invoke, mock_api):
    mock_api.get("/api/v1/admin/resources/bad").respond(404, json={"detail": "Not found"})
    result = invoke(["admin", "resources", "get", "bad"])
    assert result.exit_code == 3
