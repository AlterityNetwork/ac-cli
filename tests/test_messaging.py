"""Tests for messaging commands."""

import json

SAMPLE_SESSIONS = [
    {
        "id": "sess-1",
        "platform": "whatsapp",
        "sender_id": "+15551234567",
        "display_name": "Jane Doe",
        "user_id": "user-123",
        "organization_id": "org-456",
        "chat_thread_id": "thread-1",
        "last_activity_at": "2026-03-30T12:00:00Z",
        "created_at": "2026-03-28T10:00:00Z",
    },
    {
        "id": "sess-2",
        "platform": "slack",
        "sender_id": "U12345",
        "display_name": "Bob Smith",
        "user_id": "user-789",
        "organization_id": "org-456",
        "chat_thread_id": "thread-2",
        "last_activity_at": "2026-03-29T08:00:00Z",
        "created_at": "2026-03-27T09:00:00Z",
    },
]

SAMPLE_LINK_RESPONSE = {
    "platform": "whatsapp",
    "sender_id": "+15551234567",
    "organization_id": "org-456",
    "linked": True,
}


def test_messaging_sessions(invoke, mock_api):
    mock_api.get("/api/v1/messaging/sessions").respond(200, json=SAMPLE_SESSIONS)
    result = invoke(["messaging", "sessions"])
    assert result.exit_code == 0
    assert "whatsapp" in result.output
    assert "Jane Doe" in result.output


def test_messaging_sessions_json(invoke, mock_api):
    mock_api.get("/api/v1/messaging/sessions").respond(200, json=SAMPLE_SESSIONS)
    result = invoke(["messaging", "sessions", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert len(parsed) == 2
    assert parsed[0]["platform"] == "whatsapp"


def test_messaging_sessions_empty(invoke, mock_api):
    mock_api.get("/api/v1/messaging/sessions").respond(200, json=[])
    result = invoke(["messaging", "sessions"])
    assert result.exit_code == 0


def test_messaging_sessions_error(invoke, mock_api):
    mock_api.get("/api/v1/messaging/sessions").respond(403, json={"detail": "Forbidden"})
    result = invoke(["messaging", "sessions"])
    assert result.exit_code == 4


def test_messaging_link(invoke, mock_api):
    mock_api.post("/api/v1/messaging/link").respond(200, json=SAMPLE_LINK_RESPONSE)
    result = invoke(["messaging", "link", "--token", "valid-jwt-token"])
    assert result.exit_code == 0
    assert "Linked" in result.output
    assert "whatsapp" in result.output


def test_messaging_link_json(invoke, mock_api):
    mock_api.post("/api/v1/messaging/link").respond(200, json=SAMPLE_LINK_RESPONSE)
    result = invoke(["messaging", "link", "--token", "valid-jwt-token", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["linked"] is True
    assert parsed["platform"] == "whatsapp"


def test_messaging_link_expired_token(invoke, mock_api):
    mock_api.post("/api/v1/messaging/link").respond(
        400, json={"detail": "Link token has expired"}
    )
    result = invoke(["messaging", "link", "--token", "expired-jwt"])
    assert result.exit_code == 1


def test_messaging_link_invalid_token(invoke, mock_api):
    mock_api.post("/api/v1/messaging/link").respond(
        400, json={"detail": "Invalid link token"}
    )
    result = invoke(["messaging", "link", "--token", "garbage"])
    assert result.exit_code == 1
