"""Tests for CRM deals commands."""

import json

from tests.conftest import WHOAMI_RESPONSE


SAMPLE_DEAL = {
    "id": "d1",
    "organization_id": "org-456",
    "name": "Enterprise Contract",
    "stage": "lead",
    "amount": "50000.00",
    "currency": "USD",
    "expected_close_date": "2026-06-01",
    "tags": [],
    "competitors": [],
    "custom_fields": {},
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def test_deals_list(invoke, mock_api):
    mock_api.get("/crm/deals").respond(200, json=[SAMPLE_DEAL])
    result = invoke(["crm", "deals", "list"])
    assert result.exit_code == 0
    assert "Enterprise Contract" in result.output


def test_deals_list_json(invoke, mock_api):
    mock_api.get("/crm/deals").respond(200, json=[SAMPLE_DEAL])
    result = invoke(["crm", "--json", "deals", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["name"] == "Enterprise Contract"


def test_deals_list_with_filters(invoke, mock_api):
    mock_api.get("/crm/deals").respond(200, json=[])
    result = invoke(["crm", "deals", "list", "--stage", "lead", "--company-id", "c1"])
    assert result.exit_code == 0


def test_deals_get(invoke, mock_api):
    mock_api.get("/crm/deals/d1").respond(200, json=SAMPLE_DEAL)
    result = invoke(["crm", "deals", "get", "d1"])
    assert result.exit_code == 0
    assert "Enterprise Contract" in result.output
    assert "50000" in result.output


def test_deals_create(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/crm/deals").respond(201, json=SAMPLE_DEAL)
    result = invoke(["crm", "deals", "create", "--name", "Enterprise Contract", "--amount", "50000"])
    assert result.exit_code == 0
    assert "Created deal" in result.output


def test_deals_update(invoke, mock_api):
    updated = {**SAMPLE_DEAL, "stage": "qualified"}
    mock_api.patch("/crm/deals/d1").respond(200, json=updated)
    result = invoke(["crm", "deals", "update", "d1", "--stage", "qualified"])
    assert result.exit_code == 0
    assert "Updated deal" in result.output


def test_deals_update_no_fields(invoke, mock_api):
    result = invoke(["crm", "deals", "update", "d1"])
    assert result.exit_code == 1


def test_deals_move(invoke, mock_api):
    moved = {**SAMPLE_DEAL, "stage": "proposal"}
    mock_api.patch("/crm/deals/d1/stage").respond(200, json=moved)
    result = invoke(["crm", "deals", "move", "d1", "--stage", "proposal"])
    assert result.exit_code == 0
    assert "Moved deal to proposal" in result.output


def test_deals_delete_with_yes(invoke, mock_api):
    mock_api.delete("/crm/deals/d1").respond(204)
    result = invoke(["crm", "deals", "delete", "d1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_deals_delete_aborted(invoke, mock_api):
    result = invoke(["crm", "deals", "delete", "d1"], input="n\n")
    assert result.exit_code == 1
