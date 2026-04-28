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
    result = invoke(["hooks", "list", "email", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["name"] == "email-send"


def test_hooks_list_empty(invoke, mock_api):
    mock_api.get("/api/v1/platform/hooks").respond(200, json=[])
    result = invoke(["hooks", "list", "email"])
    assert result.exit_code == 0
    assert "No hooks found" in result.output


def test_hooks_list_passes_capability(invoke, mock_api):
    route = mock_api.get("/api/v1/platform/hooks").respond(200, json=[])
    result = invoke(["hooks", "list", "calendar"])
    assert result.exit_code == 0
    assert "capability=calendar" in str(route.calls.last.request.url)


def test_hooks_list_paginated_envelope(invoke, mock_api):
    """API may return either a bare list or {"data": [...]}; CLI handles both."""
    mock_api.get("/api/v1/platform/hooks").respond(
        200, json={"data": [SAMPLE_HOOK]}
    )
    result = invoke(["hooks", "list", "email"])
    assert result.exit_code == 0
    assert "email-send" in result.output


def test_hooks_list_server_error(invoke, mock_api):
    mock_api.get("/api/v1/platform/hooks").respond(500, json={"detail": "boom"})
    result = invoke(["hooks", "list", "email"])
    assert result.exit_code == 1


def test_hooks_list_forbidden(invoke, mock_api):
    mock_api.get("/api/v1/platform/hooks").respond(403, json={"detail": "denied"})
    result = invoke(["hooks", "list", "email"])
    assert result.exit_code == 4
