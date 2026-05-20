"""Tests for CRM companies commands."""

import json

from tests.conftest import WHOAMI_RESPONSE

SAMPLE_COMPANY = {
    "id": "c1",
    "organization_id": "org-456",
    "name": "Acme Corp",
    "industry": "SaaS",
    "lifecycle_stage": "prospect",
    "location": "San Francisco",
    "website": "https://acme.com",
    "tags": ["target"],
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
    "data_version": 1,
}


def test_companies_list(invoke, mock_api):
    mock_api.get("/api/v1/crm/companies").respond(
        200,
        json={
            "data": [SAMPLE_COMPANY],
            "total": 1,
        },
    )
    result = invoke(["crm", "companies", "list"])
    assert result.exit_code == 0
    assert "Acme Corp" in result.output


def test_companies_list_json(invoke, mock_api):
    payload = {"data": [SAMPLE_COMPANY], "total": 1}
    mock_api.get("/api/v1/crm/companies").respond(200, json=payload)
    result = invoke(["crm", "companies", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["name"] == "Acme Corp"


def test_companies_get(invoke, mock_api):
    mock_api.get("/api/v1/crm/companies/c1").respond(200, json=SAMPLE_COMPANY)
    result = invoke(["crm", "companies", "get", "c1"])
    assert result.exit_code == 0
    assert "Acme Corp" in result.output


def test_companies_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/crm/companies/bad").respond(404, json={"detail": "Not found"})
    result = invoke(["crm", "companies", "get", "bad"])
    assert result.exit_code == 3
    assert "404" in result.output


def test_companies_create(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/crm/companies").respond(201, json=SAMPLE_COMPANY)
    result = invoke(["crm", "companies", "create", "--name", "Acme Corp"])
    assert result.exit_code == 0
    assert "Created company" in result.output
    assert "Acme Corp" in result.output


def test_companies_create_with_tags(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/crm/companies").respond(201, json=SAMPLE_COMPANY)
    result = invoke(
        [
            "crm",
            "companies",
            "create",
            "--name",
            "Acme Corp",
            "--tags",
            "saas,target",
            "--industry",
            "SaaS",
        ]
    )
    assert result.exit_code == 0


def test_companies_update(invoke, mock_api):
    updated = {**SAMPLE_COMPANY, "name": "Acme Inc"}
    mock_api.patch("/api/v1/crm/companies/c1").respond(200, json=updated)
    result = invoke(["crm", "companies", "update", "c1", "--name", "Acme Inc"])
    assert result.exit_code == 0
    assert "Updated company" in result.output


def test_companies_update_no_fields(invoke, mock_api):
    result = invoke(["crm", "companies", "update", "c1"])
    assert result.exit_code == 1
    assert "No fields" in result.output


def test_companies_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/crm/companies/c1").respond(204)
    result = invoke(["crm", "companies", "delete", "c1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_companies_delete_json(invoke, mock_api):
    mock_api.delete("/api/v1/crm/companies/c1").respond(204)
    result = invoke(["crm", "companies", "delete", "c1", "--yes", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed == {"ok": True, "id": "c1", "action": "delete"}


def test_companies_delete_aborted(invoke, mock_api):
    result = invoke(["crm", "companies", "delete", "c1"], input="n\n")
    assert result.exit_code == 1


def test_companies_bulk_delete_with_yes(invoke, mock_api):
    route = mock_api.post("/api/v1/crm/companies/bulk-delete").respond(204)
    result = invoke(["crm", "companies", "bulk-delete", "--ids", "c1,c2,c3", "--yes"])
    assert result.exit_code == 0
    assert "Deleted 3 companies" in result.output
    body = json.loads(route.calls.last.request.content)
    assert body == {"ids": ["c1", "c2", "c3"]}


def test_companies_bulk_delete_json(invoke, mock_api):
    mock_api.post("/api/v1/crm/companies/bulk-delete").respond(204)
    result = invoke(["crm", "companies", "bulk-delete", "--ids", "c1,c2", "--yes", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed == {
        "ok": True,
        "ids": ["c1", "c2"],
        "count": 2,
        "action": "bulk-delete",
    }


def test_companies_bulk_delete_aborted(invoke, mock_api):
    result = invoke(["crm", "companies", "bulk-delete", "--ids", "c1,c2"], input="n\n")
    assert result.exit_code == 1


def test_companies_bulk_delete_empty_ids(invoke, mock_api):
    result = invoke(["crm", "companies", "bulk-delete", "--ids", " , ", "--yes"])
    assert result.exit_code == 1
    assert "No IDs" in result.output


def test_companies_bulk_delete_api_error(invoke, mock_api):
    mock_api.post("/api/v1/crm/companies/bulk-delete").respond(422, json={"detail": "bad"})
    result = invoke(["crm", "companies", "bulk-delete", "--ids", "c1", "--yes"])
    assert result.exit_code == 2


def test_companies_approve(invoke, mock_api):
    route = mock_api.post("/api/v1/crm/companies/approve").respond(200, json={"updated_count": 2})
    result = invoke(["crm", "companies", "approve", "--ids", "c1,c2"])
    assert result.exit_code == 0
    assert "Approved 2 companies" in result.output
    body = json.loads(route.calls.last.request.content)
    assert body == {"ids": ["c1", "c2"], "approved": True}


def test_companies_unapprove(invoke, mock_api):
    route = mock_api.post("/api/v1/crm/companies/approve").respond(200, json={"updated_count": 1})
    result = invoke(["crm", "companies", "unapprove", "--ids", "c1"])
    assert result.exit_code == 0
    assert "Unapproved 1 companies" in result.output
    body = json.loads(route.calls.last.request.content)
    assert body == {"ids": ["c1"], "approved": False}


def test_companies_approve_json(invoke, mock_api):
    mock_api.post("/api/v1/crm/companies/approve").respond(200, json={"updated_count": 2})
    result = invoke(["crm", "companies", "approve", "--ids", "c1,c2", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {"updated_count": 2}


def test_companies_approve_empty_ids(invoke, mock_api):
    result = invoke(["crm", "companies", "approve", "--ids", " "])
    assert result.exit_code == 1
    assert "No IDs" in result.output


def test_companies_list_provenance_filters(invoke, mock_api):
    route = mock_api.get("/api/v1/crm/companies").respond(
        200,
        json={"data": [], "total": 0, "limit": 100, "offset": 0, "has_more": False},
    )
    result = invoke(
        [
            "crm",
            "companies",
            "list",
            "--approved",
            "--added-by-type",
            "agent",
            "--added-by-user",
            "u1",
        ]
    )
    assert result.exit_code == 0
    url = str(route.calls.last.request.url)
    assert "approved=true" in url
    assert "added_by_type=agent" in url
    assert "added_by_user_id=u1" in url
