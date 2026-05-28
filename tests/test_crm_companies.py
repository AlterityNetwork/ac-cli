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
    route = mock_api.get("/api/v1/crm/companies").respond(
        200,
        json={
            "data": [SAMPLE_COMPANY],
            "total": 1,
        },
    )
    result = invoke(["crm", "companies", "list"])
    assert result.exit_code == 0
    assert "Acme Corp" in result.output
    # Default projection sent as `view=full` so the server keeps the wide
    # list shape used by the CRM table.
    assert route.calls.last.request.url.params.get("view") == "full"


def test_companies_list_search_query(invoke, mock_api):
    route = mock_api.get("/api/v1/crm/companies").respond(
        200, json={"data": [SAMPLE_COMPANY], "total": 1}
    )
    result = invoke(["crm", "companies", "list", "--search", "Stripe"])
    assert result.exit_code == 0
    assert route.calls.last.request.url.params.get("q") == "Stripe"


def test_companies_list_view_options(invoke, mock_api):
    """ENG-933: ``--view options`` forwards ``view=options`` to the API."""
    route = mock_api.get("/api/v1/crm/companies").respond(
        200, json={"data": [SAMPLE_COMPANY], "total": 1}
    )
    result = invoke(["crm", "companies", "list", "--view", "options"])
    assert result.exit_code == 0
    assert route.calls.last.request.url.params.get("view") == "options"


def test_companies_list_lean_alias(invoke, mock_api):
    """ENG-933: ``--lean`` is a shortcut for ``--view options``."""
    route = mock_api.get("/api/v1/crm/companies").respond(
        200, json={"data": [SAMPLE_COMPANY], "total": 1}
    )
    result = invoke(["crm", "companies", "list", "--lean"])
    assert result.exit_code == 0
    assert route.calls.last.request.url.params.get("view") == "options"


def test_companies_list_rejects_invalid_view(invoke, mock_api):
    """ENG-933: unknown ``--view`` values are rejected by Typer before
    the request fires."""
    result = invoke(["crm", "companies", "list", "--view", "tiny"])
    assert result.exit_code != 0
    assert not mock_api.calls.called


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


def test_companies_get_compact_view(invoke, mock_api):
    """ENG-1115: --view compact forwards ?view=compact to the API."""
    route = mock_api.get(
        "/api/v1/crm/companies/c1",
        params={"view": "compact"},
    ).respond(200, json=SAMPLE_COMPANY)
    result = invoke(["crm", "companies", "get", "c1", "--view", "compact"])
    assert result.exit_code == 0
    assert route.called


def test_companies_get_full_view_omits_query_param(invoke, mock_api):
    """Default --view full sends no query param (backwards compat)."""
    route = mock_api.get("/api/v1/crm/companies/c1").respond(200, json=SAMPLE_COMPANY)
    result = invoke(["crm", "companies", "get", "c1"])
    assert result.exit_code == 0
    assert route.called
    assert "view=" not in str(route.calls.last.request.url)


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


def test_companies_by_ids(invoke, mock_api):
    rows = [
        {"id": "c1", "name": "Co1"},
        {"id": "c2", "name": "Co2"},
    ]
    route = mock_api.post("/api/v1/crm/companies/by-ids").respond(
        200,
        json={"data": rows, "total": 2, "limit": 2, "offset": 0, "has_more": False},
    )
    result = invoke(["crm", "companies", "by-ids", "--ids", "c1,c2"])
    assert result.exit_code == 0
    assert "Fetched 2 companies" in result.output
    body = json.loads(route.calls.last.request.content)
    assert body == {"ids": ["c1", "c2"]}


