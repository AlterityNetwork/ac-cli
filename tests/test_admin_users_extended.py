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
