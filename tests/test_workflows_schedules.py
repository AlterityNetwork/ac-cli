"""Tests for workflow schedules commands."""

import json

SAMPLE_SCHEDULE = {
    "id": "sched-1",
    "workflow_id": "wf-1",
    "cron_expression": "0 9 * * 1-5",
    "timezone": "America/New_York",
    "enabled": True,
    "next_run_at": "2026-01-06T09:00:00Z",
    "created_at": "2026-01-01T00:00:00Z",
}


def test_schedules_list(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/schedules").respond(200, json=[SAMPLE_SCHEDULE])
    result = invoke(["workflows", "schedules", "list", "wf-1"])
    assert result.exit_code == 0
    assert "sched-1" in result.output


def test_schedules_list_json(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/schedules").respond(200, json=[SAMPLE_SCHEDULE])
    result = invoke(["workflows", "schedules", "list", "wf-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["id"] == "sched-1"


def test_schedules_get(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/schedule").respond(200, json=SAMPLE_SCHEDULE)
    result = invoke(["workflows", "schedules", "get", "wf-1"])
    assert result.exit_code == 0
    assert "0 9 * * 1-5" in result.output


def test_schedules_create(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/schedule").respond(201, json=SAMPLE_SCHEDULE)
    result = invoke(["workflows", "schedules", "create", "wf-1", "--cron", "0 9 * * 1-5"])
    assert result.exit_code == 0
    assert "Schedule created" in result.output


def test_schedules_create_json(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/schedule").respond(201, json=SAMPLE_SCHEDULE)
    result = invoke(["workflows", "schedules", "create", "wf-1", "--cron", "0 9 * * 1-5", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "sched-1"


def test_schedules_update(invoke, mock_api):
    updated = {**SAMPLE_SCHEDULE, "timezone": "UTC"}
    mock_api.patch("/api/v1/workflows/wf-1/schedules/sched-1").respond(200, json=updated)
    result = invoke(["workflows", "schedules", "update", "wf-1", "sched-1", "--timezone", "UTC"])
    assert result.exit_code == 0
    assert "Updated schedule" in result.output


def test_schedules_update_no_fields(invoke, mock_api):
    result = invoke(["workflows", "schedules", "update", "wf-1", "sched-1"])
    assert result.exit_code == 1


def test_schedules_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/workflows/wf-1/schedules/sched-1").respond(204)
    result = invoke(["workflows", "schedules", "delete", "wf-1", "sched-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_schedules_delete_aborted(invoke, mock_api):
    result = invoke(["workflows", "schedules", "delete", "wf-1", "sched-1"], input="n\n")
    assert result.exit_code == 1


def test_schedules_preview(invoke, mock_api):
    preview_data = {
        "next_runs": ["2026-01-06T09:00:00Z", "2026-01-07T09:00:00Z", "2026-01-08T09:00:00Z"]
    }
    mock_api.post("/api/v1/workflows/wf-1/schedule/preview").respond(200, json=preview_data)
    result = invoke(["workflows", "schedules", "preview", "wf-1", "--cron", "0 9 * * 1-5"])
    assert result.exit_code == 0
    assert "2026-01-06T09:00:00Z" in result.output


def test_schedules_toggle_enable(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/schedules/sched-1/toggle").respond(
        200, json={"enabled": True}
    )
    result = invoke(["workflows", "schedules", "toggle", "wf-1", "sched-1", "--enabled"])
    assert result.exit_code == 0
    assert "enabled" in result.output


def test_schedules_toggle_disable(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/schedules/sched-1/toggle").respond(
        200, json={"enabled": False}
    )
    result = invoke(["workflows", "schedules", "toggle", "wf-1", "sched-1", "--disabled"])
    assert result.exit_code == 0
    assert "disabled" in result.output


def test_schedules_create_sends_cron_type_and_input_config(invoke, mock_api):
    route = mock_api.post("/api/v1/workflows/wf-1/schedule").respond(201, json=SAMPLE_SCHEDULE)
    result = invoke(
        ["workflows", "schedules", "create", "wf-1", "--cron", "0 9 * * 1-5"]
        + ["--timezone", "Europe/London", "--input", '{"list_id": "l-1"}']
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "type": "cron",
        "cron_expression": "0 9 * * 1-5",
        "timezone": "Europe/London",
        "input_config": {"list_id": "l-1"},
    }


def test_schedules_update_sends_input_config(invoke, mock_api):
    route = mock_api.patch("/api/v1/workflows/wf-1/schedules/sched-1").respond(
        200, json=SAMPLE_SCHEDULE
    )
    result = invoke(
        ["workflows", "schedules", "update", "wf-1", "sched-1", "--input", '{"list_id": "l-2"}']
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body == {"input_config": {"list_id": "l-2"}}


def test_schedules_preview_caps_runs_on_the_client(invoke, mock_api):
    route = mock_api.post("/api/v1/workflows/wf-1/schedule/preview").respond(
        200,
        json={
            "next_runs": [
                "2026-01-06T09:00:00Z",
                "2026-01-07T09:00:00Z",
                "2026-01-08T09:00:00Z",
            ]
        },
    )
    result = invoke(
        ["workflows", "schedules", "preview", "wf-1", "--cron", "0 9 * * 1-5", "--count", "2"]
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert body == {"cron_expression": "0 9 * * 1-5", "timezone": "UTC"}
    assert "2026-01-07T09:00:00Z" in result.output
    assert "2026-01-08T09:00:00Z" not in result.output


def test_schedules_toggle_sends_is_active(invoke, mock_api):
    route = mock_api.post("/api/v1/workflows/wf-1/schedules/sched-1/toggle").respond(
        200, json=SAMPLE_SCHEDULE
    )
    assert (
        invoke(["workflows", "schedules", "toggle", "wf-1", "sched-1", "--enabled"]).exit_code == 0
    )
    assert json.loads(route.calls.last.request.content) == {"is_active": True}
    assert (
        invoke(["workflows", "schedules", "toggle", "wf-1", "sched-1", "--disabled"]).exit_code == 0
    )
    assert json.loads(route.calls.last.request.content) == {"is_active": False}


def test_schedules_preview_caps_runs_in_json_mode(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/schedule/preview").respond(
        200,
        json={
            "next_runs": ["2026-01-06T09:00:00Z", "2026-01-07T09:00:00Z"],
            "description": "At 09:00 on weekdays",
        },
    )
    result = invoke(
        ["workflows", "schedules", "preview", "wf-1", "--cron", "0 9 * * 1-5"]
        + ["--count", "1", "--json"]
    )
    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "next_runs": ["2026-01-06T09:00:00Z"],
        "description": "At 09:00 on weekdays",
    }
