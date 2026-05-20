"""Tests for `ac crm digests` commands."""

import json

PREVIEW_PAYLOAD = {
    "payload": {
        "owner_user_id": "11111111-1111-1111-1111-111111111111",
        "organization_id": "22222222-2222-2222-2222-222222222222",
        "digest_date": "2026-05-19",
        "pipeline": {
            "won_count": 1,
            "lost_count": 0,
            "staged_count": 1,
            "won_value": "10000",
            "lost_value": "0",
            "sample_won": [],
            "sample_lost": [],
            "sample_staged": [],
        },
        "overdue_activities": [],
        "next_best_actions": [],
        "suggested_followups": [],
        "engagement": {
            "emails_sent": 0,
            "opens": 0,
            "clicks": 0,
            "replies": 0,
            "bounces": 0,
            "open_rate": 0.0,
            "click_rate": 0.0,
        },
        "markdown": "# Good morning, Xiao\n\nHere's what moved in the last 24h.",
        "is_empty": False,
    }
}


def test_preview_renders_markdown(invoke, mock_api):
    mock_api.get("/api/v1/crm/digests/preview").respond(200, json=PREVIEW_PAYLOAD)
    result = invoke(["crm", "digests", "preview"])
    assert result.exit_code == 0
    assert "CRM digest preview" in result.output
    assert "Good morning, Xiao" in result.output


def test_preview_json(invoke, mock_api):
    mock_api.get("/api/v1/crm/digests/preview").respond(200, json=PREVIEW_PAYLOAD)
    result = invoke(["crm", "digests", "preview", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["payload"]["digest_date"] == "2026-05-19"


def test_preview_forbidden(invoke, mock_api):
    mock_api.get("/api/v1/crm/digests/preview").respond(403, json={"detail": "no"})
    result = invoke(["crm", "digests", "preview"])
    assert result.exit_code == 4


def test_test_send_dispatch(invoke, mock_api):
    mock_api.post("/api/v1/crm/digests/test-send").respond(
        200,
        json={
            "notification_id": "33333333-3333-3333-3333-333333333333",
            "email_sent": True,
            "is_empty": False,
        },
    )
    result = invoke(["crm", "digests", "test-send"])
    assert result.exit_code == 0
    assert "In-app notification sent" in result.output
    assert "Email dispatched" in result.output


def test_test_send_empty(invoke, mock_api):
    mock_api.post("/api/v1/crm/digests/test-send").respond(
        200, json={"notification_id": None, "email_sent": False, "is_empty": True}
    )
    result = invoke(["crm", "digests", "test-send"])
    assert result.exit_code == 0
    assert "No signals" in result.output


def test_test_send_json(invoke, mock_api):
    mock_api.post("/api/v1/crm/digests/test-send").respond(
        200,
        json={
            "notification_id": "33333333-3333-3333-3333-333333333333",
            "email_sent": False,
            "is_empty": False,
        },
    )
    result = invoke(["crm", "digests", "test-send", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["email_sent"] is False


def test_test_send_with_to_override(invoke, mock_api):
    route = mock_api.post("/api/v1/crm/digests/test-send").respond(
        200,
        json={
            "notification_id": None,
            "email_sent": True,
            "is_empty": False,
            "recipient_email": "qa@example.com",
        },
    )
    result = invoke(["crm", "digests", "test-send", "--to", "qa@example.com"])
    assert result.exit_code == 0
    assert route.called
    sent_body = json.loads(route.calls.last.request.content)
    assert sent_body == {"recipient_email": "qa@example.com"}
    assert "Email dispatched to qa@example.com" in result.output
    assert "In-app dispatch skipped" in result.output


def test_test_send_server_error(invoke, mock_api):
    mock_api.post("/api/v1/crm/digests/test-send").respond(500, json={"detail": "boom"})
    result = invoke(["crm", "digests", "test-send", "--json"])
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert parsed["error"] is True


def test_test_send_validation_error_exit_2(invoke, mock_api):
    """422 → exit code 2 with structured JSON error."""
    mock_api.post("/api/v1/crm/digests/test-send").respond(422, json={"detail": "invalid payload"})
    result = invoke(["crm", "digests", "test-send", "--json"])
    assert result.exit_code == 2
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 422


def test_test_send_not_found_exit_3(invoke, mock_api):
    """404 → exit code 3."""
    mock_api.post("/api/v1/crm/digests/test-send").respond(404, json={"detail": "owner missing"})
    result = invoke(["crm", "digests", "test-send", "--json"])
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert parsed["status_code"] == 404


def test_test_send_forbidden_exit_4(invoke, mock_api):
    """403 → exit code 4 (auth/permission)."""
    mock_api.post("/api/v1/crm/digests/test-send").respond(403, json={"detail": "not allowed"})
    result = invoke(["crm", "digests", "test-send", "--json"])
    assert result.exit_code == 4
    parsed = json.loads(result.output)
    assert parsed["status_code"] == 403


def test_test_send_conflict_exit_5(invoke, mock_api):
    """409 → exit code 5 (idempotency conflict)."""
    mock_api.post("/api/v1/crm/digests/test-send").respond(
        409, json={"detail": "duplicate dispatch"}
    )
    result = invoke(["crm", "digests", "test-send", "--json"])
    assert result.exit_code == 5
    parsed = json.loads(result.output)
    assert parsed["status_code"] == 409


def test_test_send_email_muted_hint(invoke, mock_api):
    """When opted-out (email_sent=false but in-app fires), CLI prints the
    opt-in hint pointing users to settings."""
    mock_api.post("/api/v1/crm/digests/test-send").respond(
        200,
        json={
            "notification_id": "33333333-3333-3333-3333-333333333333",
            "email_sent": False,
            "is_empty": False,
        },
    )
    result = invoke(["crm", "digests", "test-send"])
    assert result.exit_code == 0
    assert "In-app notification sent" in result.output
    assert "Email not sent" in result.output
    assert "/settings/notifications" in result.output


def test_preview_empty_markdown_renders_placeholder(invoke, mock_api):
    """When the digest payload has no markdown, preview falls back to a
    visible empty marker instead of printing nothing."""
    empty = {
        "payload": {
            **PREVIEW_PAYLOAD["payload"],
            "markdown": "",
            "is_empty": True,
        }
    }
    mock_api.get("/api/v1/crm/digests/preview").respond(200, json=empty)
    result = invoke(["crm", "digests", "preview"])
    assert result.exit_code == 0
    assert "(empty digest)" in result.output


def test_preview_validation_error_json_exit_2(invoke, mock_api):
    """422 on preview with --json → exit 2 + structured error."""
    mock_api.get("/api/v1/crm/digests/preview").respond(422, json={"detail": "bad query"})
    result = invoke(["crm", "digests", "preview", "--json"])
    assert result.exit_code == 2
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 422
