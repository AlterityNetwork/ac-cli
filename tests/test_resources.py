"""Tests for resources commands."""

import json

SAMPLE_RESOURCES = {
    "data": [
        {"id": "res-1", "source_name": "Product Guide", "status": "completed", "created_at": "2026-03-20T10:00:00Z"},
        {"id": "res-2", "source_name": "FAQ Document", "status": "processing", "created_at": "2026-03-19T08:00:00Z"},
    ],
    "total": 2,
}

SAMPLE_UPLOAD = {
    "id": "res-3",
    "source_name": "New Resource",
}

SAMPLE_STATUS = {
    "id": "res-1",
    "status": "completed",
    "chunk_count": 42,
    "error_message": None,
}


def test_resources_list(invoke, mock_api):
    mock_api.get("/api/v1/resources").respond(200, json=SAMPLE_RESOURCES)
    result = invoke(["resources", "list"])
    assert result.exit_code == 0
    assert "Product Guide" in result.output


def test_resources_list_json(invoke, mock_api):
    mock_api.get("/api/v1/resources").respond(200, json=SAMPLE_RESOURCES)
    result = invoke(["resources", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert len(parsed["data"]) == 2


def test_resources_upload(invoke, mock_api, tmp_path):
    mock_api.post("/api/v1/resources/upload").respond(200, json=SAMPLE_UPLOAD)
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"%PDF-1.4 fake pdf content")
    result = invoke(["resources", "upload", str(test_file), "--name", "Test PDF"])
    assert result.exit_code == 0


def test_resources_upload_bad_extension(invoke, tmp_path):
    test_file = tmp_path / "malware.exe"
    test_file.write_bytes(b"bad content")
    result = invoke(["resources", "upload", str(test_file), "--name", "Bad File"])
    assert result.exit_code == 1
    assert "Unsupported" in result.output


def test_resources_delete_confirm(invoke, mock_api):
    mock_api.delete("/api/v1/resources/res-1").respond(204, content=b"")
    result = invoke(["resources", "delete", "res-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_resources_delete_abort(invoke, mock_api):
    result = invoke(["resources", "delete", "res-1"], input="n\n")
    assert result.exit_code == 1


def test_resources_status(invoke, mock_api):
    mock_api.get("/api/v1/resources/res-1/status").respond(200, json=SAMPLE_STATUS)
    result = invoke(["resources", "status", "res-1"])
    assert result.exit_code == 0
    assert "completed" in result.output
    assert "42" in result.output


def test_resources_status_json(invoke, mock_api):
    mock_api.get("/api/v1/resources/res-1/status").respond(200, json=SAMPLE_STATUS)
    result = invoke(["resources", "status", "res-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["chunk_count"] == 42
