"""Tests for envoy inbox-count command."""

import json


def test_inbox_count_happy(invoke, mock_api):
    """inbox-count displays the count."""
    mock_api.get("/api/v1/envoy/dashboard/inbox-count").respond(200, json={"count": 42})
    result = invoke(["envoy", "inbox-count"])
    assert result.exit_code == 0
    assert "42" in result.output


def test_inbox_count_json(invoke, mock_api):
    """inbox-count --json outputs raw JSON."""
    mock_api.get("/api/v1/envoy/dashboard/inbox-count").respond(200, json={"count": 7})
    result = invoke(["envoy", "inbox-count", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["count"] == 7


def test_inbox_count_404(invoke, mock_api):
    """inbox-count exits 3 on 404."""
    mock_api.get("/api/v1/envoy/dashboard/inbox-count").respond(404, json={"detail": "Not found"})
    result = invoke(["envoy", "inbox-count"])
    assert result.exit_code == 3


def test_inbox_count_403(invoke, mock_api):
    """inbox-count exits 4 on 403."""
    mock_api.get("/api/v1/envoy/dashboard/inbox-count").respond(403, json={"detail": "Forbidden"})
    result = invoke(["envoy", "inbox-count"])
    assert result.exit_code == 4


def test_inbox_count_json_error(invoke, mock_api):
    """inbox-count --json returns structured error on failure."""
    mock_api.get("/api/v1/envoy/dashboard/inbox-count").respond(404, json={"detail": "Not found"})
    result = invoke(["envoy", "inbox-count", "--json"])
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 404
