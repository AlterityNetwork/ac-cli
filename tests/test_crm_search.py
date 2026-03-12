"""Tests for CRM search command."""

import json

import httpx
import respx

from tests.conftest import WHOAMI_RESPONSE


def test_search_happy_path(invoke, mock_api):
    mock_api.get("/crm/search").respond(200, json={
        "companies": [{"name": "Acme", "industry": "SaaS", "id": "c1"}],
        "contacts": [{"full_name": "Jane", "email": "jane@acme.com", "id": "p1"}],
        "deals": [{"name": "Big Deal", "stage": "lead", "id": "d1"}],
    })
    result = invoke(["crm", "search", "acme"])
    assert result.exit_code == 0
    assert "Acme" in result.output
    assert "Jane" in result.output
    assert "Big Deal" in result.output


def test_search_json_flag(invoke, mock_api):
    payload = {
        "companies": [{"name": "Acme", "industry": "SaaS", "id": "c1"}],
        "contacts": [],
        "deals": [],
    }
    mock_api.get("/crm/search").respond(200, json=payload)
    result = invoke(["crm", "--json", "search", "acme"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["companies"][0]["name"] == "Acme"


def test_search_no_results(invoke, mock_api):
    mock_api.get("/crm/search").respond(200, json={
        "companies": [], "contacts": [], "deals": [],
    })
    result = invoke(["crm", "search", "nonexistent"])
    assert result.exit_code == 0
    assert "No results found" in result.output


def test_search_api_error(invoke, mock_api):
    mock_api.get("/crm/search").respond(404, json={"detail": "Not found"})
    result = invoke(["crm", "search", "bad"])
    assert result.exit_code == 1
    assert "404" in result.output
