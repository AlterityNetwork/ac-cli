"""Tests for envoy playbooks commands."""

import json

from tests.conftest import WHOAMI_RESPONSE

SAMPLE_PLAYBOOK = {
    "id": "pb-1",
    "organization_id": "org-456",
    "name": "Competitor Battlecard",
    "description": "Playbook for competing against Acme Corp",
    "status": "active",
    "competitor_name": "Acme Corp",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def test_playbooks_list(invoke, mock_api):
    mock_api.get("/api/v1/playbooks").respond(200, json=[SAMPLE_PLAYBOOK])
    result = invoke(["envoy", "playbooks", "list"])
    assert result.exit_code == 0
    assert "Competitor Battlecard" in result.output


def test_playbooks_list_json(invoke, mock_api):
    mock_api.get("/api/v1/playbooks").respond(200, json=[SAMPLE_PLAYBOOK])
    result = invoke(["envoy", "playbooks", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["name"] == "Competitor Battlecard"


def test_playbooks_list_global_output_json(invoke, mock_api):
    mock_api.get("/api/v1/playbooks").respond(200, json=[SAMPLE_PLAYBOOK])
    result = invoke(["--output", "json", "envoy", "playbooks", "list"])
    assert result.exit_code == 0
    assert json.loads(result.output) == [
        {"id": "pb-1", "name": "Competitor Battlecard", "status": "active"}
    ]


def test_playbooks_get(invoke, mock_api):
    mock_api.get("/api/v1/playbooks/pb-1").respond(200, json=SAMPLE_PLAYBOOK)
    result = invoke(["envoy", "playbooks", "get", "pb-1"])
    assert result.exit_code == 0
    assert "Competitor Battlecard" in result.output


def test_playbooks_get_global_output_json(invoke, mock_api):
    mock_api.get("/api/v1/playbooks/pb-1").respond(200, json=SAMPLE_PLAYBOOK)
    result = invoke(["--output", "json", "envoy", "playbooks", "get", "pb-1"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "pb-1"
    assert parsed["name"] == "Competitor Battlecard"
    assert "organization_id" not in parsed


def test_playbooks_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/playbooks/pb-999").respond(404, json={"detail": "Not found"})
    result = invoke(["envoy", "playbooks", "get", "pb-999"])
    assert result.exit_code == 3


def test_playbooks_create(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/playbooks").respond(201, json=SAMPLE_PLAYBOOK)
    result = invoke(["envoy", "playbooks", "create", "--name", "Competitor Battlecard"])
    assert result.exit_code == 0
    assert "Created playbook" in result.output


def test_playbooks_create_json(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/playbooks").respond(201, json=SAMPLE_PLAYBOOK)
    result = invoke(["envoy", "playbooks", "create", "--name", "Competitor Battlecard", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["name"] == "Competitor Battlecard"


def test_playbooks_update(invoke, mock_api):
    updated = {**SAMPLE_PLAYBOOK, "name": "Updated Playbook"}
    mock_api.patch("/api/v1/playbooks/pb-1").respond(200, json=updated)
    result = invoke(["envoy", "playbooks", "update", "pb-1", "--name", "Updated Playbook"])
    assert result.exit_code == 0
    assert "Updated playbook" in result.output


def test_playbooks_update_no_fields(invoke, mock_api):
    result = invoke(["envoy", "playbooks", "update", "pb-1"])
    assert result.exit_code == 1


def test_playbooks_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/playbooks/pb-1").respond(204)
    result = invoke(["envoy", "playbooks", "delete", "pb-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_playbooks_delete_aborted(invoke, mock_api):
    result = invoke(["envoy", "playbooks", "delete", "pb-1"], input="n\n")
    assert result.exit_code == 1


def test_playbooks_duplicate(invoke, mock_api):
    duplicated = {**SAMPLE_PLAYBOOK, "id": "pb-2", "name": "Competitor Battlecard (Copy)"}
    mock_api.post("/api/v1/playbooks/pb-1/duplicate").respond(201, json=duplicated)
    result = invoke(["envoy", "playbooks", "duplicate", "pb-1"])
    assert result.exit_code == 0
    assert "Duplicated playbook" in result.output
