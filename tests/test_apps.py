"""Tests for organization apps commands."""

import json

from tests.conftest import WHOAMI_RESPONSE

SAMPLE_APP = {
    "app_slug": "email-finder",
    "status": "active",
    "installed_at": "2026-01-01T00:00:00Z",
    "organization_id": "org-456",
}

SAMPLE_CONFIG = {
    "config_key": "api_key",
    "value": "sk-***",
}


def test_apps_list(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.get("/api/v1/orgs/org-456/apps").respond(200, json=[SAMPLE_APP])
    result = invoke(["apps", "list"])
    assert result.exit_code == 0
    assert "email-finder" in result.output


def test_apps_list_json(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    payload = [SAMPLE_APP]
    mock_api.get("/api/v1/orgs/org-456/apps").respond(200, json=payload)
    result = invoke(["apps", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["app_slug"] == "email-finder"


def test_apps_list_with_org_id(invoke, mock_api):
    mock_api.get("/api/v1/orgs/org-456/apps").respond(200, json=[SAMPLE_APP])
    result = invoke(["apps", "list", "--org-id", "org-456"])
    assert result.exit_code == 0
    assert "email-finder" in result.output


def test_apps_install(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/orgs/org-456/apps/email-finder").respond(201, json=SAMPLE_APP)
    result = invoke(["apps", "install", "email-finder"])
    assert result.exit_code == 0
    assert "Installed" in result.output
    assert "email-finder" in result.output


def test_apps_uninstall_with_yes(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.delete("/api/v1/orgs/org-456/apps/email-finder").respond(204)
    result = invoke(["apps", "uninstall", "email-finder", "--yes"])
    assert result.exit_code == 0
    assert "Uninstalled" in result.output


def test_apps_uninstall_aborted(invoke, mock_api):
    result = invoke(["apps", "uninstall", "email-finder"], input="n\n")
    assert result.exit_code == 1


def test_apps_usage_event(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/orgs/org-456/apps/email-finder/events").respond(
        201, json={"event_type": "search", "app_slug": "email-finder"},
    )
    result = invoke(["apps", "usage-event", "email-finder", "--event-type", "search"])
    assert result.exit_code == 0
    assert "Recorded usage event" in result.output


def test_apps_usage(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.get("/api/v1/orgs/org-456/apps/email-finder/usage").respond(
        200, json={"app_slug": "email-finder", "total_events": 42, "last_event_at": "2026-01-15T00:00:00Z"},
    )
    result = invoke(["apps", "usage", "email-finder"])
    assert result.exit_code == 0
    assert "email-finder" in result.output


def test_apps_configs(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.get("/api/v1/orgs/org-456/apps/email-finder/configs").respond(200, json=[SAMPLE_CONFIG])
    result = invoke(["apps", "configs", "email-finder"])
    assert result.exit_code == 0
    assert "api_key" in result.output


def test_apps_configs_json(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    payload = [SAMPLE_CONFIG]
    mock_api.get("/api/v1/orgs/org-456/apps/email-finder/configs").respond(200, json=payload)
    result = invoke(["apps", "configs", "email-finder", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["config_key"] == "api_key"


def test_apps_update_config(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.put("/api/v1/orgs/org-456/apps/email-finder/configs/api_key").respond(
        200, json={"config_key": "api_key", "value": "sk-new"},
    )
    result = invoke(["apps", "update-config", "email-finder", "api_key", "--value", "sk-new"])
    assert result.exit_code == 0
    assert "Updated config" in result.output


def test_apps_delete_config_with_yes(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.delete("/api/v1/orgs/org-456/apps/email-finder/configs/api_key").respond(204)
    result = invoke(["apps", "delete-config", "email-finder", "api_key", "--yes"])
    assert result.exit_code == 0
    assert "Deleted config" in result.output


def test_apps_delete_config_aborted(invoke, mock_api):
    result = invoke(["apps", "delete-config", "email-finder", "api_key"], input="n\n")
    assert result.exit_code == 1


def test_apps_install_error(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/orgs/org-456/apps/email-finder").respond(409, json={"detail": "Already installed"})
    result = invoke(["apps", "install", "email-finder"])
    assert result.exit_code == 5
    assert "409" in result.output
