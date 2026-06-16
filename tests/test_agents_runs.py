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


def _sse(*frames: tuple[str | None, str]) -> bytes:
    chunks: list[str] = []
    for event_id, payload in frames:
        if event_id:
            chunks.append(f"id: {event_id}\n")
        chunks.append(f"data: {payload}\n\n")
    return "".join(chunks).encode()


def test_runs_create_with_watch_streams_until_terminal(invoke, mock_api):
    payload = {"run_id": "run-1", "agent": "research_agent", "status": "queued"}
    mock_api.post("/api/v1/agents/runs").respond(202, json=payload)
    mock_api.get("/api/v1/agents/runs/run-1/events").respond(
        200,
        content=_sse(
            (
                "1-0",
                json.dumps(
                    {
                        "event_type": "agent.message",
                        "status": "running",
                        "data": {"type": "agent.message", "text": "hello"},
                    }
                ),
            ),
            (
                "2-0",
                json.dumps({"event_type": "run", "status": "completed", "data": {}}),
            ),
        ),
        headers={"content-type": "text/event-stream"},
    )

    result = invoke(["agents", "runs", "create", "--agent", "research_agent", "--watch"])

    assert result.exit_code == 0
    assert "Run created" in result.output
    assert "hello" in result.output
    assert "Run completed" in result.output


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


def test_runs_watch_completed(invoke, mock_api):
    mock_api.get("/api/v1/agents/runs/run-1/events").respond(
        200,
        content=_sse(
            (
                "1-0",
                json.dumps(
                    {
                        "event_type": "agent.message",
                        "status": "running",
                        "data": {"type": "agent.message", "text": "partial"},
                    }
                ),
            ),
            (
                "2-0",
                json.dumps({"event_type": "run", "status": "completed", "data": {}}),
            ),
        ),
        headers={"content-type": "text/event-stream"},
    )

    result = invoke(["agents", "runs", "watch", "run-1"])

    assert result.exit_code == 0
    assert "partial" in result.output
    assert "Run completed" in result.output


def test_runs_watch_failed_exits_nonzero(invoke, mock_api):
    mock_api.get("/api/v1/agents/runs/run-1/events").respond(
        200,
        content=_sse(
            (
                "9-0",
                json.dumps(
                    {
                        "event_type": "run",
                        "status": "failed",
                        "data": {"error": "model exploded"},
                    }
                ),
            )
        ),
        headers={"content-type": "text/event-stream"},
    )

    result = invoke(["agents", "runs", "watch", "run-1"])

    assert result.exit_code == 1
    assert "model exploded" in result.output


def test_runs_watch_skips_malformed_sse_frame(invoke, mock_api):
    mock_api.get("/api/v1/agents/runs/run-1/events").respond(
        200,
        content=(
            b"id: bad-0\n"
            b"data: {not-json\n\n"
            + _sse(
                (
                    "2-0",
                    json.dumps({"event_type": "run", "status": "completed", "data": {}}),
                )
            )
        ),
        headers={"content-type": "text/event-stream"},
    )

    result = invoke(["agents", "runs", "watch", "run-1"])

    assert result.exit_code == 0
    assert "Skipping malformed SSE frame" in result.output
    assert "Run completed" in result.output


def test_runs_watch_json_outputs_ndjson(invoke, mock_api):
    frame = {"event_type": "run", "status": "completed", "data": {}}
    mock_api.get("/api/v1/agents/runs/run-1/events").respond(
        200,
        content=_sse(("1-0", json.dumps(frame))),
        headers={"content-type": "text/event-stream"},
    )

    result = invoke(["agents", "runs", "watch", "run-1", "--json"])

    assert result.exit_code == 0
    assert [json.loads(line) for line in result.output.splitlines()] == [frame]


def _runs_page(*runs):
    """The standard paginated envelope GET /agents/runs returns."""
    items = list(runs)
    return {
        "data": items,
        "total": len(items),
        "limit": 50,
        "offset": 0,
        "has_more": False,
    }


def test_runs_list(invoke, mock_api):
    mock_api.get("/api/v1/agents/runs").respond(200, json=_runs_page(SAMPLE_RUN))
    result = invoke(["agents", "runs", "list"])
    assert result.exit_code == 0
    assert "run-1" in result.output


def test_runs_list_filters(invoke, mock_api):
    route = mock_api.get("/api/v1/agents/runs").respond(200, json=_runs_page(SAMPLE_RUN))
    result = invoke(
        ["agents", "runs", "list", "--agent", "research_agent", "--status", "completed"]
    )
    assert result.exit_code == 0
    params = route.calls[0].request.url.params
    assert params["agent"] == "research_agent"
    assert params["status"] == "completed"


def test_runs_list_json(invoke, mock_api):
    mock_api.get("/api/v1/agents/runs").respond(200, json=_runs_page(SAMPLE_RUN))
    result = invoke(["agents", "runs", "list", "--json"])
    assert result.exit_code == 0
    # --json mirrors the API: the full paginated envelope.
    assert json.loads(result.output)["data"][0]["run_id"] == "run-1"
