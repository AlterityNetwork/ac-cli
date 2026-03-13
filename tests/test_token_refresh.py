"""Tests for automatic token refresh on 401 responses."""

from unittest.mock import MagicMock, patch

import httpx
from supabase import AuthApiError
from typer.testing import CliRunner

from ac_cli.main import app
from tests.conftest import API_BASE, MOCK_CONFIG, WHOAMI_RESPONSE

runner = CliRunner()


def _make_mock_session(access_token="new-access-token", refresh_token="new-refresh-token"):
    session = MagicMock()
    session.access_token = access_token
    session.refresh_token = refresh_token
    return session


def _make_mock_supabase(session):
    mock_sb = MagicMock()
    mock_response = MagicMock()
    mock_response.session = session
    mock_sb.auth.refresh_session.return_value = mock_response
    return mock_sb


# The lazy import in _refresh_access_token does `from supabase import create_client`,
# so we patch it on the supabase module.
PATCH_CREATE_CLIENT = "supabase.create_client"


def test_auto_refresh_on_401(mock_api):
    """First request gets 401, refresh succeeds, retry succeeds."""
    mock_api.get("/api/v1/crm/companies").mock(
        side_effect=[
            httpx.Response(401, json={"detail": "JWT expired"}),
            httpx.Response(200, json={"data": [], "total": 0}),
        ]
    )

    session = _make_mock_session()
    mock_sb = _make_mock_supabase(session)
    saved_configs = []

    def capture_save(data):
        saved_configs.append(data.copy())

    with (
        patch("ac_cli.client.load_config", return_value=MOCK_CONFIG.copy()),
        patch("ac_cli.client.save_config", side_effect=capture_save),
        patch(PATCH_CREATE_CLIENT, return_value=mock_sb),
    ):
        result = runner.invoke(app, ["crm", "companies", "list"])

    assert result.exit_code == 0
    assert len(saved_configs) == 1
    assert saved_configs[0]["access_token"] == "new-access-token"
    assert saved_configs[0]["refresh_token"] == "new-refresh-token"


def test_refresh_failure_exits(mock_api):
    """If token refresh fails, CLI exits with error."""
    mock_api.get("/api/v1/crm/companies").respond(401, json={"detail": "JWT expired"})

    mock_sb = MagicMock()
    mock_sb.auth.refresh_session.side_effect = AuthApiError("Refresh token revoked", 401, None)

    with (
        patch("ac_cli.client.load_config", return_value=MOCK_CONFIG.copy()),
        patch(PATCH_CREATE_CLIENT, return_value=mock_sb),
    ):
        result = runner.invoke(app, ["crm", "companies", "list"])

    assert result.exit_code == 1
    assert "refresh failed" in result.output.lower() or "login" in result.output.lower()


def test_refresh_no_session_exits(mock_api):
    """If refresh returns no session, CLI exits with error."""
    mock_api.get("/api/v1/crm/companies").respond(401, json={"detail": "JWT expired"})

    mock_sb = MagicMock()
    mock_response = MagicMock()
    mock_response.session = None
    mock_sb.auth.refresh_session.return_value = mock_response

    with (
        patch("ac_cli.client.load_config", return_value=MOCK_CONFIG.copy()),
        patch(PATCH_CREATE_CLIENT, return_value=mock_sb),
    ):
        result = runner.invoke(app, ["crm", "companies", "list"])

    assert result.exit_code == 1
    assert "login" in result.output.lower()


def test_no_refresh_token_exits(mock_api):
    """If no refresh_token in config, CLI exits with login prompt."""
    mock_api.get("/api/v1/crm/companies").respond(401, json={"detail": "JWT expired"})

    cfg_no_refresh = {
        "api_url": API_BASE,
        "access_token": "expired-token",
    }

    with patch("ac_cli.client.load_config", return_value=cfg_no_refresh):
        result = runner.invoke(app, ["crm", "companies", "list"])

    assert result.exit_code == 1
    assert "login" in result.output.lower()


def test_no_refresh_needed_on_200(mock_api):
    """Normal 200 response does not trigger refresh."""
    mock_api.get("/api/v1/crm/companies").respond(200, json={"data": [], "total": 0})

    with patch("ac_cli.client.load_config", return_value=MOCK_CONFIG.copy()):
        result = runner.invoke(app, ["crm", "companies", "list"])

    assert result.exit_code == 0


def test_refresh_updates_client_headers(mock_api):
    """After refresh on first request, second request in same session uses new token."""
    mock_api.get("/whoami").mock(
        side_effect=[
            httpx.Response(401, json={"detail": "JWT expired"}),
            httpx.Response(200, json=WHOAMI_RESPONSE),
        ]
    )
    mock_api.post("/api/v1/crm/companies").respond(201, json={
        "id": "c1", "organization_id": "org-456", "name": "Test",
        "lifecycle_stage": "target", "tags": [],
        "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
        "data_version": 1,
    })

    session = _make_mock_session()
    mock_sb = _make_mock_supabase(session)

    with (
        patch("ac_cli.client.load_config", return_value=MOCK_CONFIG.copy()),
        patch("ac_cli.client.save_config"),
        patch(PATCH_CREATE_CLIENT, return_value=mock_sb),
    ):
        result = runner.invoke(app, ["crm", "companies", "create", "--name", "Test"])

    assert result.exit_code == 0
    assert "Created company" in result.output
