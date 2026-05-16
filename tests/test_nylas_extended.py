"""Tests for new nylas commands: sync-thread, download-attachment."""

import json


def test_sync_thread(invoke, mock_api):
    mock_api.post("/api/v1/nylas/sync/threads/t-1/sync").respond(200, json={"synced": 3})
    result = invoke(["nylas", "sync-thread", "t-1"])
    assert result.exit_code == 0
    assert "Synced" in result.output


def test_sync_thread_json(invoke, mock_api):
    mock_api.post("/api/v1/nylas/sync/threads/t-1/sync").respond(200, json={"synced": 3})
    result = invoke(["nylas", "sync-thread", "t-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["synced"] == 3


def test_sync_thread_404(invoke, mock_api):
    mock_api.post("/api/v1/nylas/sync/threads/bad/sync").respond(404, json={"detail": "Not found"})
    result = invoke(["nylas", "sync-thread", "bad"])
    assert result.exit_code == 3


def test_download_attachment(invoke, mock_api):
    mock_api.get("/api/v1/nylas/sync/messages/m-1/attachments/a-1/download").respond(
        200, content=b"file-content"
    )
    result = invoke(["nylas", "download-attachment", "m-1", "a-1"])
    assert result.exit_code == 0
    assert "12 bytes" in result.output


def test_download_attachment_json(invoke, mock_api):
    mock_api.get("/api/v1/nylas/sync/messages/m-1/attachments/a-1/download").respond(
        200, content=b"file-content"
    )
    result = invoke(["nylas", "download-attachment", "m-1", "a-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "downloaded"
    assert parsed["size"] == 12
