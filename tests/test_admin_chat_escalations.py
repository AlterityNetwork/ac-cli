"""Tests for admin chat-escalations commands."""

import json


SAMPLE_ESCALATION = {
    "id": "esc-1",
    "organization_id": "org-1",
    "thread_id": "thread-1",
    "status": "open",
    "note": None,
    "created_at": "2026-04-15T00:00:00Z",
}


def test_chat_escalations_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/chat-escalations").respond(
        200, json={"data": [SAMPLE_ESCALATION], "total": 1}
    )
    result = invoke(["admin", "chat-escalations", "list"])
    assert result.exit_code == 0
    assert "Chat Escalations" in result.output


def test_chat_escalations_list_status_filter(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/chat-escalations").respond(
        200, json={"data": [], "total": 0}
    )
    result = invoke(
        ["admin", "chat-escalations", "list", "--status", "triaged", "--json"]
    )
    assert result.exit_code == 0
    assert "status=triaged" in str(route.calls.last.request.url)


def test_chat_escalations_update(invoke, mock_api):
    mock_api.patch("/api/v1/admin/chat-escalations/esc-1").respond(
        200, json={**SAMPLE_ESCALATION, "status": "resolved"}
    )
    result = invoke(
        ["admin", "chat-escalations", "update", "esc-1", "--status", "resolved"]
    )
    assert result.exit_code == 0
    assert "resolved" in result.output


def test_chat_escalations_update_with_note(invoke, mock_api):
    route = mock_api.patch("/api/v1/admin/chat-escalations/esc-1").respond(
        200, json={**SAMPLE_ESCALATION, "status": "triaged", "note": "looking"}
    )
    result = invoke(
        [
            "admin", "chat-escalations", "update", "esc-1",
            "--status", "triaged", "--note", "looking", "--json",
        ]
    )
    assert result.exit_code == 0
    sent = json.loads(route.calls.last.request.content)
    assert sent == {"status": "triaged", "note": "looking"}


def test_chat_escalations_update_not_found(invoke, mock_api):
    mock_api.patch("/api/v1/admin/chat-escalations/bogus").respond(
        404, json={"detail": "Not found"}
    )
    result = invoke(
        ["admin", "chat-escalations", "update", "bogus", "--status", "open"]
    )
    assert result.exit_code == 3
