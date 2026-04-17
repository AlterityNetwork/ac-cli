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
    mock_api.get("/api/v1/crm/deals").respond(200, json=[SAMPLE_DEAL])
    result = invoke(["crm", "deals", "list"])
    assert result.exit_code == 0
    assert "Enterprise Contract" in result.output


def test_deals_list_json(invoke, mock_api):
    mock_api.get("/api/v1/crm/deals").respond(200, json=[SAMPLE_DEAL])
    result = invoke(["crm", "deals", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["name"] == "Enterprise Contract"


def test_deals_list_with_filters(invoke, mock_api):
    mock_api.get("/api/v1/crm/deals").respond(200, json=[])
    result = invoke(["crm", "deals", "list", "--stage", "lead", "--company-id", "c1"])
    assert result.exit_code == 0


def test_deals_list_sort_by_value_desc(invoke, mock_api):
    """--sort-by value --order desc maps to sort_by/order query params."""
    route = mock_api.get("/api/v1/crm/deals").respond(200, json=[])
    result = invoke(
        ["crm", "deals", "list", "--sort-by", "value", "--order", "desc", "--json"]
    )
    assert result.exit_code == 0
    assert route.called
    request = route.calls.last.request
    assert "sort_by=value" in str(request.url)
    assert "order=desc" in str(request.url)


def test_deals_list_close_date_range(invoke, mock_api):
    """--close-after and --close-before pass through as query params."""
    route = mock_api.get("/api/v1/crm/deals").respond(200, json=[])
    result = invoke(
        [
            "crm", "deals", "list",
            "--close-after", "2026-04-01",
            "--close-before", "2026-04-30",
            "--json",
        ]
    )
    assert result.exit_code == 0
    request = route.calls.last.request
    assert "close_after=2026-04-01" in str(request.url)
    assert "close_before=2026-04-30" in str(request.url)


def test_deals_list_limit_top_5(invoke, mock_api):
    """--limit 5 caps the page to 5 so `top 5 deals by value` works end-to-end."""
    route = mock_api.get("/api/v1/crm/deals").respond(200, json=[])
    result = invoke(
        ["crm", "deals", "list", "--sort-by", "value", "--order", "desc", "--limit", "5"]
    )
    assert result.exit_code == 0
    request = route.calls.last.request
    assert "limit=5" in str(request.url)


def test_deals_get(invoke, mock_api):
    mock_api.get("/api/v1/crm/deals/d1").respond(200, json=SAMPLE_DEAL)
    result = invoke(["crm", "deals", "get", "d1"])
    assert result.exit_code == 0
    assert "Enterprise Contract" in result.output
    assert "50000" in result.output


def test_deals_create(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/crm/deals").respond(201, json=SAMPLE_DEAL)
    result = invoke(["crm", "deals", "create", "--name", "Enterprise Contract", "--amount", "50000"])
    assert result.exit_code == 0
    assert "Created deal" in result.output


def test_deals_update(invoke, mock_api):
    updated = {**SAMPLE_DEAL, "stage": "qualified"}
    mock_api.patch("/api/v1/crm/deals/d1").respond(200, json=updated)
    result = invoke(["crm", "deals", "update", "d1", "--stage", "qualified"])
    assert result.exit_code == 0
    assert "Updated deal" in result.output


def test_deals_update_no_fields(invoke, mock_api):
    result = invoke(["crm", "deals", "update", "d1"])
    assert result.exit_code == 1


def test_deals_move(invoke, mock_api):
    moved = {**SAMPLE_DEAL, "stage": "proposal"}
    mock_api.patch("/api/v1/crm/deals/d1/stage").respond(200, json=moved)
    result = invoke(["crm", "deals", "move", "d1", "--stage", "proposal"])
    assert result.exit_code == 0
    assert "Moved deal to proposal" in result.output


def test_deals_order(invoke, mock_api):
    mock_api.post("/api/v1/crm/deals/order").respond(200, json={"ordered": True})
    result = invoke(["crm", "deals", "order", "--stage", "lead", "--deal-ids", "d1,d2,d3"])
    assert result.exit_code == 0
    assert "Reordered 3 deals" in result.output
    assert "lead" in result.output


def test_deals_order_json(invoke, mock_api):
    mock_api.post("/api/v1/crm/deals/order").respond(200, json={"ordered": True})
    result = invoke(["crm", "deals", "order", "--stage", "lead", "--deal-ids", "d1,d2", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["ordered"] is True


def test_deals_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/crm/deals/d1").respond(204)
    result = invoke(["crm", "deals", "delete", "d1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_deals_delete_json(invoke, mock_api):
    mock_api.delete("/api/v1/crm/deals/d1").respond(204)
    result = invoke(["crm", "deals", "delete", "d1", "--yes", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed == {"ok": True, "id": "d1", "action": "delete"}


def test_deals_delete_aborted(invoke, mock_api):
    result = invoke(["crm", "deals", "delete", "d1"], input="n\n")
    assert result.exit_code == 1