def test_companies_by_ids_json(invoke, mock_api):
    rows = [{"id": "c1", "name": "Co1"}]
    mock_api.post("/api/v1/crm/companies/by-ids").respond(
        200,
        json={"data": rows, "total": 1, "limit": 1, "offset": 0, "has_more": False},
    )
    result = invoke(["crm", "companies", "by-ids", "--ids", "c1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["total"] == 1
    assert parsed["data"][0]["id"] == "c1"


def test_companies_by_ids_empty(invoke, mock_api):
    result = invoke(["crm", "companies", "by-ids", "--ids", " , "])
    assert result.exit_code == 1
    assert "No IDs" in result.output


def test_companies_by_ids_api_error(invoke, mock_api):
    mock_api.post("/api/v1/crm/companies/by-ids").respond(422, json={"detail": "ids too long"})
    result = invoke(["crm", "companies", "by-ids", "--ids", "c1"])
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


def test_companies_mark_actioned(invoke, mock_api):
    route = mock_api.post("/api/v1/crm/companies/mark-actioned").respond(
        200, json={"updated_count": 2}
    )
    result = invoke(["crm", "companies", "mark-actioned", "--ids", "c1,c2"])
    assert result.exit_code == 0
    assert "Marked 2 companies actioned" in result.output
    body = json.loads(route.calls.last.request.content)
    assert body == {"ids": ["c1", "c2"], "note": None}


def test_companies_mark_actioned_with_note(invoke, mock_api):
    route = mock_api.post("/api/v1/crm/companies/mark-actioned").respond(
        200, json={"updated_count": 1}
    )
    result = invoke(
        [
            "crm",
            "companies",
            "mark-actioned",
            "--ids",
            "c1",
            "--note",
            "Sent LinkedIn connection",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body == {"ids": ["c1"], "note": "Sent LinkedIn connection"}


def test_companies_mark_actioned_json(invoke, mock_api):
    mock_api.post("/api/v1/crm/companies/mark-actioned").respond(200, json={"updated_count": 2})
    result = invoke(["crm", "companies", "mark-actioned", "--ids", "c1,c2", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {"updated_count": 2}


def test_companies_mark_actioned_empty_ids(invoke, mock_api):
    result = invoke(["crm", "companies", "mark-actioned", "--ids", " "])
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


SAMPLE_ENRICH_RESPONSE = {
    "data": {
        "company_name": "Reddit, Inc.",
        "website_url": "https://www.redditinc.com",
        "industry": "Social Networking Platforms",
        "employee_count": "1001-5000",
        "revenue_band": "1B-10B",
        "country": "US",
        "city": "San Francisco",
        "region": "California",
    },
    "source": "explorium",
}


def test_companies_enrich(invoke, mock_api):
    route = mock_api.post("/api/v1/crm/companies/enrich").respond(200, json=SAMPLE_ENRICH_RESPONSE)
    result = invoke(["crm", "companies", "enrich", "https://reddit.com"])
    assert result.exit_code == 0, result.output
    assert "Reddit, Inc." in result.output
    assert "explorium" in result.output  # source label surfaced
    body = json.loads(route.calls.last.request.content)
    assert body == {"url": "https://reddit.com"}


def test_companies_enrich_with_provider(invoke, mock_api):
    route = mock_api.post("/api/v1/crm/companies/enrich").respond(200, json=SAMPLE_ENRICH_RESPONSE)
    result = invoke(
        [
            "crm",
            "companies",
            "enrich",
            "https://reddit.com",
            "--provider",
            "hunter",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body == {"url": "https://reddit.com", "provider": "hunter"}


def test_companies_enrich_json(invoke, mock_api):
    mock_api.post("/api/v1/crm/companies/enrich").respond(200, json=SAMPLE_ENRICH_RESPONSE)
    result = invoke(["crm", "companies", "enrich", "https://reddit.com", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["source"] == "explorium"
    assert payload["data"]["company_name"] == "Reddit, Inc."


def test_companies_enrich_unknown_provider_rejected(invoke, mock_api):
    # Validation happens at the API layer (422). The CLI surfaces semantic
    # exit code 2.
    mock_api.post("/api/v1/crm/companies/enrich").respond(
        422, json={"detail": [{"msg": "Invalid provider"}]}
    )
    result = invoke(["crm", "companies", "enrich", "https://reddit.com", "--provider", "banana"])
    assert result.exit_code == 2
