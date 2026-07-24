"""Tests for admin intelligence viewer commands."""

import json

SAMPLE_COMPANY = {
    "id": "co-1",
    "name": "Acme",
    "domain": "acme.test",
    "industry": "Software",
    "country": "US",
    "last_enriched_at": "2026-07-01T00:00:00Z",
}

SAMPLE_PERSON = {
    "id": "pe-1",
    "full_name": "Jane Doe",
    "linkedin_url": "https://linkedin.com/in/jane",
    "current_title": "CTO",
    "current_company_text": "Acme",
    "country": "US",
}

SAMPLE_SOURCE = {
    "id": "src-1",
    "provider": "explorium",
    "kind": "company",
    "cost_usd": 0.02,
    "fetched_at": "2026-07-01T00:00:00Z",
}

_LIST = {"total": 1, "limit": 50, "offset": 0, "has_more": False}


def test_companies_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/intelligence/companies").respond(
        200, json={"data": [SAMPLE_COMPANY], **_LIST}
    )
    result = invoke(["admin", "intelligence", "companies", "list"])
    assert result.exit_code == 0
    assert "Acme" in result.output


def test_companies_list_search_param(invoke, mock_api):
    route = mock_api.get("/api/v1/admin/intelligence/companies").respond(
        200, json={"data": [], **_LIST, "total": 0}
    )
    result = invoke(["admin", "intelligence", "companies", "list", "--query", "acme", "--json"])
    assert result.exit_code == 0
    assert "q=acme" in str(route.calls.last.request.url)


def test_companies_list_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/intelligence/companies").respond(
        200, json={"data": [SAMPLE_COMPANY], **_LIST}
    )
    result = invoke(["admin", "intelligence", "companies", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["data"][0]["name"] == "Acme"


def test_companies_get(invoke, mock_api):
    mock_api.get("/api/v1/admin/intelligence/companies/co-1").respond(
        200, json={"company": SAMPLE_COMPANY, "sources": [SAMPLE_SOURCE]}
    )
    result = invoke(["admin", "intelligence", "companies", "get", "co-1"])
    assert result.exit_code == 0
    assert "Acme" in result.output
    assert "explorium" in result.output


def test_companies_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/admin/intelligence/companies/bad").respond(
        404, json={"detail": "Intel company not found"}
    )
    result = invoke(["admin", "intelligence", "companies", "get", "bad"])
    assert result.exit_code == 3
    assert "404" in result.output


def test_companies_get_forbidden(invoke, mock_api):
    mock_api.get("/api/v1/admin/intelligence/companies/co-1").respond(
        403, json={"detail": "Superadmin access required"}
    )
    result = invoke(["admin", "intelligence", "companies", "get", "co-1"])
    assert result.exit_code == 4


def test_people_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/intelligence/people").respond(
        200, json={"data": [SAMPLE_PERSON], **_LIST}
    )
    result = invoke(["admin", "intelligence", "people", "list"])
    assert result.exit_code == 0
    assert "Jane Doe" in result.output


def test_people_list_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/intelligence/people").respond(
        200, json={"data": [SAMPLE_PERSON], **_LIST}
    )
    result = invoke(["admin", "intelligence", "people", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["data"][0]["full_name"] == "Jane Doe"


def test_people_get(invoke, mock_api):
    mock_api.get("/api/v1/admin/intelligence/people/pe-1").respond(
        200, json={"person": SAMPLE_PERSON, "sources": []}
    )
    result = invoke(["admin", "intelligence", "people", "get", "pe-1"])
    assert result.exit_code == 0
    assert "Jane Doe" in result.output


# -- CRUD ---------------------------------------------------------------------


def test_companies_create(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/intelligence/companies").respond(201, json=SAMPLE_COMPANY)
    result = invoke(
        ["admin", "intelligence", "companies", "create", "--name", "Acme", "--domain", "acme.test"]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body == {"name": "Acme", "domain": "acme.test"}


def test_companies_create_conflict(invoke, mock_api):
    mock_api.post("/api/v1/admin/intelligence/companies").respond(
        409, json={"detail": "already exists"}
    )
    result = invoke(["admin", "intelligence", "companies", "create", "--domain", "acme.test"])
    assert result.exit_code == 5


def test_companies_create_no_fields(invoke, mock_api):
    # A create with no identity fields is rejected client-side before any call.
    result = invoke(["admin", "intelligence", "companies", "create"])
    assert result.exit_code == 1
    assert "at least one" in result.output.lower()


def test_companies_update(invoke, mock_api):
    route = mock_api.patch("/api/v1/admin/intelligence/companies/co-1").respond(
        200, json={**SAMPLE_COMPANY, "name": "Renamed"}
    )
    result = invoke(["admin", "intelligence", "companies", "update", "co-1", "--name", "Renamed"])
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {"name": "Renamed"}


def test_companies_update_no_fields(invoke, mock_api):
    result = invoke(["admin", "intelligence", "companies", "update", "co-1"])
    assert result.exit_code == 1
    assert "No fields" in result.output


def test_companies_delete_yes(invoke, mock_api):
    mock_api.delete("/api/v1/admin/intelligence/companies/co-1").respond(200, json={"ok": True})
    result = invoke(["admin", "intelligence", "companies", "delete", "co-1", "--yes"])
    assert result.exit_code == 0


def test_companies_delete_abort(invoke, mock_api):
    result = invoke(["admin", "intelligence", "companies", "delete", "co-1"], input="n\n")
    assert result.exit_code == 1


def test_people_create(invoke, mock_api):
    route = mock_api.post("/api/v1/admin/intelligence/people").respond(201, json=SAMPLE_PERSON)
    result = invoke(
        [
            "admin",
            "intelligence",
            "people",
            "create",
            "--linkedin",
            "https://linkedin.com/in/jane",
            "--name",
            "Jane Doe",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body["linkedin_url"] == "https://linkedin.com/in/jane"
    assert body["full_name"] == "Jane Doe"


def test_people_update(invoke, mock_api):
    mock_api.patch("/api/v1/admin/intelligence/people/pe-1").respond(
        200, json={**SAMPLE_PERSON, "current_title": "CEO"}
    )
    result = invoke(["admin", "intelligence", "people", "update", "pe-1", "--title", "CEO"])
    assert result.exit_code == 0


def test_people_delete_yes(invoke, mock_api):
    mock_api.delete("/api/v1/admin/intelligence/people/pe-1").respond(200, json={"ok": True})
    result = invoke(["admin", "intelligence", "people", "delete", "pe-1", "--yes"])
    assert result.exit_code == 0
