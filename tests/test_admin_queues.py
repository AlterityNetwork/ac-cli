"""Tests for admin queues commands."""

import json


SAMPLE_HEALTH = {"status": "healthy", "queues": 5, "workers": 3}
SAMPLE_STATS = {"total_jobs": 1000, "completed": 950, "failed": 10, "pending": 40}
SAMPLE_FAILED = {"job_id": "j-1", "error": "Timeout", "failed_at": "2026-01-01T00:00:00Z"}


def test_queues_health(invoke, mock_api):
    mock_api.get("/api/v1/admin/queues/health").respond(200, json=SAMPLE_HEALTH)
    result = invoke(["admin", "queues", "health"])
    assert result.exit_code == 0
    assert "healthy" in result.output


def test_queues_health_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/queues/health").respond(200, json=SAMPLE_HEALTH)
    result = invoke(["admin", "--json", "queues", "health"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "healthy"


def test_queues_stats(invoke, mock_api):
    mock_api.get("/api/v1/admin/queues/stats").respond(200, json=SAMPLE_STATS)
    result = invoke(["admin", "queues", "stats"])
    assert result.exit_code == 0


def test_queues_stats_json(invoke, mock_api):
    mock_api.get("/api/v1/admin/queues/stats").respond(200, json=SAMPLE_STATS)
    result = invoke(["admin", "--json", "queues", "stats"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["total_jobs"] == 1000


def test_queues_queue_stats(invoke, mock_api):
    mock_api.get("/api/v1/admin/queues/default/stats").respond(200, json=SAMPLE_STATS)
    result = invoke(["admin", "queues", "queue-stats", "default"])
    assert result.exit_code == 0


def test_queues_metrics(invoke, mock_api):
    mock_api.get("/api/v1/admin/queues/metrics").respond(200, json={"metrics": []})
    result = invoke(["admin", "queues", "metrics"])
    assert result.exit_code == 0


def test_queues_send_to_sentry(invoke, mock_api):
    mock_api.post("/api/v1/admin/queues/metrics/send-to-sentry").respond(200, json={"status": "ok"})
    result = invoke(["admin", "queues", "send-to-sentry"])
    assert result.exit_code == 0
    assert "Metrics sent to Sentry" in result.output


def test_queues_job_performance(invoke, mock_api):
    mock_api.get("/api/v1/admin/queues/jobs/j-1/performance").respond(200, json={"duration_ms": 1500})
    result = invoke(["admin", "queues", "job-performance", "j-1"])
    assert result.exit_code == 0


def test_queues_failed(invoke, mock_api):
    mock_api.get("/api/v1/admin/queues/default/failed").respond(200, json=[SAMPLE_FAILED])
    result = invoke(["admin", "queues", "failed", "default"])
    assert result.exit_code == 0
    assert "Timeout" in result.output


def test_queues_retry_all(invoke, mock_api):
    mock_api.post("/api/v1/admin/queues/default/failed/retry").respond(200, json={"status": "ok"})
    result = invoke(["admin", "queues", "retry-all", "default", "--yes"])
    assert result.exit_code == 0
    assert "Retrying" in result.output


def test_queues_retry_job(invoke, mock_api):
    mock_api.post("/api/v1/admin/queues/jobs/j-1/retry").respond(200, json={"status": "ok"})
    result = invoke(["admin", "queues", "retry-job", "j-1"])
    assert result.exit_code == 0
    assert "Retrying" in result.output


def test_queues_clear_failed_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/admin/queues/default/failed").respond(204)
    result = invoke(["admin", "queues", "clear-failed", "default", "--yes"])
    assert result.exit_code == 0
    assert "Cleared" in result.output


def test_queues_clear_failed_aborted(invoke, mock_api):
    result = invoke(["admin", "queues", "clear-failed", "default"], input="n\n")
    assert result.exit_code == 1
