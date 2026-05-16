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
    mock_api.post("/api/v1/tos/accept").respond(200, json={"accepted": True})
    result = invoke(["tos", "accept"])
    assert result.exit_code == 0
    assert "accepted" in result.output.lower()


def test_accept_json(invoke, mock_api):
    mock_api.post("/api/v1/tos/accept").respond(200, json={"accepted": True})
    result = invoke(["tos", "accept", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["accepted"] is True


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
