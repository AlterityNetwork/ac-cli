"""Tests for customer-facing organization analytics commands."""

import json

SAMPLE_OVERVIEW = {
    "period_days": 30,
    "sonar_companies": {"current": 12, "previous": 8, "change_pct": 50.0},
    "sonar_signals": {"current": 7, "previous": 5, "change_pct": 40.0},
    "headhunter_people": {"current": 9, "previous": 6, "change_pct": 50.0},
    "emails_sent": {"current": 21, "previous": 15, "change_pct": 40.0},
    "companies_new": {"current": 4, "previous": 2, "change_pct": 100.0},
}


def test_overview(invoke, mock_api):
    route = mock_api.get("/api/v1/analytics/overview").respond(200, json=SAMPLE_OVERVIEW)

    result = invoke(["analytics", "overview", "--period-days", "30"])

    assert result.exit_code == 0
    assert route.calls.last.request.url.params["period_days"] == "30"
    assert "Organization Analytics" in result.output
    assert "Companies discovered: 12" in result.output


def test_overview_json(invoke, mock_api):
    mock_api.get("/api/v1/analytics/overview").respond(200, json=SAMPLE_OVERVIEW)

    result = invoke(["analytics", "overview", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output)["emails_sent"]["current"] == 21


def test_overview_rejects_out_of_range_period_before_request(invoke, mock_api):
    result = invoke(["analytics", "overview", "--period-days", "366"])

    assert result.exit_code == 2
    assert not mock_api.calls
