"""Tests for admin AI usage by-app command."""

import json

SAMPLE_BY_APP = [{"app_id": "email-finder", "requests": 100, "tokens": 5000, "cost": 0.50}]


def test_by_app(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/by-app").respond(200, json=SAMPLE_BY_APP)
    result = invoke(["admin", "ai-usage", "by-app"])
    assert result.exit_code == 0
    assert "email-finder" in result.output


def test_by_app_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/by-app").respond(200, json=SAMPLE_BY_APP)
    result = invoke(["admin", "ai-usage", "by-app", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["app_id"] == "email-finder"


def test_by_app_with_filters(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/by-app").respond(200, json=[])
    result = invoke(
        ["admin", "ai-usage", "by-app", "--start-date", "2026-01-01", "--org-id", "org-1"]
    )
    assert result.exit_code == 0


def test_by_app_403(invoke, mock_api):
    mock_api.get("/api/v1/admin/ai-usage/by-app").respond(403, json={"detail": "Forbidden"})
    result = invoke(["admin", "ai-usage", "by-app"])
    assert result.exit_code == 4
