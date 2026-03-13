"""Tests for hooks commands."""

import json

SAMPLE_HOOK = {
    "name": "email-send",
    "capability": "email",
    "description": "Send email via connected provider",
}


def test_hooks_list(invoke, mock_api):
    mock_api.get("/api/v1/platform/hooks").respond(200, json=[SAMPLE_HOOK])
    result = invoke(["hooks", "list", "email"])
    assert result.exit_code == 0
    assert "email-send" in result.output


def test_hooks_list_json(invoke, mock_api):
    mock_api.get("/api/v1/platform/hooks").respond(200, json=[SAMPLE_HOOK])
    result = invoke(["hooks", "--json", "list", "email"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["name"] == "email-send"


def test_hooks_list_empty(invoke, mock_api):
    mock_api.get("/api/v1/platform/hooks").respond(200, json=[])
    result = invoke(["hooks", "list", "email"])
    assert result.exit_code == 0
    assert "No hooks found" in result.output
