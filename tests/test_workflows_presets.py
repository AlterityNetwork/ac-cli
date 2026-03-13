"""Tests for workflow presets commands."""

import json


SAMPLE_PRESET = {
    "id": "pre-1",
    "workflow_id": "wf-1",
    "name": "Default Config",
    "description": "Standard settings",
    "config": {"key": "value"},
    "created_at": "2026-01-01T00:00:00Z",
}


def test_presets_list(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/presets").respond(200, json=[SAMPLE_PRESET])
    result = invoke(["workflows", "presets", "list", "wf-1"])
    assert result.exit_code == 0
    assert "Default Config" in result.output


def test_presets_list_json(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/presets").respond(200, json=[SAMPLE_PRESET])
    result = invoke(["workflows", "--json", "presets", "list", "wf-1"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["name"] == "Default Config"


def test_presets_get(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/presets/pre-1").respond(200, json=SAMPLE_PRESET)
    result = invoke(["workflows", "presets", "get", "wf-1", "pre-1"])
    assert result.exit_code == 0
    assert "Default Config" in result.output


def test_presets_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/workflows/wf-1/presets/pre-999").respond(404, json={"detail": "Not found"})
    result = invoke(["workflows", "presets", "get", "wf-1", "pre-999"])
    assert result.exit_code == 1


def test_presets_create(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/presets").respond(201, json=SAMPLE_PRESET)
    result = invoke(["workflows", "presets", "create", "wf-1", "--name", "Default Config"])
    assert result.exit_code == 0
    assert "Created preset" in result.output


def test_presets_create_json(invoke, mock_api):
    mock_api.post("/api/v1/workflows/wf-1/presets").respond(201, json=SAMPLE_PRESET)
    result = invoke(["workflows", "--json", "presets", "create", "wf-1", "--name", "Default Config"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["name"] == "Default Config"


def test_presets_update(invoke, mock_api):
    updated = {**SAMPLE_PRESET, "name": "Updated Config"}
    mock_api.patch("/api/v1/workflows/wf-1/presets/pre-1").respond(200, json=updated)
    result = invoke(["workflows", "presets", "update", "wf-1", "pre-1", "--name", "Updated Config"])
    assert result.exit_code == 0
    assert "Updated preset" in result.output


def test_presets_update_no_fields(invoke, mock_api):
    result = invoke(["workflows", "presets", "update", "wf-1", "pre-1"])
    assert result.exit_code == 1


def test_presets_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/workflows/wf-1/presets/pre-1").respond(204)
    result = invoke(["workflows", "presets", "delete", "wf-1", "pre-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_presets_delete_aborted(invoke, mock_api):
    result = invoke(["workflows", "presets", "delete", "wf-1", "pre-1"], input="n\n")
    assert result.exit_code == 1
