"""Tests for marketplace commands."""

import json

SAMPLE_APP = {
    "slug": "email-finder",
    "name": "Email Finder",
    "category": "data",
    "status": "active",
    "developer_name": "AgencyCore",
}
SAMPLE_DEV = {"id": "dev-1", "name": "AgencyCore", "app_count": 3}


def test_list(invoke, mock_api):
    mock_api.get("/api/v1/marketplace/apps").respond(200, json=[SAMPLE_APP])
    result = invoke(["marketplace", "list"])
    assert result.exit_code == 0
    assert "Email Finder" in result.output


def test_list_json(invoke, mock_api):
    mock_api.get("/api/v1/marketplace/apps").respond(200, json=[SAMPLE_APP])
    result = invoke(["marketplace", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)


def test_list_with_category(invoke, mock_api):
    mock_api.get("/api/v1/marketplace/apps").respond(200, json=[])
    result = invoke(["marketplace", "list", "--category", "data"])
    assert result.exit_code == 0


def test_get(invoke, mock_api):
    mock_api.get("/api/v1/marketplace/apps/email-finder").respond(200, json=SAMPLE_APP)
    result = invoke(["marketplace", "get", "email-finder"])
    assert result.exit_code == 0
    assert "Email Finder" in result.output


def test_get_json(invoke, mock_api):
    mock_api.get("/api/v1/marketplace/apps/email-finder").respond(200, json=SAMPLE_APP)
    result = invoke(["marketplace", "get", "email-finder", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["slug"] == "email-finder"


def test_get_404(invoke, mock_api):
    mock_api.get("/api/v1/marketplace/apps/nonexistent").respond(404, json={"detail": "Not found"})
    result = invoke(["marketplace", "get", "nonexistent"])
    assert result.exit_code == 3


def test_developers(invoke, mock_api):
    mock_api.get("/api/v1/marketplace/developers").respond(200, json=[SAMPLE_DEV])
    result = invoke(["marketplace", "developers"])
    assert result.exit_code == 0
    assert "AgencyCore" in result.output


def test_developers_json(invoke, mock_api):
    mock_api.get("/api/v1/marketplace/developers").respond(200, json=[SAMPLE_DEV])
    result = invoke(["marketplace", "developers", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
