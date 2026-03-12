"""Tests for CRM dashboard command."""

import json


SAMPLE_DASHBOARD = {
    "period_days": 30,
    "generated_at": "2026-03-12T00:00:00Z",
    "pipeline": {
        "total_deals": 5,
        "total_value": 250000.00,
        "deals_by_stage": {
            "lead": {"count": 2, "value": 50000.0},
            "qualified": {"count": 3, "value": 200000.0},
        },
    },
    "active_pipeline": {
        "total_value": 250000.0,
        "adjusted_value": 125000.0,
        "active_deals_count": 5,
        "current_period_value": 100000.0,
        "previous_period_value": 80000.0,
    },
    "leads": {
        "current_period": 10,
        "previous_period": 8,
        "change": 2,
        "total": 50,
    },
    "messages_sent": {
        "current_period": 25,
        "previous_period": 20,
        "change": 5,
    },
    "recent": {
        "activities": [],
        "upcoming_tasks": [],
        "communications": [],
        "recent_leads": [],
    },
}


def test_dashboard(invoke, mock_api):
    mock_api.get("/api/v1/crm/dashboard").respond(200, json=SAMPLE_DASHBOARD)
    result = invoke(["crm", "dashboard"])
    assert result.exit_code == 0
    assert "Pipeline" in result.output
    assert "250,000" in result.output
    assert "Leads" in result.output


def test_dashboard_json(invoke, mock_api):
    mock_api.get("/api/v1/crm/dashboard").respond(200, json=SAMPLE_DASHBOARD)
    result = invoke(["crm", "--json", "dashboard"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["pipeline"]["total_deals"] == 5


def test_dashboard_custom_period(invoke, mock_api):
    mock_api.get("/api/v1/crm/dashboard").respond(200, json=SAMPLE_DASHBOARD)
    result = invoke(["crm", "dashboard", "--period", "90"])
    assert result.exit_code == 0


def test_dashboard_api_error(invoke, mock_api):
    mock_api.get("/api/v1/crm/dashboard").respond(500, json={"detail": "Internal error"})
    result = invoke(["crm", "dashboard"])
    assert result.exit_code == 1
    assert "500" in result.output
