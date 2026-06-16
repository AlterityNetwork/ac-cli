"""Tests for managed agents runs commands."""

import json

SAMPLE_RUN = {
    "run_id": "run-1",
    "agent": "research_agent",
    "status": "completed",
    "input": {"query": "hello"},
    "output": {"result": "done"},
    "error": None,
    "usage": {"input_tokens": 10, "output_tokens": 20, "cost_usd": 0.001},
    "created_at": "2026-01-01T00:00:00Z",
    "started_at": "2026-01-01T00:00:01Z",
    "finished_at": "2026-01-01T00:00:05Z",
}


def test_runs_create(invoke, mock_api):
    route = mock_api.post("/api/v1/agents/runs").respond(
        202,
        json={"run_id": "run-1", "agent": "research_agent", "status": "queued"},
    )
    result = invoke(
        ["agents", "runs", "create", "--agent", "research_agent", "--input", '{"query": "hello"}']
    )
    assert result.exit_code == 0
    assert "run-1" in result.output
    body = json.loads(route.calls[0].request.content)
    assert body == {"agent": "research_agent", "input": {"query": "hello"}}


def test_runs_create_default_input(invoke, mock_api):
    route = mock_api.post("/api/v1/agents/runs").respond(
        202,
        json={"run_id": "run-2", "agent": "research_agent", "status": "queued"},
    )
    result = invoke(["agents", "runs", "create", "--agent", "research_agent"])
    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert body == {"agent": "research_agent", "input": {}}


def test_runs_create_invalid_input(invoke, mock_api):
    result = invoke(["agents", "runs", "create", "--agent", "research_agent", "--input", "{bad"])
    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


def test_runs_create_json(invoke, mock_api):
    payload = {"run_id": "run-1", "agent": "research_agent", "status": "queued"}
    mock_api.post("/api/v1/agents/runs").respond(202, json=payload)
    result = invoke(["agents", "runs", "create", "--agent", "research_agent", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["run_id"] == "run-1"


def test_runs_create_unknown_agent(invoke, mock_api):
    mock_api.post("/api/v1/agents/runs").respond(404, json={"detail": "Unknown agent"})
    result = invoke(["agents", "runs", "create", "--agent", "nope"])
    assert result.exit_code == 3
    assert "404" in result.output


def test_runs_get(invoke, mock_api):
    mock_api.get("/api/v1/agents/runs/run-1").respond(200, json=SAMPLE_RUN)
    result = invoke(["agents", "runs", "get", "run-1"])
    assert result.exit_code == 0
    assert "research_agent" in result.output


def test_runs_get_json(invoke, mock_api):
    mock_api.get("/api/v1/agents/runs/run-1").respond(200, json=SAMPLE_RUN)
    result = invoke(["agents", "runs", "get", "run-1", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["run_id"] == "run-1"


def test_runs_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/agents/runs/bad").respond(404, json={"detail": "Not found"})
    result = invoke(["agents", "runs", "get", "bad"])
    assert result.exit_code == 3
    assert "404" in result.output


def test_runs_list(invoke, mock_api):
    mock_api.get("/api/v1/agents/runs").respond(200, json=[SAMPLE_RUN])
    result = invoke(["agents", "runs", "list"])
    assert result.exit_code == 0
    assert "run-1" in result.output


def test_runs_list_filters(invoke, mock_api):
    route = mock_api.get("/api/v1/agents/runs").respond(200, json=[SAMPLE_RUN])
    result = invoke(
        ["agents", "runs", "list", "--agent", "research_agent", "--status", "completed"]
    )
    assert result.exit_code == 0
    params = route.calls[0].request.url.params
    assert params["agent"] == "research_agent"
    assert params["status"] == "completed"


def test_runs_list_json(invoke, mock_api):
    mock_api.get("/api/v1/agents/runs").respond(200, json=[SAMPLE_RUN])
    result = invoke(["agents", "runs", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)[0]["run_id"] == "run-1"
