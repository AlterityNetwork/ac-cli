"""Tests for admin limit-overrides commands."""

import json

ORG = "org-1"
BASE = f"/api/v1/admin/organizations/{ORG}/limit-overrides"

OVERRIDE = {
    "organization_id": ORG,
    "limit_name": "email_sends_per_day",
    "value": 50,
    "set_by": "admin-1",
    "created_at": "2026-10-29T10:00:00+00:00",
    "updated_at": "2026-10-29T10:00:00+00:00",
}
LIST = {
    "overrides": [OVERRIDE],
    "plan_limits": {"seats": 3, "email_sends_per_day": 200},
    "limits": {"seats": 3, "email_sends_per_day": 50},
}


def test_limit_overrides_list(invoke, mock_api):
    mock_api.get(BASE).respond(200, json=LIST)
    result = invoke(["admin", "limit-overrides", "list", "--org-id", ORG])
    assert result.exit_code == 0
    assert "email_sends_per_day" in result.output
    assert "200" in result.output
    assert "50" in result.output


def test_limit_overrides_list_json(invoke, mock_api):
    mock_api.get(BASE).respond(200, json=LIST)
    result = invoke(["admin", "limit-overrides", "list", "--org-id", ORG, "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["limits"]["email_sends_per_day"] == 50


def test_limit_overrides_set(invoke, mock_api):
    route = mock_api.put(f"{BASE}/email_sends_per_day").respond(200, json=OVERRIDE)
    result = invoke(
        [
            "admin",
            "limit-overrides",
            "set",
            "--org-id",
            ORG,
            "--limit",
            "email_sends_per_day",
            "--value",
            "50",
        ]
    )
    assert result.exit_code == 0
    assert json.loads(route.calls[0].request.content) == {"value": 50}
    assert "50" in result.output


def test_limit_overrides_set_json(invoke, mock_api):
    mock_api.put(f"{BASE}/email_sends_per_day").respond(200, json=OVERRIDE)
    result = invoke(
        [
            "admin",
            "limit-overrides",
            "set",
            "--org-id",
            ORG,
            "--value",
            "50",
            "--json",
        ]
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["value"] == 50


def test_limit_overrides_set_invalid_maps_exit_code(invoke, mock_api):
    mock_api.put(f"{BASE}/email_sends_per_day").respond(
        422, json={"detail": "value must be at least 0"}
    )
    result = invoke(["admin", "limit-overrides", "set", "--org-id", ORG, "--value", "-1", "--json"])
    assert result.exit_code == 2


def test_limit_overrides_clear(invoke, mock_api):
    route = mock_api.delete(f"{BASE}/email_sends_per_day").respond(204)
    result = invoke(["admin", "limit-overrides", "clear", "--org-id", ORG, "--yes"])
    assert result.exit_code == 0
    assert route.called


def test_limit_overrides_clear_aborted(invoke, mock_api):
    result = invoke(["admin", "limit-overrides", "clear", "--org-id", ORG], input="n\n")
    assert result.exit_code == 1


def test_limit_overrides_clear_not_found(invoke, mock_api):
    mock_api.delete(f"{BASE}/email_sends_per_day").respond(
        404, json={"detail": "Limit override not found"}
    )
    result = invoke(["admin", "limit-overrides", "clear", "--org-id", ORG, "--yes", "--json"])
    assert result.exit_code == 3
