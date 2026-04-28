"""Tests for envoy battlecards commands."""

import json

from tests.conftest import WHOAMI_RESPONSE


SAMPLE_BATTLECARD = {
    "id": "bc-1",
    "organization_id": "org-456",
    "name": "vs Competitor X",
    "description": "Competitive positioning",
    "competitor_name": "Competitor X",
    "status": "active",
    "strengths": ["Better pricing"],
    "weaknesses": ["Less features"],
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def test_battlecards_list(invoke, mock_api):
    mock_api.get("/api/v1/battlecards").respond(200, json=[SAMPLE_BATTLECARD])
    result = invoke(["envoy", "battlecards", "list"])
    assert result.exit_code == 0
    assert "vs Competitor X" in result.output


def test_battlecards_list_json(invoke, mock_api):
    mock_api.get("/api/v1/battlecards").respond(200, json=[SAMPLE_BATTLECARD])
    result = invoke(["envoy", "battlecards", "list", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["name"] == "vs Competitor X"


def test_battlecards_get(invoke, mock_api):
    mock_api.get("/api/v1/battlecards/bc-1").respond(200, json=SAMPLE_BATTLECARD)
    result = invoke(["envoy", "battlecards", "get", "bc-1"])
    assert result.exit_code == 0
    assert "vs Competitor X" in result.output


def test_battlecards_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/battlecards/bc-999").respond(404, json={"detail": "Not found"})
    result = invoke(["envoy", "battlecards", "get", "bc-999"])
    assert result.exit_code == 3


def test_battlecards_create(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/battlecards").respond(201, json=SAMPLE_BATTLECARD)
    result = invoke(["envoy", "battlecards", "create", "--name", "vs Competitor X"])
    assert result.exit_code == 0
    assert "Created battlecard" in result.output


def test_battlecards_create_json(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/battlecards").respond(201, json=SAMPLE_BATTLECARD)
    result = invoke(["envoy", "battlecards", "create", "--name", "vs Competitor X", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["name"] == "vs Competitor X"


def test_battlecards_update(invoke, mock_api):
    updated = {**SAMPLE_BATTLECARD, "name": "Updated Battlecard"}
    mock_api.patch("/api/v1/battlecards/bc-1").respond(200, json=updated)
    result = invoke(["envoy", "battlecards", "update", "bc-1", "--name", "Updated Battlecard"])
    assert result.exit_code == 0
    assert "Updated battlecard" in result.output


def test_battlecards_update_no_fields(invoke, mock_api):
    result = invoke(["envoy", "battlecards", "update", "bc-1"])
    assert result.exit_code == 1


def test_battlecards_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/battlecards/bc-1").respond(204)
    result = invoke(["envoy", "battlecards", "delete", "bc-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_battlecards_delete_aborted(invoke, mock_api):
    result = invoke(["envoy", "battlecards", "delete", "bc-1"], input="n\n")
    assert result.exit_code == 1


def test_battlecards_duplicate(invoke, mock_api):
    duplicated = {**SAMPLE_BATTLECARD, "id": "bc-2", "name": "vs Competitor X (copy)"}
    mock_api.post("/api/v1/battlecards/bc-1/duplicate").respond(201, json=duplicated)
    result = invoke(["envoy", "battlecards", "duplicate", "bc-1"])
    assert result.exit_code == 0
    assert "Duplicated battlecard" in result.output
