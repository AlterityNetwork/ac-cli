"""Tests for admin users commands."""

import json


SAMPLE_USER = {
    "id": "u-1",
    "email": "admin@test.com",
    "full_name": "Admin User",
    "organization_id": "org-456",
    "is_superadmin": True,
    "created_at": "2026-01-01T00:00:00Z",
}


def test_users_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/users").respond(200, json={
        "data": [SAMPLE_USER],
        "total": 1,
        "page": 1,
        "page_size": 50,
    })
    result = invoke(["admin", "users", "list"])
    assert result.exit_code == 0
    assert "admin@test.com" in result.output


def test_users_list_json(invoke, mock_api):
    payload = {"data": [SAMPLE_USER], "total": 1, "page": 1, "page_size": 50}
    mock_api.get("/api/v1/admin/users").respond(200, json=payload)
    result = invoke(["admin", "--json", "users", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["email"] == "admin@test.com"


def test_users_get(invoke, mock_api):
    mock_api.get("/api/v1/admin/users/u-1").respond(200, json=SAMPLE_USER)
    result = invoke(["admin", "users", "get", "u-1"])
    assert result.exit_code == 0
    assert "admin@test.com" in result.output


def test_users_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/admin/users/bad").respond(404, json={"detail": "Not found"})
    result = invoke(["admin", "users", "get", "bad"])
    assert result.exit_code == 1
    assert "404" in result.output


def test_users_create(invoke, mock_api):
    mock_api.post("/api/v1/admin/users").respond(201, json={"id": "u-1"})
    result = invoke(["admin", "users", "create", "--email", "admin@test.com", "--password", "secret123"])
    assert result.exit_code == 0
    assert "Created user" in result.output
    assert "u-1" in result.output


def test_users_create_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/users").respond(201, json={"id": "u-1"})
    result = invoke(["admin", "--json", "users", "create", "--email", "admin@test.com", "--password", "secret123"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "u-1"


def test_users_update(invoke, mock_api):
    updated = {**SAMPLE_USER, "full_name": "Updated Name"}
    mock_api.patch("/api/v1/admin/users/u-1").respond(200, json=updated)
    result = invoke(["admin", "users", "update", "u-1", "--full-name", "Updated Name"])
    assert result.exit_code == 0
    assert "Updated user" in result.output


def test_users_update_no_fields(invoke, mock_api):
    result = invoke(["admin", "users", "update", "u-1"])
    assert result.exit_code == 1
    assert "No fields" in result.output


def test_users_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/admin/users/u-1").respond(204)
    result = invoke(["admin", "users", "delete", "u-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_users_delete_aborted(invoke, mock_api):
    result = invoke(["admin", "users", "delete", "u-1"], input="n\n")
    assert result.exit_code == 1


def test_users_search(invoke, mock_api):
    mock_api.get("/api/v1/admin/users/search").respond(200, json=SAMPLE_USER)
    result = invoke(["admin", "users", "search", "--email", "admin@test.com"])
    assert result.exit_code == 0


def test_users_reset_password(invoke, mock_api):
    mock_api.post("/api/v1/admin/users/u-1/reset-password").respond(200, json={"status": "ok"})
    result = invoke(["admin", "users", "reset-password", "u-1", "--yes"])
    assert result.exit_code == 0
    assert "Password reset" in result.output


def test_users_impersonate(invoke, mock_api):
    mock_api.post("/api/v1/admin/users/u-1/impersonate").respond(200, json={"status": "ok"})
    result = invoke(["admin", "users", "impersonate", "u-1"])
    assert result.exit_code == 0
    assert "Impersonating user" in result.output


def test_users_exit_impersonation(invoke, mock_api):
    mock_api.post("/api/v1/admin/users/impersonate/exit").respond(200, json={"status": "ok"})
    result = invoke(["admin", "users", "exit-impersonation"])
    assert result.exit_code == 0
    assert "Exited impersonation" in result.output


def test_users_generate_link(invoke, mock_api):
    mock_api.post("/api/v1/admin/users/u-1/generate-impersonation-link").respond(
        200, json={"link": "https://app.example.com/impersonate?token=abc123"}
    )
    result = invoke(["admin", "users", "generate-link", "u-1"])
    assert result.exit_code == 0
    assert "Impersonation link" in result.output
    assert "abc123" in result.output
