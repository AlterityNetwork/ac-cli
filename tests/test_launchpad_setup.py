"""Tests for the launchpad setup commands."""

import json

_PATH = "/api/v1/launchpad/setup"

OPEN = {
    "steps": [
        {"id": "mailbox", "done": True},
        {"id": "linkedin", "done": False},
        {"id": "ideal_customer", "done": False},
        {"id": "signals_search", "done": False},
        {"id": "writing_style", "done": False},
    ],
    "completed": 1,
    "total": 5,
    "dismissed": False,
    "visible": True,
}


def test_get_lists_each_step(invoke, mock_api):
    mock_api.get(_PATH).respond(200, json=OPEN)
    result = invoke(["launchpad", "setup", "get"])
    assert result.exit_code == 0
    assert "Connect your mailbox" in result.output
    assert "Create a writing style" in result.output
    assert "1 of 5" in result.output


def test_get_json(invoke, mock_api):
    mock_api.get(_PATH).respond(200, json=OPEN)
    result = invoke(["launchpad", "setup", "get", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["completed"] == 1
    assert parsed["visible"] is True


def test_dismiss_posts_and_confirms(invoke, mock_api):
    route = mock_api.post(f"{_PATH}/dismiss").respond(
        200, json={**OPEN, "dismissed": True, "visible": False}
    )
    result = invoke(["launchpad", "setup", "dismiss"])
    assert result.exit_code == 0
    assert route.called
    assert "Dismissed" in result.output


def test_dismiss_json(invoke, mock_api):
    mock_api.post(f"{_PATH}/dismiss").respond(
        200, json={**OPEN, "dismissed": True, "visible": False}
    )
    result = invoke(["launchpad", "setup", "dismiss", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["dismissed"] is True
