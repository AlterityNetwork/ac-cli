"""Tests for CRM engagement-dashboard command."""

import json

SAMPLE_ENGAGEMENT = {
    "period_days": 30,
    "emails_sent": {
        "current_period": 150,
        "previous_period": 120,
        "change": 30,
    },
    "open_rate": 45.2,
    "click_rate": 12.8,
    "reply_rate": 8.5,
    "bounce_rate": 1.2,
    "email_health": {
        "score": 92,
        "status": "healthy",
    },
    "top_clicked_links": [
        {"url": "https://example.com/pricing", "clicks": 45},
        {"url": "https://example.com/demo", "clicks": 32},
    ],
}


def test_engagement_dashboard_default(invoke, mock_api):
    mock_api.get("/api/v1/crm/engagement-dashboard").respond(200, json=SAMPLE_ENGAGEMENT)
    result = invoke(["crm", "engagement-dashboard"])
    assert result.exit_code == 0
    assert "150" in result.output
    assert "45.2" in result.output


def test_engagement_dashboard_custom_period(invoke, mock_api):
    mock_api.get("/api/v1/crm/engagement-dashboard").respond(200, json=SAMPLE_ENGAGEMENT)
    result = invoke(["crm", "engagement-dashboard", "--period", "60"])
    assert result.exit_code == 0


def test_engagement_dashboard_json(invoke, mock_api):
    mock_api.get("/api/v1/crm/engagement-dashboard").respond(200, json=SAMPLE_ENGAGEMENT)
    result = invoke(["crm", "engagement-dashboard", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["open_rate"] == 45.2


def test_engagement_dashboard_period_passed_as_param(invoke, mock_api):
    route = mock_api.get("/api/v1/crm/engagement-dashboard").respond(200, json=SAMPLE_ENGAGEMENT)
    result = invoke(["crm", "engagement-dashboard", "--period", "7"])
    assert result.exit_code == 0
    url = str(route.calls.last.request.url)
    assert "period_days=7" in url or "period=7" in url


def test_engagement_dashboard_forbidden(invoke, mock_api):
    mock_api.get("/api/v1/crm/engagement-dashboard").respond(403, json={"detail": "denied"})
    result = invoke(["crm", "engagement-dashboard"])
    assert result.exit_code == 4


def test_engagement_dashboard_server_error_json(invoke, mock_api):
    mock_api.get("/api/v1/crm/engagement-dashboard").respond(500, json={"detail": "boom"})
    result = invoke(["crm", "engagement-dashboard", "--json"])
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert parsed["error"] is True


def test_engagement_dashboard_empty_dataset(invoke, mock_api):
    """Brand-new orgs: zero metrics shouldn't blow up rendering."""
    empty = {
        "period_days": 30,
        "emails_sent": {"current_period": 0, "previous_period": 0, "change": 0},
        "open_rate": 0.0,
        "click_rate": 0.0,
        "reply_rate": 0.0,
        "bounce_rate": 0.0,
        "email_health": {"score": None, "status": "unknown"},
        "top_clicked_links": [],
    }
    mock_api.get("/api/v1/crm/engagement-dashboard").respond(200, json=empty)
    result = invoke(["crm", "engagement-dashboard"])
    assert result.exit_code == 0
