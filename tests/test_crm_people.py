"""Tests for CRM people commands."""

import json

from tests.conftest import WHOAMI_RESPONSE


SAMPLE_PERSON = {
    "id": "p1",
    "organization_id": "org-456",
    "full_name": "Jane Smith",
    "email": "jane@acme.com",
    "current_title": "CTO",
    "lifecycle_stage": "prospect",
    "is_favorite": False,
    "tags": [],
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
    "data_version": 1,
}


def test_people_list(invoke, mock_api):
    mock_api.get("/api/v1/crm/people").respond(200, json={
        "data": [SAMPLE_PERSON],
        "total": 1,
    })
    result = invoke(["crm", "people", "list"])
    assert result.exit_code == 0
    assert "Jane Smith" in result.output


def test_people_list_json(invoke, mock_api):
    payload = {"data": [SAMPLE_PERSON], "total": 1}
    mock_api.get("/api/v1/crm/people").respond(200, json=payload)
    result = invoke(["crm", "people", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["email"] == "jane@acme.com"


def test_people_list_filter_company(invoke, mock_api):
    mock_api.get("/api/v1/crm/people").respond(200, json={"data": [], "total": 0})
    result = invoke(["crm", "people", "list", "--company-id", "c1"])
    assert result.exit_code == 0


def test_people_get(invoke, mock_api):
    mock_api.get("/api/v1/crm/people/p1").respond(200, json=SAMPLE_PERSON)
    result = invoke(["crm", "people", "get", "p1"])
    assert result.exit_code == 0
    assert "Jane Smith" in result.output
    assert "CTO" in result.output


def test_people_create(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/crm/people").respond(201, json=SAMPLE_PERSON)
    result = invoke(["crm", "people", "create", "--email", "jane@acme.com", "--full-name", "Jane Smith"])
    assert result.exit_code == 0
    assert "Created person" in result.output


def test_people_update(invoke, mock_api):
    updated = {**SAMPLE_PERSON, "current_title": "CEO"}
    mock_api.patch("/api/v1/crm/people/p1").respond(200, json=updated)
    result = invoke(["crm", "people", "update", "p1", "--current-title", "CEO"])
    assert result.exit_code == 0
    assert "Updated person" in result.output


def test_people_update_no_fields(invoke, mock_api):
    result = invoke(["crm", "people", "update", "p1"])
    assert result.exit_code == 1


def test_people_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/crm/people/p1").respond(204)
    result = invoke(["crm", "people", "delete", "p1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_people_delete_json(invoke, mock_api):
    mock_api.delete("/api/v1/crm/people/p1").respond(204)
    result = invoke(["crm", "people", "delete", "p1", "--yes", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed == {"ok": True, "id": "p1", "action": "delete"}


def test_people_delete_aborted(invoke, mock_api):
    result = invoke(["crm", "people", "delete", "p1"], input="n\n")
    assert result.exit_code == 1
