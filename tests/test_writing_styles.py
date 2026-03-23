"""Tests for writing styles commands."""

import json

from tests.conftest import WHOAMI_RESPONSE


SAMPLE_STYLE = {
    "id": "ws-1",
    "organization_id": "org-456",
    "name": "Professional",
    "description": "Professional tone for B2B",
    "tone": "professional",
    "formality": "formal",
    "status": "active",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def test_styles_list(invoke, mock_api):
    mock_api.get("/api/v1/writing-styles").respond(200, json={"data": [SAMPLE_STYLE], "total": 1})
    result = invoke(["styles", "list"])
    assert result.exit_code == 0
    assert "Professional" in result.output


def test_styles_list_json(invoke, mock_api):
    mock_api.get("/api/v1/writing-styles").respond(200, json={"data": [SAMPLE_STYLE], "total": 1})
    result = invoke(["styles", "--json", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"][0]["name"] == "Professional"


def test_styles_get(invoke, mock_api):
    mock_api.get("/api/v1/writing-styles/ws-1").respond(200, json=SAMPLE_STYLE)
    result = invoke(["styles", "get", "ws-1"])
    assert result.exit_code == 0
    assert "Professional" in result.output


def test_styles_get_not_found(invoke, mock_api):
    mock_api.get("/api/v1/writing-styles/ws-1").respond(404, json={"detail": "Not found"})
    result = invoke(["styles", "get", "ws-1"])
    assert result.exit_code == 3


def test_styles_create(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/writing-styles").respond(201, json=SAMPLE_STYLE)
    result = invoke(["styles", "create", "--name", "Professional"])
    assert result.exit_code == 0
    assert "Created style" in result.output


def test_styles_create_json(invoke, mock_api):
    mock_api.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
    mock_api.post("/api/v1/writing-styles").respond(201, json=SAMPLE_STYLE)
    result = invoke(["styles", "--json", "create", "--name", "Professional"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["name"] == "Professional"


def test_styles_update(invoke, mock_api):
    updated = {**SAMPLE_STYLE, "name": "Updated Style"}
    mock_api.put("/api/v1/writing-styles/ws-1").respond(200, json=updated)
    result = invoke(["styles", "update", "ws-1", "--name", "Updated Style"])
    assert result.exit_code == 0
    assert "Updated style" in result.output


def test_styles_update_no_fields(invoke, mock_api):
    result = invoke(["styles", "update", "ws-1"])
    assert result.exit_code == 1
    assert "No fields" in result.output


def test_styles_delete_with_yes(invoke, mock_api):
    mock_api.delete("/api/v1/writing-styles/ws-1").respond(204)
    result = invoke(["styles", "delete", "ws-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_styles_delete_aborted(invoke, mock_api):
    result = invoke(["styles", "delete", "ws-1"], input="n\n")
    assert result.exit_code == 1


def test_styles_train(invoke, mock_api):
    mock_api.post("/api/v1/writing-styles/ws-1/train").respond(200, json={"session_id": "ts-1", "status": "started"})
    result = invoke(["styles", "train", "ws-1", "--sample-text", "This is a sample."])
    assert result.exit_code == 0
    assert "Training session" in result.output


def test_styles_feedback(invoke, mock_api):
    mock_api.post("/api/v1/writing-styles/training-sessions/ts-1/feedback").respond(200, json={"status": "received"})
    result = invoke(["styles", "feedback", "ts-1", "--rating", "5", "--comments", "Great"])
    assert result.exit_code == 0
    assert "Feedback submitted" in result.output


def test_styles_iterate(invoke, mock_api):
    mock_api.post("/api/v1/writing-styles/training-sessions/ts-1/iterate").respond(200, json={"status": "iterating"})
    result = invoke(["styles", "iterate", "ts-1", "--feedback", "More formal please"])
    assert result.exit_code == 0
    assert "Iteration submitted" in result.output


def test_styles_analyze(invoke, mock_api):
    mock_api.post("/api/v1/writing-styles/analyze").respond(200, json={"analysis": "Good tone"})
    result = invoke(["styles", "analyze", "--text", "Hello world"])
    assert result.exit_code == 0
    assert "Good tone" in result.output


def test_styles_analyze_json(invoke, mock_api):
    mock_api.post("/api/v1/writing-styles/analyze").respond(200, json={"analysis": "Good tone"})
    result = invoke(["styles", "--json", "analyze", "--text", "Hello world"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["analysis"] == "Good tone"
