"""Tests for analytics commands."""

import json

OVERVIEW = {
    "start_date": "2026-06-21",
    "end_date": "2026-07-21",
    "period_days": 30,
    "sonar_companies": {"current": 42, "previous": 30, "change_pct": 40.0},
    "sonar_signals": {"current": 120, "previous": 100, "change_pct": 20.0},
    "sonar_searches": {"current": 5, "previous": 4, "change_pct": 25.0},
    "sonar_searches_scheduled": 2,
    "headhunter_people": {"current": 88, "previous": 70, "change_pct": 25.7},
    "headhunter_searches": {"current": 3, "previous": 3, "change_pct": 0.0},
    "headhunter_searches_scheduled": 1,
    "headhunter_people_with_email": 61,
    "sequences_launched": {"current": 6, "previous": 2, "change_pct": 200.0},
    "sequences_active": 4,
    "emails_sent": {"current": 240, "previous": 180, "change_pct": 33.3},
    "email_replies": {"current": 12, "previous": 9, "change_pct": 33.3},
    "reply_rate": 5.333333,
    "sequences_processed_by_day": [],
    "outputs_by_type": [{"type": "email", "count": 240}],
    "companies_new": {"current": 15, "previous": 10, "change_pct": 50.0},
    "companies_total": 300,
    "people": {"current": 40, "previous": 35, "change_pct": 14.3},
    "people_total": 900,
    "tasks_created": {"current": 20, "previous": 18, "change_pct": 11.1},
    "tasks_completed": {"current": 16, "previous": 12, "change_pct": 33.3},
    "tasks_created_completed": 14,
    "task_completion_rate": 70.588,
    "workflow_runs": {"current": 9, "previous": 7, "change_pct": 28.6},
    "logins": {"current": 55, "previous": 50, "change_pct": 10.0},
    "active_users": {"current": 4, "previous": 4, "change_pct": 0.0},
    "daily_activity": [],
}


def test_analytics_overview(invoke, mock_api):
    mock_api.get("/api/v1/analytics/overview").respond(200, json=OVERVIEW)
    result = invoke(["analytics", "overview"])
    assert result.exit_code == 0
    assert "Sonar companies" in result.output
    assert "42" in result.output
    assert "2026-06-21" in result.output
    assert "Reply rate: 5.3%" in result.output
    assert "Task completion rate: 70.6%" in result.output


def test_analytics_overview_period_days(invoke, mock_api):
    route = mock_api.get("/api/v1/analytics/overview").respond(200, json=OVERVIEW)
    result = invoke(["analytics", "overview", "--period-days", "7"])
    assert result.exit_code == 0
    assert route.calls.last.request.url.params["period_days"] == "7"


def test_analytics_overview_rejects_out_of_range_period_before_request(invoke, mock_api):
    result = invoke(["analytics", "overview", "--period-days", "366"])
    assert result.exit_code == 2
    assert not mock_api.calls


def test_analytics_overview_json(invoke, mock_api):
    mock_api.get("/api/v1/analytics/overview").respond(200, json=OVERVIEW)
    result = invoke(["analytics", "overview", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == OVERVIEW


def test_analytics_overview_error(invoke, mock_api):
    mock_api.get("/api/v1/analytics/overview").respond(500, json={"detail": "boom"})
    result = invoke(["analytics", "overview"])
    assert result.exit_code == 1


def test_analytics_overview_error_json(invoke, mock_api):
    mock_api.get("/api/v1/analytics/overview").respond(500, json={"detail": "boom"})
    result = invoke(["analytics", "overview", "--json"])
    assert result.exit_code == 1
    body = json.loads(result.output)
    assert body["error"] is True
    assert body["status_code"] == 500
    assert body["detail"] == "boom"
