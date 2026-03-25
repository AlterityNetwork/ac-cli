"""Tests for envoy sequences commands."""

import json

from tests.conftest import WHOAMI_RESPONSE


SAMPLE_SEQUENCE = {
    "id": "seq-1",
    "organization_id": "org-456",
    "name": "Q1 Outreach",
    "description": "Outreach to target companies",
    "status": "draft",
    "execution_mode": "manual",
    "writing_style_id": None,
    "playbook_id": None,
    "crm_list_id": "l1",
    "steps": [],
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def test_sequences_list(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences").respond(200, json=[SAMPLE_SEQUENCE])
    result = invoke(["envoy", "sequences", "list"])
    assert result.exit_code == 0
    assert "Q1 Outreach" in result.output


def test_sequences_list_json(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences").respond(200, json=[SAMPLE_SEQUENCE])
    result = invoke(["envoy", "sequences", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["name"] == "Q1 Outreach"


def test_sequences_list_with_status(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences").respond(200, json=[])
    result = invoke(["envoy", "sequences", "list", "--status", "active"])
    assert result.exit_code == 0


def test_sequences_get(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences/seq-1").respond(200, json=SAMPLE_SEQUENCE)
    result = invoke(["envoy", "sequences", "get", "seq-1"])
    assert result.exit_code == 0
    assert "Q1 Outreach" in result.output


def test_sequences_get_json(invoke, mock_api):
    mock_api.get("/api/v1/envoy/sequences/seq-1").respond(200, json=SAMPLE_SEQUENCE)
    result = invoke(["envoy", "sequences", "get", "seq-1", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "seq-1"


def test_sequences_create(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/envoy/sequences").respond(201, json=SAMPLE_SEQUENCE)
    result = invoke(["envoy", "sequences", "create", "--name", "Q1 Outreach"])
    assert result.exit_code == 0
    assert "Created sequence" in result.output


def test_sequences_create_json(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/envoy/sequences").respond(201, json=SAMPLE_SEQUENCE)
    result = invoke(["envoy", "sequences", "create", "--name", "Q1 Outreach", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["name"] == "Q1 Outreach"


def test_sequences_update(invoke, mock_api):
    updated = {**SAMPLE_SEQUENCE, "name": "Updated Sequence"}
    mock_api.patch("/api/v1/envoy/sequences/seq-1").respond(200, json=updated)
    result = invoke(["envoy", "sequences", "update", "seq-1", "--name", "Updated Sequence"])
    assert result.exit_code == 0
    assert "Updated sequence" in result.output


def test_sequences_update_no_fields(invoke, mock_api):
    result = invoke(["envoy", "sequences", "update", "seq-1"])
    assert result.exit_code == 1


def test_sequences_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/envoy/sequences/seq-1").respond(204)
    result = invoke(["envoy", "sequences", "delete", "seq-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_sequences_delete_aborted(invoke, mock_api):
    result = invoke(["envoy", "sequences", "delete", "seq-1"], input="n\n")
    assert result.exit_code == 1


def test_sequences_launch(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/launch").respond(200, json={"status": "active"})
    result = invoke(["envoy", "sequences", "launch", "seq-1", "--workflow-id", "wf-1"])
    assert result.exit_code == 0
    assert "Launched" in result.output


def test_sequences_pause(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/pause").respond(200, json={"status": "paused"})
    result = invoke(["envoy", "sequences", "pause", "seq-1"])
    assert result.exit_code == 0
    assert "Paused" in result.output


def test_sequences_resume(invoke, mock_api):
    mock_api.post("/api/v1/envoy/sequences/seq-1/resume").respond(200, json={"status": "active"})
    result = invoke(["envoy", "sequences", "resume", "seq-1", "--workflow-id", "wf-1"])
    assert result.exit_code == 0
    assert "Resumed" in result.output
