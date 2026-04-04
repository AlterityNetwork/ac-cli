"""Tests for admin analytics-overview command."""

import json


SAMPLE_OVERVIEW = {
    "ai_requests_per_day": 42.5,
    "app_runs_per_day": 15.0,
    "platform_events_per_day": 100.0,
    "active_user_rate": 75.0,
    "total_active_users": 12,
    "total_org_members": 16,
    "ai_total_cost": 123.45,
    "ai_change_cost": -5.2,
    "app_total_runs": 450,
    "app_change_runs": 10.0,
    "platform_total_events": 3000,
    "platform_change_events": 3.5,
}


def test_analytics_overview(invoke, mock_api):
    mock_api.get("/api/v1/admin/analytics-overview/summary").respond(
        200, json=SAMPLE_OVERVIEW
    )
    result = invoke(["admin", "analytics-overview"])
    assert result.exit_code == 0
    assert "Analytics Overview" in result.output
    assert "42.5" in result.output
    assert "$123.45" in result.output


def test_analytics_overview_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/analytics-overview/summary").respond(
        200, json=SAMPLE_OVERVIEW
    )
    result = invoke(["admin", "analytics-overview", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["ai_requests_per_day"] == 42.5
    assert parsed["total_active_users"] == 12


def test_analytics_overview_with_filters(invoke, mock_api):
    mock_api.get("/api/v1/admin/analytics-overview/summary").respond(
        200, json=SAMPLE_OVERVIEW
    )
    result = invoke([
        "admin", "analytics-overview",
        "--start-date", "2026-03-01",
        "--end-date", "2026-03-31",
        "--org-id", "org-123",
    ])
    assert result.exit_code == 0
    assert "Analytics Overview" in result.output


def test_analytics_overview_api_error(invoke, mock_api):
    """API 403 returns exit code 4."""
    mock_api.get("/api/v1/admin/analytics-overview/summary").respond(
        403, json={"detail": "Forbidden"}
    )
    result = invoke(["admin", "analytics-overview"])
    assert result.exit_code == 4
    assert "403" in result.output


def test_analytics_overview_api_error_json(invoke, mock_api):
    """API error with --json returns structured JSON error."""
    mock_api.get("/api/v1/admin/analytics-overview/summary").respond(
        403, json={"detail": "Forbidden"}
    )
    result = invoke(["admin", "analytics-overview", "--json"])
    assert result.exit_code == 4
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 403
