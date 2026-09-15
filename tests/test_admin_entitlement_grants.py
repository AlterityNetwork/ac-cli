"""Tests for admin entitlement-grants commands."""

import json

ORG = "org-1"
BASE = f"/api/v1/admin/organizations/{ORG}/entitlement-grants"

SAMPLE_GRANT = {
    "id": "grant-1",
    "organization_id": ORG,
    "key": "network",
    "mode": "grant",
    "source": "comp",
    "expires_at": None,
    "granted_by": "admin-1",
    "created_at": "2026-09-15T12:00:00+00:00",
}

SAMPLE_LIST = {
    "grants": [SAMPLE_GRANT],
    "snapshot": {
        "keys": ["crm", "network"],
        "credits": {"allowance": 500},
        "limits": {"seats": 3, "email_sends_per_day": None},
        "trials": [],
        "access_mode": "full",
    },
}


def test_grants_list(invoke, mock_api):
    mock_api.get(BASE).respond(200, json=SAMPLE_LIST)
    result = invoke(["admin", "entitlement-grants", "list", "--org-id", ORG])
    assert result.exit_code == 0
    assert "crm, network" in result.output
    assert "network" in result.output
    assert "comp" in result.output


def test_grants_list_json(invoke, mock_api):
    mock_api.get(BASE).respond(200, json=SAMPLE_LIST)
    result = invoke(["admin", "entitlement-grants", "list", "--org-id", ORG, "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["snapshot"]["access_mode"] == "full"


def test_grants_create(invoke, mock_api):
    route = mock_api.post(BASE).respond(201, json=SAMPLE_GRANT)
    result = invoke(
        [
            "admin",
            "entitlement-grants",
            "create",
            "--org-id",
            ORG,
            "--key",
            "network",
            "--source",
            "comp",
        ]
    )
    assert result.exit_code == 0
    assert "Created grant row for network" in result.output
    body = json.loads(route.calls[0].request.content)
    assert body == {"key": "network", "source": "comp", "mode": "grant"}


def test_grants_create_trial_with_expiry(invoke, mock_api):
    route = mock_api.post(BASE).respond(
        201,
        json={**SAMPLE_GRANT, "source": "trial", "expires_at": "2026-10-01T00:00:00+00:00"},
    )
    result = invoke(
        [
            "admin",
            "entitlement-grants",
            "create",
            "--org-id",
            ORG,
            "--key",
            "chat",
            "--source",
            "trial",
            "--expires-at",
            "2026-10-01T00:00:00+00:00",
            "--json",
        ]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert body["expires_at"] == "2026-10-01T00:00:00+00:00"
    assert json.loads(result.output)["source"] == "trial"


def test_grants_create_validation_error(invoke, mock_api):
    mock_api.post(BASE).respond(422, json={"detail": [{"msg": "A trial needs an expiry"}]})
    result = invoke(
        [
            "admin",
            "entitlement-grants",
            "create",
            "--org-id",
            ORG,
            "--key",
            "chat",
            "--source",
            "trial",
        ]
    )
    assert result.exit_code != 0


def test_grants_delete_with_yes(invoke, mock_api):
    mock_api.delete(f"{BASE}/grant-1").respond(204)
    result = invoke(["admin", "entitlement-grants", "delete", "grant-1", "--org-id", ORG, "--yes"])
    assert result.exit_code == 0
    assert "Deleted entitlement grant" in result.output


def test_grants_delete_aborted(invoke, mock_api):
    result = invoke(
        ["admin", "entitlement-grants", "delete", "grant-1", "--org-id", ORG],
        input="n\n",
    )
    assert result.exit_code == 1


def test_grants_delete_not_found(invoke, mock_api):
    mock_api.delete(f"{BASE}/missing").respond(404, json={"detail": "Entitlement grant not found"})
    result = invoke(["admin", "entitlement-grants", "delete", "missing", "--org-id", ORG, "--yes"])
    assert result.exit_code != 0
