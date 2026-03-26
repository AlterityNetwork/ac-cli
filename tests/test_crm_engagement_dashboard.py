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
