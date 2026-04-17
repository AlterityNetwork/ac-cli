"""Tests for CRM lists commands."""

import json

import httpx

from tests.conftest import API_BASE, WHOAMI_RESPONSE


SAMPLE_LIST = {
    "id": "l1",
    "organization_id": "org-456",
    "name": "Target Companies",
    "description": "Companies to reach out to",
    "type": "static",
    "member_type": "company",
    "member_count": 5,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}

SAMPLE_MEMBER = {
    "list_id": "l1",
    "company_id": "c1",
    "person_id": None,
    "added_at": "2026-01-01T00:00:00Z",
    "added_via": "manual",
    "position": 1,
}


def test_lists_list(invoke, mock_api):
    mock_api.get("/api/v1/crm/lists").respond(200, json={
        "data": [SAMPLE_LIST],
        "total": 1,
    })
    result = invoke(["crm", "lists", "list"])
    assert result.exit_code == 0
    assert "Target Companies" in result.output


def test_lists_list_json(invoke, mock_api):
    payload = {"data": [SAMPLE_LIST], "total": 1}
    mock_api.get("/api/v1/crm/lists").respond(200, json=payload)
    result = invoke(["crm", "lists", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["name"] == "Target Companies"


def test_lists_get(invoke, mock_api):
    mock_api.get("/api/v1/crm/lists/l1").respond(200, json=SAMPLE_LIST)
    result = invoke(["crm", "lists", "get", "l1"])
    assert result.exit_code == 0
    assert "Target Companies" in result.output


def test_lists_create(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/crm/lists").respond(201, json=SAMPLE_LIST)
    result = invoke(["crm", "lists", "create", "--name", "Target Companies", "--member-type", "company"])
    assert result.exit_code == 0
    assert "Created list" in result.output


def test_lists_update(invoke, mock_api):
    updated = {**SAMPLE_LIST, "name": "Updated List"}
    mock_api.patch("/api/v1/crm/lists/l1").respond(200, json=updated)
    result = invoke(["crm", "lists", "update", "l1", "--name", "Updated List"])
    assert result.exit_code == 0
    assert "Updated list" in result.output


def test_lists_update_json(invoke, mock_api):
    updated = {**SAMPLE_LIST, "name": "Updated List"}
    mock_api.patch("/api/v1/crm/lists/l1").respond(200, json=updated)
    result = invoke(["crm", "lists", "update", "l1", "--name", "Updated List", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["name"] == "Updated List"


def test_lists_update_no_fields(invoke, mock_api):
    result = invoke(["crm", "lists", "update", "l1"])
    assert result.exit_code == 1


def test_lists_members(invoke, mock_api):
    mock_api.get("/api/v1/crm/lists/l1/members").respond(200, json={
        "data": [SAMPLE_MEMBER],
        "total": 1,
    })
    result = invoke(["crm", "lists", "members", "l1"])
    assert result.exit_code == 0
    assert "c1" in result.output


def test_lists_add_member(invoke, mock_api):
    mock_api.post("/api/v1/crm/lists/l1/members").respond(201, json=SAMPLE_MEMBER)
    result = invoke(["crm", "lists", "add-member", "l1", "--company-id", "c1"])
    assert result.exit_code == 0
    assert "Added" in result.output


def test_lists_add_member_missing_id(invoke, mock_api):
    result = invoke(["crm", "lists", "add-member", "l1"])
    assert result.exit_code == 1
    assert "Must specify" in result.output


def test_lists_remove_member(invoke, mock_api):
    mock_api.delete("/api/v1/crm/lists/l1/members/company/c1").respond(204)
    result = invoke(["crm", "lists", "remove-member", "l1", "--company-id", "c1"])
    assert result.exit_code == 0
    assert "Removed" in result.output


def test_lists_remove_member_json(invoke, mock_api):
    mock_api.delete("/api/v1/crm/lists/l1/members/company/c1").respond(204)
    result = invoke(["crm", "lists", "remove-member", "l1", "--company-id", "c1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed == {
        "ok": True,
        "list_id": "l1",
        "member_type": "company",
        "member_id": "c1",
        "action": "remove-member",
    }


def test_lists_remove_member_person(invoke, mock_api):
    mock_api.delete("/api/v1/crm/lists/l1/members/person/p1").respond(204)
    result = invoke(["crm", "lists", "remove-member", "l1", "--person-id", "p1"])
    assert result.exit_code == 0


def test_lists_remove_member_missing_id(invoke, mock_api):
    result = invoke(["crm", "lists", "remove-member", "l1"])
    assert result.exit_code == 1


def test_lists_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/crm/lists/l1").respond(204)
    result = invoke(["crm", "lists", "delete", "l1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_lists_delete_json(invoke, mock_api):
    mock_api.delete("/api/v1/crm/lists/l1").respond(204)
    result = invoke(["crm", "lists", "delete", "l1", "--yes", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed == {"ok": True, "id": "l1", "action": "delete"}


def test_lists_delete_aborted(invoke, mock_api):
    result = invoke(["crm", "lists", "delete", "l1"], input="n\n")
    assert result.exit_code == 1


def test_lists_list_follows_redirect(invoke, mock_api):
    """Client should follow 307 redirects (e.g. trailing-slash normalization)."""
    payload = {"data": [SAMPLE_LIST], "total": 1}
    mock_api.get("/api/v1/crm/lists").mock(
        return_value=httpx.Response(
            307,
            headers={"Location": f"{API_BASE}/api/v1/crm/lists/"},
        )
    )
    mock_api.get("/api/v1/crm/lists/").respond(200, json=payload)
    result = invoke(["crm", "lists", "list"])
    assert result.exit_code == 0
    assert "Target Companies" in result.output
