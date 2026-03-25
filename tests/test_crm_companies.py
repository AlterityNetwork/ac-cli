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
    mock_api.get("/api/v1/crm/companies").respond(200, json={
        "data": [SAMPLE_COMPANY],
        "total": 1,
    })
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
    result = invoke([
        "crm", "companies", "create",
        "--name", "Acme Corp",
        "--tags", "saas,target",
        "--industry", "SaaS",
    ])
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


def test_companies_delete_aborted(invoke, mock_api):
    result = invoke(["crm", "companies", "delete", "c1"], input="n\n")
    assert result.exit_code == 1
