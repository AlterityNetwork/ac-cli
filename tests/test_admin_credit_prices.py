"""Tests for `ac admin credit-prices` commands."""

import json

BASE = "/api/v1/admin/credit-prices"

SAMPLE_PRICE = {
    "id": "price-1",
    "action_key": "people.search",
    "unit": "company",
    "credits": 35,
    "minimum_credits": 150,
    "version": 2,
    "effective_from": "2026-12-01T00:00:00+00:00",
    "created_by": "admin-1",
    "created_at": "2026-10-26T12:00:00+00:00",
}


# --- list ------------------------------------------------------------------


def test_credit_prices_list(invoke, mock_api):
    route = mock_api.get(BASE).respond(200, json=[SAMPLE_PRICE])
    result = invoke(["admin", "credit-prices", "list"])
    assert result.exit_code == 0
    assert "people.search" in result.output
    assert "company" in result.output
    assert "150" in result.output
    params = route.calls[0].request.url.params
    assert params["latest_only"] == "true"
    assert "action_key" not in params


def test_credit_prices_list_filters_by_action_key(invoke, mock_api):
    route = mock_api.get(BASE).respond(200, json=[SAMPLE_PRICE])
    result = invoke(["admin", "credit-prices", "list", "--action-key", "people.search"])
    assert result.exit_code == 0
    assert route.calls[0].request.url.params["action_key"] == "people.search"


def test_credit_prices_list_all_versions(invoke, mock_api):
    route = mock_api.get(BASE).respond(200, json=[SAMPLE_PRICE, {**SAMPLE_PRICE, "version": 1}])
    result = invoke(["admin", "credit-prices", "list", "--all-versions"])
    assert result.exit_code == 0
    assert route.calls[0].request.url.params["latest_only"] == "false"


def test_credit_prices_list_empty(invoke, mock_api):
    mock_api.get(BASE).respond(200, json=[])
    result = invoke(["admin", "credit-prices", "list"])
    assert result.exit_code == 0
    assert "No credit prices" in result.output


def test_credit_prices_list_json(invoke, mock_api):
    mock_api.get(BASE).respond(200, json=[SAMPLE_PRICE])
    result = invoke(["admin", "credit-prices", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)[0]["minimum_credits"] == 150


def test_credit_prices_list_forbidden(invoke, mock_api):
    mock_api.get(BASE).respond(403, json={"detail": "Super admin only"})
    result = invoke(["admin", "credit-prices", "list", "--json"])
    assert result.exit_code == 4
    assert json.loads(result.output)["status_code"] == 403


# --- create ----------------------------------------------------------------


def _create(invoke, *extra: str):
    return invoke(
        [
            "admin",
            "credit-prices",
            "create",
            "--action-key",
            "people.search",
            "--unit",
            "company",
            *extra,
        ]
    )


def test_credit_prices_create_minimal(invoke, mock_api):
    route = mock_api.post(BASE).respond(
        201, json={**SAMPLE_PRICE, "credits": 30, "minimum_credits": 0}
    )
    result = _create(invoke, "--credits", "30")
    assert result.exit_code == 0
    assert "Created people.search version 2: 30 credits per company" in result.output
    body = json.loads(route.calls[0].request.content)
    assert body == {"action_key": "people.search", "unit": "company", "credits": 30}


def test_credit_prices_create_with_minimum_and_date(invoke, mock_api):
    route = mock_api.post(BASE).respond(201, json=SAMPLE_PRICE)
    result = _create(
        invoke,
        "--credits",
        "35",
        "--minimum-credits",
        "150",
        "--effective-from",
        "2026-12-01T00:00:00+00:00",
    )
    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert body == {
        "action_key": "people.search",
        "unit": "company",
        "credits": 35,
        "minimum_credits": 150,
        "effective_from": "2026-12-01T00:00:00+00:00",
    }


def test_credit_prices_create_keeps_zero_credits(invoke, mock_api):
    """A zero price is a real price, so the body keeps it."""
    route = mock_api.post(BASE).respond(201, json={**SAMPLE_PRICE, "credits": 0})
    result = _create(invoke, "--credits", "0", "--minimum-credits", "0")
    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert body["credits"] == 0
    assert body["minimum_credits"] == 0


def test_credit_prices_create_json(invoke, mock_api):
    mock_api.post(BASE).respond(201, json=SAMPLE_PRICE)
    result = _create(invoke, "--credits", "35", "--json")
    assert result.exit_code == 0
    assert json.loads(result.output)["version"] == 2


def test_credit_prices_create_conflict(invoke, mock_api):
    mock_api.post(BASE).respond(409, json={"detail": "A concurrent write took version 3"})
    result = _create(invoke, "--credits", "35")
    assert result.exit_code == 5
    assert "version 3" in result.output


def test_credit_prices_create_validation_error(invoke, mock_api):
    mock_api.post(BASE).respond(
        422,
        json={
            "error": "Validation Error",
            "message": "The request contains invalid data.",
            "type": "request_validation_error",
            "details": [{"loc": ["body", "effective_from"], "msg": "too soon"}],
        },
    )
    result = _create(invoke, "--credits", "35", "--json")
    assert result.exit_code == 2
    assert json.loads(result.output)["status_code"] == 422


def test_credit_prices_create_forbidden(invoke, mock_api):
    mock_api.post(BASE).respond(403, json={"detail": "Super admin only"})
    result = _create(invoke, "--credits", "35")
    assert result.exit_code == 4
