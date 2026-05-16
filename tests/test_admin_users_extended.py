"""Tests for admin user suspension/activate commands."""

import json

SAMPLE_MSG = {"id": "msg-1", "message": "Violation of terms"}


def test_suspension_messages(invoke, mock_api):
    mock_api.get("/api/v1/admin/suspension-messages").respond(200, json=[SAMPLE_MSG])
    result = invoke(["admin", "users", "suspension-messages"])
    assert result.exit_code == 0
    assert "Violation" in result.output


def test_suspension_messages_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/suspension-messages").respond(200, json=[SAMPLE_MSG])
    result = invoke(["admin", "users", "suspension-messages", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)


def test_suspension_messages_403(invoke, mock_api):
    mock_api.get("/api/v1/admin/suspension-messages").respond(403, json={"detail": "Forbidden"})
    result = invoke(["admin", "users", "suspension-messages"])
    assert result.exit_code == 4


def test_suspend_user(invoke, mock_api):
    mock_api.post("/api/v1/admin/users/u-1/suspend").respond(
        200, json={"id": "u-1", "status": "suspended"}
    )
    result = invoke(["admin", "users", "suspend", "u-1", "--yes"])
    assert result.exit_code == 0
    assert "Suspended" in result.output


def test_suspend_user_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/users/u-1/suspend").respond(
        200, json={"id": "u-1", "status": "suspended"}
    )
    result = invoke(["admin", "users", "suspend", "u-1", "--yes", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "suspended"


def test_suspend_user_404(invoke, mock_api):
    mock_api.post("/api/v1/admin/users/bad/suspend").respond(404, json={"detail": "Not found"})
    result = invoke(["admin", "users", "suspend", "bad", "--yes"])
    assert result.exit_code == 3


def test_activate_user(invoke, mock_api):
    mock_api.post("/api/v1/admin/users/u-1/activate").respond(
        200, json={"id": "u-1", "status": "active"}
    )
    result = invoke(["admin", "users", "activate", "u-1"])
    assert result.exit_code == 0
    assert "Activated" in result.output


def test_activate_user_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/users/u-1/activate").respond(
        200, json={"id": "u-1", "status": "active"}
    )
    result = invoke(["admin", "users", "activate", "u-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "active"


def test_activate_user_404(invoke, mock_api):
    mock_api.post("/api/v1/admin/users/bad/activate").respond(404, json={"detail": "Not found"})
    result = invoke(["admin", "users", "activate", "bad"])
    assert result.exit_code == 3


def test_impersonation_status(invoke, mock_api):
    import json as _json

    payload = {
        "session_id": "sess-1",
        "target_user_id": "u-9",
        "started_at": "2026-05-10T00:00:00Z",
        "expires_at": "2026-05-10T01:00:00Z",
        "active": True,
    }
    route = mock_api.get("/api/v1/impersonation/me").respond(200, json=payload)
    result = invoke(["admin", "users", "impersonation-status", "--session-id", "sess-1", "--json"])
    assert result.exit_code == 0
    assert _json.loads(result.output) == payload
    assert route.calls.last.request.url.params["session_id"] == "sess-1"


def test_impersonation_end(invoke, mock_api):
    import json as _json

    route = mock_api.post("/api/v1/impersonation/me/end").respond(204)
    result = invoke(["admin", "users", "impersonation-end", "--session-id", "sess-1"])
    assert result.exit_code == 0
    assert "Ended impersonation session sess-1" in result.output
    body = _json.loads(route.calls.last.request.content)
    assert body == {"session_id": "sess-1"}


def test_impersonation_end_json(invoke, mock_api):
    import json as _json

    mock_api.post("/api/v1/impersonation/me/end").respond(204)
    result = invoke(["admin", "users", "impersonation-end", "--session-id", "sess-1", "--json"])
    assert result.exit_code == 0
    assert _json.loads(result.output)["session_id"] == "sess-1"


def test_impersonation_status_not_found(invoke, mock_api):
    mock_api.get("/api/v1/impersonation/me").respond(404, json={"detail": "no"})
    result = invoke(["admin", "users", "impersonation-status", "--session-id", "missing"])
    assert result.exit_code == 3
