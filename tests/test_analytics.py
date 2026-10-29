"""Tests for analytics commands."""

import json

OVERVIEW = {
    "start_date": "2026-06-21",
    "end_date": "2026-07-21",
    "period_days": 30,
    "prospects_found": {"current": 42, "previous": 30, "change_pct": 40.0},
    "prospects_watched": {"current": 9, "previous": 6, "change_pct": 50.0},
    "prospects_watching_total": 14,
    "prospects_dismissed": {"current": 11, "previous": 8, "change_pct": 37.5},
    "signals_companies_added": {"current": 5, "previous": 3, "change_pct": 66.7},
    "signals_people_added": {"current": 7, "previous": 4, "change_pct": 75.0},
    "prospects_pursued": {"current": 6, "previous": 2, "change_pct": 200.0},
    "sequences_active": 4,
    "sequence_prospects_added": {"current": 50, "previous": 40, "change_pct": 25.0},
    "outbound_touches": {"current": 240, "previous": 180, "change_pct": 33.3},
    "replies": {"current": 12, "previous": 9, "change_pct": 33.3},
    "sequences_by_reply_rate": [
        {
            "id": "s1",
            "name": "Q4 founders",
            "status": "active",
            "prospects": 40,
            "replies": 5,
            "reply_rate": 12.5,
        }
    ],
    "sequences_processed_by_day": [],
    "outputs_by_type": [{"type": "Email", "count": 240}],
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
    assert "Prospects found" in result.output
    assert "Outbound touches" in result.output
    assert "42" in result.output
    assert "2026-06-21" in result.output
    assert "Live sequences: 4" in result.output
    assert "Watching now: 14" in result.output
    assert "Task completion rate: 70.6%" in result.output
    assert "Sequences by reply rate" in result.output
    assert "Q4 founders" in result.output
    assert "12.5%" in result.output
    assert "Sonar" not in result.output
    assert "Headhunter" not in result.output
    assert "Reply rate:" not in result.output


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


def test_analytics_overview_renders_null_change_without_crashing(invoke, mock_api):
    """The API sends change_pct: null when the previous period was zero.

    `.get("change_pct", 0.0)` returns None for a present-but-null key, and
    f"{None:+.1f}%" raises TypeError — so the whole command died on any org
    whose metric grew from nothing.
    """
    payload = dict(OVERVIEW)
    payload["prospects_found"] = {"current": 42, "previous": 0, "change_pct": None}

    mock_api.get("/api/v1/analytics/overview").respond(200, json=payload)
    result = invoke(["analytics", "overview"])

    assert result.exit_code == 0
    assert "Prospects found" in result.output
    # No fabricated percentage for an undefined comparison.
    assert "+100.0%" not in result.output


def test_analytics_overview_json_passes_null_change_through(invoke, mock_api):
    payload = dict(OVERVIEW)
    payload["prospects_found"] = {"current": 42, "previous": 0, "change_pct": None}

    mock_api.get("/api/v1/analytics/overview").respond(200, json=payload)
    result = invoke(["analytics", "overview", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output)["prospects_found"]["change_pct"] is None


def test_analytics_overview_with_no_sequences_prints_no_ranking(invoke, mock_api):
    payload = dict(OVERVIEW)
    payload["sequences_by_reply_rate"] = []

    mock_api.get("/api/v1/analytics/overview").respond(200, json=payload)
    result = invoke(["analytics", "overview"])

    assert result.exit_code == 0
    assert "Sequences by reply rate" not in result.output
