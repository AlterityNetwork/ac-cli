"""Shared test fixtures for ac-cli tests."""

from unittest.mock import patch

import pytest
import respx
from typer.testing import CliRunner

from ac_cli.main import app

API_BASE = "http://test-api:8008"

MOCK_CONFIG = {
    "api_url": API_BASE,
    "access_token": "test-token",
    "refresh_token": "test-refresh-token",
    "supabase_url": "http://test-supabase",
    "supabase_anon_key": "test-anon-key",
}

WHOAMI_RESPONSE = {
    "user_id": "user-123",
    "organization_id": "org-456",
    "email": "test@example.com",
}


@pytest.fixture()
def mock_config():
    with patch("ac_cli.client.load_config", return_value=MOCK_CONFIG):
        yield MOCK_CONFIG


@pytest.fixture()
def mock_api():
    with respx.mock(base_url=API_BASE, assert_all_called=False) as router:
        yield router


@pytest.fixture()
def invoke(mock_config, mock_api):
    """Convenience fixture: returns a function that invokes the CLI app."""
    runner = CliRunner()

    def _invoke(args, input=None):
        return runner.invoke(app, args, input=input)

    return _invoke
