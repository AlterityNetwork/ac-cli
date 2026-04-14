"""Tests for health check command."""

import json
from unittest.mock import patch

import httpx
import respx
from typer.testing import CliRunner

from ac_cli.main import app
from tests.conftest import API_BASE, MOCK_CONFIG

runner = CliRunner()


def _invoke_health(args, config_url=API_BASE):
    """Invoke health command with mocked config."""
    with patch("ac_cli.commands.health.load_config", return_value={**MOCK_CONFIG, "api_url": config_url}):
        return runner.invoke(app, ["health", "check"] + args)


@respx.mock
def test_health_check_happy():
    """Health check prints success when API is healthy."""
    respx.get(f"{API_BASE}/health").respond(200, json={"status": "healthy"})
    result = _invoke_health([])
    assert result.exit_code == 0
    assert "healthy" in result.output.lower()


@respx.mock
def test_health_check_json():
    """Health check --json outputs raw JSON."""
    respx.get(f"{API_BASE}/health").respond(200, json={"status": "healthy", "version": "1.0"})
    result = _invoke_health(["--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "healthy"


@respx.mock
def test_health_check_connection_error():
    """Health check exits 1 on connection error."""
    respx.get(f"{API_BASE}/health").mock(side_effect=httpx.ConnectError("Connection refused"))
    result = _invoke_health([])
    assert result.exit_code == 1
    assert "failed" in result.output.lower() or "error" in result.output.lower()


@respx.mock
def test_health_check_connection_error_json():
    """Health check --json outputs structured error on connection failure."""
    respx.get(f"{API_BASE}/health").mock(side_effect=httpx.ConnectError("Connection refused"))
    result = _invoke_health(["--json"])
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] is None


@respx.mock
def test_health_check_server_error():
    """Health check exits 1 on 500 server error."""
    respx.get(f"{API_BASE}/health").respond(500, json={"detail": "Internal error"})
    result = _invoke_health([])
    assert result.exit_code == 1


@respx.mock
def test_health_check_custom_api_url():
    """Health check respects --api-url override."""
    custom = "http://custom-api:9999"
    respx.get(f"{custom}/health").respond(200, json={"status": "healthy"})
    result = _invoke_health(["--api-url", custom])
    assert result.exit_code == 0
