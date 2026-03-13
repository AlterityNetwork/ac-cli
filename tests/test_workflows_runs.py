"""Tests for workflow runs commands."""

import json


SAMPLE_RUN = {
    "id": "run-1",
    "workflow_id": "wf-1",
    "status": "completed",
    "started_at": "2026-01-01T00:00:00Z",
    "completed_at": "2026-01-01T00:01:00Z",
    "error": None,
}

SAMPLE_LOG = {
    "timestamp": "2026-01-01T00:00:30Z",
    "level": "info",
    "message": "Processing step 1",
}


def test_runs_create(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/runs").respond(202, json={"run_id": "run-1", "status": "accepted"})
    result = invoke(["workflows", "runs", "create", "wf-1"])
    assert result.exit_code == 0
    assert "Run created" in result.output
    assert "run-1" in result.output


def test_runs_create_json(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/runs").respond(202, json={"run_id": "run-1", "status": "accepted"})
    result = invoke(["workflows", "--json", "runs", "create", "wf-1"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["run_id"] == "run-1"


def test_runs_create_with_input(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/runs").respond(202, json={"run_id": "run-1", "status": "accepted"})
    result = invoke(["workflows", "runs", "create", "wf-1", "--input", '{"key": "value"}'])
    assert result.exit_code == 0
    assert "Run created" in result.output


def test_runs_create_with_idempotency_key(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/runs").respond(202, json={"run_id": "run-1", "status": "accepted"})
    result = invoke(["workflows", "runs", "create", "wf-1", "--idempotency-key", "key-123"])
    assert result.exit_code == 0
    assert "Run created" in result.output


def test_runs_list(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs").respond(200, json={"data": [SAMPLE_RUN], "total": 1})
    result = invoke(["workflows", "runs", "list", "wf-1"])
    assert result.exit_code == 0
    assert "run-1" in result.output


def test_runs_list_json(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs").respond(200, json={"data": [SAMPLE_RUN], "total": 1})
    result = invoke(["workflows", "--json", "runs", "list", "wf-1"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["id"] == "run-1"


def test_runs_get(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/run-1").respond(200, json=SAMPLE_RUN)
    result = invoke(["workflows", "runs", "get", "wf-1", "run-1"])
    assert result.exit_code == 0
    assert "run-1" in result.output


def test_runs_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/run-999").respond(404, json={"detail": "Not found"})
    result = invoke(["workflows", "runs", "get", "wf-1", "run-999"])
    assert result.exit_code == 1


def test_runs_logs(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/run-1/logs").respond(200, json=[SAMPLE_LOG])
    result = invoke(["workflows", "runs", "logs", "wf-1", "run-1"])
    assert result.exit_code == 0
    assert "Processing step 1" in result.output


def test_runs_logs_json(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/run-1/logs").respond(200, json=[SAMPLE_LOG])
    result = invoke(["workflows", "--json", "runs", "logs", "wf-1", "run-1"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["level"] == "info"
