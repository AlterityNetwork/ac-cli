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
    route = mock_api.post("/api/v1/workflows/wf-1/runs").respond(
        202, json={"workflow_run_id": "run-1", "status": "queued"}
    )
    result = invoke(["workflows", "runs", "create", "wf-1"])
    assert result.exit_code == 0
    assert "Run created" in result.output
    assert "run-1" in result.output
    # Verify empty trigger_data is sent by default
    body = json.loads(route.calls[0].request.content)
    assert body["trigger_data"] == {}


def test_runs_create_json(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/runs").respond(
        202, json={"workflow_run_id": "run-1", "status": "queued"}
    )
    result = invoke(["workflows", "runs", "create", "wf-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["workflow_run_id"] == "run-1"


def test_runs_create_with_input(invoke, mock_api):
    route = mock_api.post("/api/v1/workflows/wf-1/runs").respond(
        202, json={"workflow_run_id": "run-1", "status": "queued"}
    )
    result = invoke(["workflows", "runs", "create", "wf-1", "--input", '{"key": "value"}'])
    assert result.exit_code == 0
    assert "Run created" in result.output
    # Verify trigger_data contains the input
    body = json.loads(route.calls[0].request.content)
    assert body["trigger_data"] == {"key": "value"}


def test_runs_create_with_idempotency_key(invoke, mock_api):
    route = mock_api.post("/api/v1/workflows/wf-1/runs").respond(
        202, json={"workflow_run_id": "run-1", "status": "queued"}
    )
    result = invoke(["workflows", "runs", "create", "wf-1", "--idempotency-key", "key-123"])
    assert result.exit_code == 0
    assert "Run created" in result.output
    # Verify idempotency header was sent
    assert route.calls[0].request.headers.get("Idempotency-Key") == "key-123"


def test_runs_create_invalid_input_json(invoke, mock_api):
    result = invoke(["workflows", "runs", "create", "wf-1", "--input", "not-json"])
    assert result.exit_code == 1


def test_runs_list(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs").respond(
        200, json={"data": [SAMPLE_RUN], "total": 1}
    )
    result = invoke(["workflows", "runs", "list", "wf-1"])
    assert result.exit_code == 0
    assert "run-1" in result.output


def test_runs_list_json(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs").respond(
        200, json={"data": [SAMPLE_RUN], "total": 1}
    )
    result = invoke(["workflows", "runs", "list", "wf-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["id"] == "run-1"


def test_runs_list_include_archived(invoke, mock_api):
    route = mock_api.get("/api/v1/workflows/wf-1/runs").respond(
        200, json={"data": [SAMPLE_RUN], "total": 1}
    )
    result = invoke(["workflows", "runs", "list", "wf-1", "--include-archived"])
    assert result.exit_code == 0
    assert route.calls[0].request.url.params["include_archived"] == "true"


def test_runs_archive(invoke, mock_api):
    route = mock_api.post("/api/v1/workflows/wf-1/runs/archive").respond(
        200, json={"archived_count": 2}
    )
    result = invoke(["workflows", "runs", "archive", "wf-1", "run-1", "run-2", "--yes"])
    assert result.exit_code == 0
    assert "Archived 2 runs" in result.output
    assert json.loads(route.calls[0].request.content) == {
        "run_ids": ["run-1", "run-2"]
    }


def test_runs_archive_json(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/runs/archive").respond(
        200, json={"archived_count": 1}
    )
    result = invoke(["workflows", "runs", "archive", "wf-1", "run-1", "--yes", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["archived_count"] == 1


def test_runs_archive_aborted(invoke, mock_api):
    result = invoke(["workflows", "runs", "archive", "wf-1", "run-1"], input="n\n")
    assert result.exit_code == 1
    assert not mock_api.calls


def test_runs_archive_in_flight_error(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/runs/archive").respond(
        422, json={"detail": "In-flight runs cannot be archived"}
    )
    result = invoke(["workflows", "runs", "archive", "wf-1", "run-1", "--yes", "--json"])
    assert result.exit_code == 2
    parsed = json.loads(result.output)
    assert parsed["status_code"] == 422
    assert "In-flight" in parsed["detail"]


def test_runs_restore(invoke, mock_api):
    route = mock_api.post("/api/v1/workflows/wf-1/runs/restore").respond(
        200, json={"restored_count": 1}
    )
    result = invoke(["workflows", "runs", "restore", "wf-1", "run-1", "--yes"])
    assert result.exit_code == 0
    assert "Restored 1 run" in result.output
    assert json.loads(route.calls[0].request.content) == {"run_ids": ["run-1"]}


def test_runs_restore_json(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/runs/restore").respond(
        200, json={"restored_count": 1}
    )
    result = invoke(["workflows", "runs", "restore", "wf-1", "run-1", "--yes", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["restored_count"] == 1


def test_runs_restore_aborted(invoke, mock_api):
    result = invoke(["workflows", "runs", "restore", "wf-1", "run-1"], input="n\n")
    assert result.exit_code == 1
    assert not mock_api.calls


def test_runs_restore_error(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/runs/restore").respond(
        422, json={"detail": "Invalid run id"}
    )
    result = invoke(["workflows", "runs", "restore", "wf-1", "run-1", "--yes", "--json"])
    assert result.exit_code == 2
    parsed = json.loads(result.output)
    assert parsed["status_code"] == 422
    assert parsed["detail"] == "Invalid run id"


def test_runs_get(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/run-1").respond(200, json=SAMPLE_RUN)
    result = invoke(["workflows", "runs", "get", "wf-1", "run-1"])
    assert result.exit_code == 0
    assert "run-1" in result.output


def test_runs_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/run-999").respond(404, json={"detail": "Not found"})
    result = invoke(["workflows", "runs", "get", "wf-1", "run-999"])
    assert result.exit_code == 3


def test_runs_logs(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/run-1/logs").respond(200, json=[SAMPLE_LOG])
    result = invoke(["workflows", "runs", "logs", "wf-1", "run-1"])
    assert result.exit_code == 0
    assert "Processing step 1" in result.output


def test_runs_logs_json(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/runs/run-1/logs").respond(200, json=[SAMPLE_LOG])
    result = invoke(["workflows", "runs", "logs", "wf-1", "run-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["level"] == "info"
