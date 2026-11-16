"""Tests for TOS commands."""

import json


def test_config(invoke, mock_api):
    mock_api.get("/api/v1/tos/config").respond(
        200, json={"version": "3.0", "embed_url": "https://termly.io/tos"}
    )
    result = invoke(["tos", "config"])
    assert result.exit_code == 0
    assert "3.0" in result.output


def test_config_json(invoke, mock_api):
    mock_api.get("/api/v1/tos/config").respond(
        200, json={"version": "3.0", "embed_url": "https://termly.io/tos"}
    )
    result = invoke(["tos", "config", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["version"] == "3.0"


def test_status(invoke, mock_api):
    mock_api.get("/api/v1/tos/status").respond(200, json={"accepted": True, "version": "3.0"})
    result = invoke(["tos", "status"])
    assert result.exit_code == 0
    assert "Accepted" in result.output


def test_status_json(invoke, mock_api):
    mock_api.get("/api/v1/tos/status").respond(200, json={"accepted": False})
    result = invoke(["tos", "status", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["accepted"] is False


def test_accept(invoke, mock_api):
    mock_api.get("/api/v1/tos/config").respond(
        200, json={"current_version": "3.0", "termly_embed_url": ""}
    )
    route = mock_api.post("/api/v1/tos/accept").respond(200, json={"accepted": True})
    result = invoke(["tos", "accept"])
    assert result.exit_code == 0
    assert "accepted" in result.output.lower()
    assert json.loads(route.calls.last.request.content) == {"tos_version": "3.0"}


def test_accept_json(invoke, mock_api):
    mock_api.get("/api/v1/tos/config").respond(
        200, json={"current_version": "3.0", "termly_embed_url": ""}
    )
    mock_api.post("/api/v1/tos/accept").respond(200, json={"accepted": True})
    result = invoke(["tos", "accept", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["accepted"] is True


def test_accept_a_named_version_skips_the_config_read(invoke, mock_api):
    config = mock_api.get("/api/v1/tos/config")
    route = mock_api.post("/api/v1/tos/accept").respond(200, json={"accepted": True})
    result = invoke(["tos", "accept", "--version", "2.1"])
    assert result.exit_code == 0
    assert not config.called
    assert json.loads(route.calls.last.request.content) == {"tos_version": "2.1"}


def test_accept_with_no_current_version_stops(invoke, mock_api):
    mock_api.get("/api/v1/tos/config").respond(
        200, json={"current_version": "", "termly_embed_url": ""}
    )
    route = mock_api.post("/api/v1/tos/accept")
    result = invoke(["tos", "accept"])
    assert result.exit_code == 1
    assert not route.called


def test_update_config(invoke, mock_api):
    mock_api.patch("/api/v1/admin/tos/config").respond(200, json={"version": "4.0"})
    result = invoke(["tos", "update-config", "--version", "4.0"])
    assert result.exit_code == 0
    assert "updated" in result.output.lower()


def test_update_config_json(invoke, mock_api):
    mock_api.patch("/api/v1/admin/tos/config").respond(200, json={"version": "4.0"})
    result = invoke(["tos", "update-config", "--version", "4.0", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["version"] == "4.0"


def test_update_config_no_fields(invoke, mock_api):
    result = invoke(["tos", "update-config"])
    assert result.exit_code == 1


def test_update_config_sends_api_field_names(invoke, mock_api):
    route = mock_api.patch("/api/v1/admin/tos/config").respond(200, json={})
    result = invoke(
        ["tos", "update-config", "--version", "4.0", "--embed-url", "https://example.com/tos"]
    )
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {
        "current_version": "4.0",
        "termly_embed_url": "https://example.com/tos",
    }
