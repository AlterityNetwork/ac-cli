"""Tests for envoy dashboard command."""

import json


SAMPLE_DASHBOARD = {
    "reply_rate": 0.24,
    "emails_sent": 150,
    "meetings_booked": 8,
    "active_sessions": 3,
    "ready_for_review": 12,
}


def test_envoy_dashboard(invoke, mock_api):
    mock_api.get("/api/v1/envoy/dashboard/stats").respond(200, json=SAMPLE_DASHBOARD)
    result = invoke(["envoy", "dashboard"])
    assert result.exit_code == 0
    assert "Envoy Dashboard" in result.output
    assert "150" in result.output
    assert "24" in result.output  # reply rate percentage


def test_envoy_dashboard_json(invoke, mock_api):
    mock_api.get("/api/v1/envoy/dashboard/stats").respond(200, json=SAMPLE_DASHBOARD)
    result = invoke(["envoy", "dashboard", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["emails_sent"] == 150
    assert parsed["reply_rate"] == 0.24


def test_envoy_dashboard_forbidden(invoke, mock_api):
    mock_api.get("/api/v1/envoy/dashboard/stats").respond(403, json={"detail": "no"})
    result = invoke(["envoy", "dashboard"])
    assert result.exit_code == 4


def test_envoy_dashboard_server_error_json(invoke, mock_api):
    mock_api.get("/api/v1/envoy/dashboard/stats").respond(500, json={"detail": "boom"})
    result = invoke(["envoy", "dashboard", "--json"])
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 500


def test_envoy_inbox_count(invoke, mock_api):
    mock_api.get("/api/v1/envoy/dashboard/inbox-count").respond(
        200, json={"count": 7}
    )
    result = invoke(["envoy", "inbox-count"])
    assert result.exit_code == 0
    assert "7" in result.output


def test_envoy_inbox_count_json(invoke, mock_api):
    mock_api.get("/api/v1/envoy/dashboard/inbox-count").respond(
        200, json={"count": 0}
    )
    result = invoke(["envoy", "inbox-count", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["count"] == 0
