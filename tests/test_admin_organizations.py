"""Tests for admin organizations commands."""

import json


SAMPLE_ORG = {
    "id": "org-1",
    "name": "Test Corp",
    "slug": "test-corp",
    "plan": "pro",
    "created_at": "2026-01-01T00:00:00Z",
}

SAMPLE_MEMBER = {
    "user_id": "u-1",
    "email": "member@test.com",
    "role": "admin",
}


def test_orgs_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/organizations").respond(200, json={
        "data": [SAMPLE_ORG],
        "total": 1,
        "page": 1,
        "page_size": 50,
    })
    result = invoke(["admin", "orgs", "list"])
    assert result.exit_code == 0
    assert "Test Corp" in result.output


def test_orgs_list_json(invoke, mock_api):
    payload = {"data": [SAMPLE_ORG], "total": 1, "page": 1, "page_size": 50}
    mock_api.get("/api/v1/admin/organizations").respond(200, json=payload)
    result = invoke(["admin", "orgs", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["name"] == "Test Corp"


def test_orgs_get(invoke, mock_api):
    mock_api.get("/api/v1/admin/organizations/org-1").respond(200, json=SAMPLE_ORG)
    result = invoke(["admin", "orgs", "get", "org-1"])
    assert result.exit_code == 0
    assert "Test Corp" in result.output


def test_orgs_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/admin/organizations/bad").respond(404, json={"detail": "Not found"})
    result = invoke(["admin", "orgs", "get", "bad"])
    assert result.exit_code == 3
    assert "404" in result.output


def test_orgs_create(invoke, mock_api):
    mock_api.post("/api/v1/admin/organizations").respond(201, json=SAMPLE_ORG)
    result = invoke(["admin", "orgs", "create", "--name", "Test Corp"])
    assert result.exit_code == 0
    assert "Created org" in result.output
    assert "Test Corp" in result.output


def test_orgs_update(invoke, mock_api):
    updated = {**SAMPLE_ORG, "name": "Updated Corp"}
    mock_api.patch("/api/v1/admin/organizations/org-1").respond(200, json=updated)
    result = invoke(["admin", "orgs", "update", "org-1", "--name", "Updated Corp"])
    assert result.exit_code == 0
    assert "Updated org" in result.output


def test_orgs_update_no_fields(invoke, mock_api):
    result = invoke(["admin", "orgs", "update", "org-1"])
    assert result.exit_code == 1
    assert "No fields" in result.output


def test_orgs_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/admin/organizations/org-1").respond(204)
    result = invoke(["admin", "orgs", "delete", "org-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_orgs_delete_aborted(invoke, mock_api):
    result = invoke(["admin", "orgs", "delete", "org-1"], input="n\n")
    assert result.exit_code == 1


def test_orgs_members(invoke, mock_api):
    mock_api.get("/api/v1/admin/organizations/org-1/members").respond(200, json={
        "data": [SAMPLE_MEMBER],
        "total": 1,
    })
    result = invoke(["admin", "orgs", "members", "org-1"])
    assert result.exit_code == 0
    assert "member@test.com" in result.output


def test_orgs_add_member(invoke, mock_api):
    mock_api.post("/api/v1/admin/organizations/org-1/members").respond(201, json=SAMPLE_MEMBER)
    result = invoke(["admin", "orgs", "add-member", "org-1", "--user-id", "u-1"])
    assert result.exit_code == 0
    assert "Added" in result.output


def test_orgs_update_member(invoke, mock_api):
    updated_member = {**SAMPLE_MEMBER, "role": "member"}
    mock_api.patch("/api/v1/admin/organizations/org-1/members/u-1").respond(200, json=updated_member)
    result = invoke(["admin", "orgs", "update-member", "org-1", "u-1", "--role", "member"])
    assert result.exit_code == 0
    assert "Updated member" in result.output


def test_orgs_remove_member_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/admin/organizations/org-1/members/u-1").respond(204)
    result = invoke(["admin", "orgs", "remove-member", "org-1", "u-1", "--yes"])
    assert result.exit_code == 0
    assert "Removed" in result.output


def test_orgs_remove_member_aborted(invoke, mock_api):
    result = invoke(["admin", "orgs", "remove-member", "org-1", "u-1"], input="n\n")
    assert result.exit_code == 1


def test_orgs_transfer_ownership(invoke, mock_api):
    mock_api.post("/api/v1/admin/organizations/org-1/transfer-ownership").respond(
        200, json={"status": "ok"}
    )
    result = invoke(["admin", "orgs", "transfer-ownership", "org-1", "--new-owner-id", "u-2", "--yes"])
    assert result.exit_code == 0
    assert "Transferred" in result.output
