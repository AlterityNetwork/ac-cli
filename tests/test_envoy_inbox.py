"""Tests for envoy inbox commands."""

import json


SAMPLE_THREAD = {
    "id": "t-1",
    "subject": "Re: Partnership",
    "status": "open",
    "sentiment": "positive",
    "assigned_to": "user-123",
    "sequence_id": "seq-1",
    "created_at": "2026-01-01T00:00:00Z",
}

SAMPLE_MESSAGE = {
    "id": "m-1",
    "thread_id": "t-1",
    "sender": "john@example.com",
    "body": "Looking forward to connecting",
    "sent_at": "2026-01-01T00:00:00Z",
}


def test_inbox_list(invoke, mock_api):
    mock_api.get("/api/v1/envoy/inbox/threads").respond(
        200, json={"data": [SAMPLE_THREAD], "total": 1, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["envoy", "inbox", "list"])
    assert result.exit_code == 0
    assert "Re: Partnership" in result.output
    assert "open" in result.output
    assert "1 total" in result.output


def test_inbox_list_json(invoke, mock_api):
    mock_api.get("/api/v1/envoy/inbox/threads").respond(
        200, json={"data": [SAMPLE_THREAD], "total": 1, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["envoy", "inbox", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["id"] == "t-1"


def test_inbox_list_with_filters(invoke, mock_api):
    mock_api.get("/api/v1/envoy/inbox/threads").respond(
        200, json={"data": [], "total": 0, "limit": 50, "offset": 0, "has_more": False}
    )
    result = invoke(["envoy", "inbox", "list", "--status", "open"])
    assert result.exit_code == 0


def test_inbox_list_with_offset(invoke, mock_api):
    route = mock_api.get("/api/v1/envoy/inbox/threads").respond(
        200, json={"data": [SAMPLE_THREAD], "total": 11, "limit": 50, "offset": 10, "has_more": False}
    )
    result = invoke(["envoy", "inbox", "list", "--offset", "10"])
    assert result.exit_code == 0
    assert "11 total" in result.output
    req = route.calls[0].request
    assert "offset=10" in str(req.url)


def test_inbox_messages(invoke, mock_api):
    mock_api.get("/api/v1/envoy/inbox/threads/t-1/messages").respond(200, json={"messages": [SAMPLE_MESSAGE]})
    result = invoke(["envoy", "inbox", "messages", "t-1"])
    assert result.exit_code == 0
    assert "john@example.com" in result.output
    assert "Looking forward" in result.output


def test_inbox_messages_json(invoke, mock_api):
    mock_api.get("/api/v1/envoy/inbox/threads/t-1/messages").respond(200, json={"messages": [SAMPLE_MESSAGE]})
    result = invoke(["envoy", "inbox", "messages", "t-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["messages"][0]["id"] == "m-1"


def test_inbox_archive(invoke, mock_api):
    mock_api.post("/api/v1/envoy/inbox/threads/t-1/archive").respond(200, json=SAMPLE_THREAD)
    result = invoke(["envoy", "inbox", "archive", "t-1"])
    assert result.exit_code == 0
    assert "Archived" in result.output


def test_inbox_unarchive(invoke, mock_api):
    mock_api.post("/api/v1/envoy/inbox/threads/t-1/unarchive").respond(200, json=SAMPLE_THREAD)
    result = invoke(["envoy", "inbox", "unarchive", "t-1"])
    assert result.exit_code == 0
    assert "Unarchived" in result.output


def test_inbox_assign(invoke, mock_api):
    mock_api.post("/api/v1/envoy/inbox/threads/t-1/assign").respond(200, json=SAMPLE_THREAD)
    result = invoke(["envoy", "inbox", "assign", "t-1", "--user-id", "user-456"])
    assert result.exit_code == 0
    assert "Assigned" in result.output


def test_inbox_snooze(invoke, mock_api):
    mock_api.post("/api/v1/envoy/inbox/threads/t-1/snooze").respond(200, json=SAMPLE_THREAD)
    result = invoke(["envoy", "inbox", "snooze", "t-1", "--until", "2026-03-15T09:00:00Z"])
    assert result.exit_code == 0
    assert "Snoozed" in result.output


def test_inbox_complete(invoke, mock_api):
    mock_api.post("/api/v1/envoy/inbox/threads/t-1/complete").respond(200, json=SAMPLE_THREAD)
    result = invoke(["envoy", "inbox", "complete", "t-1"])
    assert result.exit_code == 0
    assert "Completed" in result.output


def test_inbox_update_status(invoke, mock_api):
    mock_api.patch("/api/v1/envoy/inbox/threads/t-1/status").respond(200, json=SAMPLE_THREAD)
    result = invoke(["envoy", "inbox", "update-status", "t-1", "--status", "closed"])
    assert result.exit_code == 0
    assert "Updated" in result.output


def test_inbox_add_tags(invoke, mock_api):
    mock_api.post("/api/v1/envoy/inbox/threads/t-1/tags").respond(200, json=SAMPLE_THREAD)
    result = invoke(["envoy", "inbox", "add-tags", "t-1", "--tags", "vip,priority"])
    assert result.exit_code == 0
    assert "Added tags" in result.output


def test_inbox_remove_tags(invoke, mock_api):
    mock_api.delete("/api/v1/envoy/inbox/threads/t-1/tags").respond(200, json=SAMPLE_THREAD)
    result = invoke(["envoy", "inbox", "remove-tags", "t-1", "--tags", "vip,priority"])
    assert result.exit_code == 0
    assert "Removed tags" in result.output


def test_inbox_reply(invoke, mock_api):
    mock_api.post("/api/v1/envoy/inbox/threads/t-1/reply").respond(200, json=SAMPLE_MESSAGE)
    result = invoke(["envoy", "inbox", "reply", "t-1", "--body", "Thanks for reaching out"])
    assert result.exit_code == 0
    assert "Replied" in result.output


def test_inbox_list_not_found(invoke, mock_api):
    mock_api.get("/api/v1/envoy/inbox/threads").respond(404, json={"detail": "Not found"})
    result = invoke(["envoy", "inbox", "list"])
    assert result.exit_code == 3
