"""Tests for admin app management commands."""

import json


SAMPLE_APP = {"id": "app-1", "name": "Email Finder", "slug": "email-finder", "status": "active"}


def test_apps_list(invoke, mock_api):
    mock_api.get("/api/v1/admin/apps").respond(200, json=[SAMPLE_APP])
    result = invoke(["admin", "apps", "list"])
    assert result.exit_code == 0
    assert "Email Finder" in result.output


def test_apps_list_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/apps").respond(200, json=[SAMPLE_APP])
    result = invoke(["admin", "apps", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)


def test_apps_update(invoke, mock_api):
    mock_api.patch("/api/v1/admin/apps/app-1").respond(200, json={**SAMPLE_APP, "name": "Updated"})
    result = invoke(["admin", "apps", "update", "app-1", "--name", "Updated"])
    assert result.exit_code == 0
    assert "Updated" in result.output


def test_apps_update_json(invoke, mock_api):
    mock_api.patch("/api/v1/admin/apps/app-1").respond(200, json={**SAMPLE_APP, "name": "Updated"})
    result = invoke(["admin", "apps", "update", "app-1", "--name", "Updated", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["name"] == "Updated"


def test_apps_update_no_fields(invoke, mock_api):
    result = invoke(["admin", "apps", "update", "app-1"])
    assert result.exit_code == 1


def test_apps_sync_icons(invoke, mock_api):
    mock_api.post("/api/v1/admin/apps/sync-icons").respond(200, json={"synced": 5})
    result = invoke(["admin", "apps", "sync-icons"])
    assert result.exit_code == 0
    assert "synced" in result.output.lower()


def test_apps_sync_icons_json(invoke, mock_api):
    mock_api.post("/api/v1/admin/apps/sync-icons").respond(200, json={"synced": 5})
    result = invoke(["admin", "apps", "sync-icons", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["synced"] == 5
