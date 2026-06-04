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

SAMPLE_AUTH_USER = {
    "id": "u-1",
    "email": "admin@test.com",
    "created_at": "2026-01-01T00:00:00Z",
    "email_confirmed_at": "2026-01-01T00:01:00Z",
    "last_sign_in_at": "2026-03-20T12:00:00Z",
}


def test_users_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/users").respond(
        200,
        json={
            "items": [SAMPLE_USER],
            "total": 1,
            "page": 1,
            "page_size": 50,
        },
    )
    result = invoke(["admin", "users", "list"])
    assert result.exit_code == 0
    assert "admin@test.com" in result.output


def test_users_list_json(invoke, mock_api):
    payload = {"items": [SAMPLE_USER], "total": 1, "page": 1, "page_size": 50}
    mock_api.get("/api/v1/admin/users").respond(200, json=payload)
    result = invoke(["admin", "users", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["items"][0]["email"] == "admin@test.com"


def test_users_get(invoke, mock_api):
    mock_api.get("/api/v1/admin/users/u-1").respond(200, json=SAMPLE_USER)
    result = invoke(["admin", "users", "get", "u-1"])
    assert result.exit_code == 0
    assert "admin@test.com" in result.output


def test_users_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/admin/users/bad").respond(404, json={"detail": "Not found"})
    result = invoke(["admin", "users", "get", "bad"])
    assert result.exit_code == 3
    assert "404" in result.output


def test_users_create(invoke, mock_api):
    mock_api.post("/api/v1/admin/users").respond(201, json={"id": "u-1"})
    result = invoke(
        ["admin", "users", "create", "--email", "admin@test.com", "--password", "secret123"]
    )
    assert result.exit_code == 0
    assert "Created user" in result.output
    assert "u-1" in result.output


def test_users_create_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/users").respond(201, json={"id": "u-1"})
    result = invoke(
        [
            "admin",
            "users",
            "create",
            "--email",
            "admin@test.com",
            "--password",
            "secret123",
            "--json",
        ]
    )
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


def test_users_require_tos_resign_with_yes(invoke, mock_api):
    mock_api.post("/api/v1/admin/users/u-1/require-tos-resign").respond(200, json={"id": "u-1"})
    result = invoke(["admin", "users", "require-tos-resign", "u-1", "--yes"])
    assert result.exit_code == 0
    assert "ToS re-sign required" in result.output


def test_users_require_tos_resign_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/users/u-1/require-tos-resign").respond(200, json={"id": "u-1"})
    result = invoke(["admin", "users", "require-tos-resign", "u-1", "--yes", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "u-1"


def test_users_require_tos_resign_aborted(invoke, mock_api):
    result = invoke(["admin", "users", "require-tos-resign", "u-1"], input="n\n")
    assert result.exit_code == 1


def test_users_require_tos_resign_empty_body(invoke, mock_api):
    # API may return an empty body (e.g. 204); the command falls back to the
    # supplied user_id instead of trying to parse no content.
    mock_api.post("/api/v1/admin/users/u-1/require-tos-resign").respond(204)
    result = invoke(["admin", "users", "require-tos-resign", "u-1", "--yes"])
    assert result.exit_code == 0
    assert "ToS re-sign required for user u-1" in result.output


def test_users_require_tos_resign_empty_body_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/users/u-1/require-tos-resign").respond(204)
    result = invoke(["admin", "users", "require-tos-resign", "u-1", "--yes", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["id"] == "u-1"


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


# -- auth-search tests --------------------------------------------------------


def test_users_auth_search(invoke, mock_api):
    mock_api.get("/api/v1/admin/users/auth-search").respond(200, json=SAMPLE_AUTH_USER)
    result = invoke(["admin", "users", "auth-search", "--email", "admin@test.com"])
    assert result.exit_code == 0
    assert "admin@test.com" in result.output


def test_users_auth_search_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/users/auth-search").respond(200, json=SAMPLE_AUTH_USER)
    result = invoke(["admin", "users", "auth-search", "--email", "admin@test.com", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["email"] == "admin@test.com"
    assert parsed["last_sign_in_at"] == "2026-03-20T12:00:00Z"


def test_users_auth_search_not_found(invoke, mock_api):
    mock_api.get("/api/v1/admin/users/auth-search").respond(
        404, json={"detail": "Auth user not found"}
    )
    result = invoke(["admin", "users", "auth-search", "--email", "nobody@test.com"])
    assert result.exit_code == 3
    assert "404" in result.output


# -- create/update field name tests -------------------------------------------


def test_users_create_with_full_name(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/users").respond(201, json={"id": "u-2"})
    result = invoke(
        [
            "admin",
            "users",
            "create",
            "--email",
            "new@test.com",
            "--password",
            "secret123",
            "--full-name",
            "Jane Doe",
        ]
    )
    assert result.exit_code == 0
    assert "u-2" in result.output
    body = json.loads(route.calls[0].request.content)
    assert body["first_name"] == "Jane"
    assert body["last_name"] == "Doe"
    assert "full_name" not in body


def test_users_create_single_name(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/users").respond(201, json={"id": "u-3"})
    result = invoke(
        [
            "admin",
            "users",
            "create",
            "--email",
            "mono@test.com",
            "--password",
            "secret123",
            "--full-name",
            "Cher",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert body["first_name"] == "Cher"
    assert "last_name" not in body


def test_users_update_with_full_name(invoke, mock_api):
    route = mock_api.patch("/api/v1/admin/users/u-1").respond(200, json={"id": "u-1"})
    result = invoke(["admin", "users", "update", "u-1", "--full-name", "John Smith"])
    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert body["first_name"] == "John"
    assert body["last_name"] == "Smith"
    assert "full_name" not in body


# -- list query param test ----------------------------------------------------


def test_users_list_query_param(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/users").respond(
        200,
        json={
            "items": [SAMPLE_USER],
            "total": 1,
            "page": 1,
            "page_size": 50,
        },
    )
    result = invoke(["admin", "users", "list", "--query", "admin"])
    assert result.exit_code == 0
    request_url = str(route.calls[0].request.url)
    assert "q=admin" in request_url
    assert "query=admin" not in request_url
