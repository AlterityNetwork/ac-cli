"""Tests for envoy steps commands."""

import json


SAMPLE_STEP = {
    "id": "step-1",
    "sequence_id": "seq-1",
    "step_type": "message",
    "step_order": 1,
    "message_template": "Hi {{name}}",
    "prompt": None,
    "delay_value": None,
    "delay_unit": None,
}


def test_steps_create(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/steps").respond(201, json=SAMPLE_STEP)
    result = invoke(["envoy", "steps", "create", "seq-1", "--type", "message", "--message-template", "Hi {{name}}"])
    assert result.exit_code == 0
    assert "Created step" in result.output


def test_steps_create_json(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/steps").respond(201, json=SAMPLE_STEP)
    result = invoke(["envoy", "steps", "create", "seq-1", "--type", "message", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["step_type"] == "message"


def test_steps_update(invoke, mock_api):
    updated = {**SAMPLE_STEP, "message_template": "Hello {{name}}"}
    mock_api.patch("/api/v1/envoy/sequences/seq-1/steps/step-1").respond(200, json=updated)
    result = invoke(["envoy", "steps", "update", "seq-1", "step-1", "--message-template", "Hello {{name}}"])
    assert result.exit_code == 0
    assert "Updated step" in result.output


def test_steps_update_no_fields(invoke, mock_api):
    result = invoke(["envoy", "steps", "update", "seq-1", "step-1"])
    assert result.exit_code == 1


def test_steps_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/envoy/sequences/seq-1/steps/step-1").respond(204)
    result = invoke(["envoy", "steps", "delete", "seq-1", "step-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_steps_delete_aborted(invoke, mock_api):
    result = invoke(["envoy", "steps", "delete", "seq-1", "step-1"], input="n\n")
    assert result.exit_code == 1


def test_steps_reorder(invoke, mock_api):
    mock_api.put("/api/v1/envoy/sequences/seq-1/steps/reorder").respond(200, json={"reordered": True})
    result = invoke(["envoy", "steps", "reorder", "seq-1", "--step-ids", "step-2,step-1,step-3"])
    assert result.exit_code == 0
    assert "Reordered 3 steps" in result.output


def test_steps_reorder_json(invoke, mock_api):
    mock_api.put("/api/v1/envoy/sequences/seq-1/steps/reorder").respond(200, json={"reordered": True})
    result = invoke(["envoy", "steps", "reorder", "seq-1", "--step-ids", "step-2,step-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["reordered"] is True


def test_steps_stats(invoke, mock_api):
    stats = [
        {"step_order": 1, "step_type": "message", "total": 50, "sent": 48, "replied": 12, "bounced": 2},
        {"step_order": 2, "step_type": "message", "total": 40, "sent": 38, "replied": 8, "bounced": 2},
    ]
    mock_api.get("/api/v1/envoy/sequences/seq-1/step-stats").respond(200, json=stats)
    result = invoke(["envoy", "steps", "stats", "seq-1"])
    assert result.exit_code == 0
    assert "Step Statistics" in result.output


def test_steps_stats_json(invoke, mock_api):
    stats = [{"step_order": 1, "step_type": "message", "total": 50, "sent": 48, "replied": 12, "bounced": 2}]
    mock_api.get("/api/v1/envoy/sequences/seq-1/step-stats").respond(200, json=stats)
    result = invoke(["envoy", "steps", "stats", "seq-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["total"] == 50


def test_steps_stats_empty(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences/seq-1/step-stats").respond(200, json=[])
    result = invoke(["envoy", "steps", "stats", "seq-1"])
    assert result.exit_code == 0
    assert "No step statistics" in result.output
