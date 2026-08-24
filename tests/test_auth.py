"""Tests for auth commands: login, logout, whoami."""

import json
from unittest.mock import MagicMock, patch

import respx
from typer.testing import CliRunner

from ac_cli.main import app
from tests.conftest import API_BASE, MOCK_CONFIG, WHOAMI_RESPONSE

runner = CliRunner()


def _mock_supabase_login():
    """Create a mock supabase client that returns a valid session."""
    mock_session = MagicMock()
    mock_session.access_token = "test-access-token"
    mock_session.refresh_token = "test-refresh-token"

    mock_response = MagicMock()
    mock_response.session = mock_session

    mock_client = MagicMock()
    mock_client.auth.sign_in_with_password.return_value = mock_response
    return mock_client


def test_login_defaults_to_active_env():
    """Login without --env should use the currently active environment, not always production."""
    saved = {}

    def fake_save(full):
        saved.update(full)

    fake_full_config = {"active": "local", "environments": {}}

    with (
        patch("ac_cli.commands.auth.create_client", return_value=_mock_supabase_login()),
        patch("ac_cli.commands.auth.load_full_config", return_value=fake_full_config),
        patch("ac_cli.commands.auth.save_full_config", side_effect=fake_save),
        patch("ac_cli.commands.auth.get_active_env", return_value="local"),
    ):
        result = runner.invoke(
            app,
            ["auth", "login", "--email", "test@test.com", "--password", "pass"],
        )

    assert result.exit_code == 0
    assert "local" in result.output
    assert saved["active"] == "local"


def test_login_explicit_env_overrides_active():
    """Login with --env staging should use staging regardless of active env."""
    saved = {}

    def fake_save(full):
        saved.update(full)

    fake_full_config = {"active": "local", "environments": {}}

    with (
        patch("ac_cli.commands.auth.create_client", return_value=_mock_supabase_login()),
        patch("ac_cli.commands.auth.load_full_config", return_value=fake_full_config),
        patch("ac_cli.commands.auth.save_full_config", side_effect=fake_save),
        patch("ac_cli.commands.auth.get_active_env", return_value="local"),
    ):
        result = runner.invoke(
            app,
            ["auth", "login", "--email", "test@test.com", "--password", "pass", "--env", "staging"],
        )

    assert result.exit_code == 0
    assert "staging" in result.output
    assert saved["active"] == "staging"


# -- Logout -------------------------------------------------------------------


def test_logout_all():
    """Logout without --env clears all environments."""
    with patch("ac_cli.commands.auth.clear_config") as mock_clear:
        result = runner.invoke(app, ["auth", "logout"])

    assert result.exit_code == 0
    assert "all environments" in result.output.lower()
    mock_clear.assert_called_once()


def test_logout_specific_env():
    """Logout with --env clears only that environment."""
    with patch("ac_cli.commands.auth.clear_env_config") as mock_clear:
        result = runner.invoke(app, ["auth", "logout", "--env", "staging"])

    assert result.exit_code == 0
    assert "staging" in result.output
    mock_clear.assert_called_once_with("staging")


def test_logout_unknown_env():
    """Logout with unknown --env exits with error."""
    result = runner.invoke(app, ["auth", "logout", "--env", "nonexistent"])
    assert result.exit_code == 1
    assert "Unknown environment" in result.output


# -- Whoami --------------------------------------------------------------------


def test_whoami_happy():
    """Whoami shows user info."""
    with (
        respx.mock(base_url=API_BASE) as router,
        patch("ac_cli.client.load_config", return_value=MOCK_CONFIG),
        patch("ac_cli.commands.auth.get_active_env", return_value="staging"),
    ):
        router.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
        result = runner.invoke(app, ["auth", "whoami"])

    assert result.exit_code == 0
    assert "org-456" in result.output


def test_whoami_json():
    """Whoami --json outputs structured JSON with environment."""
    with (
        respx.mock(base_url=API_BASE) as router,
        patch("ac_cli.client.load_config", return_value=MOCK_CONFIG),
        patch("ac_cli.commands.auth.get_active_env", return_value="production"),
    ):
        router.get("/whoami").respond(200, json=WHOAMI_RESPONSE)
        result = runner.invoke(app, ["auth", "whoami", "--json"])

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["user_id"] == "user-123"
    assert parsed["environment"] == "production"


def test_whoami_403():
    """Whoami exits 4 on 403."""
    with (
        respx.mock(base_url=API_BASE) as router,
        patch("ac_cli.client.load_config", return_value=MOCK_CONFIG),
        patch("ac_cli.commands.auth.get_active_env", return_value="staging"),
    ):
        router.get("/whoami").respond(403, json={"detail": "Forbidden"})
        result = runner.invoke(app, ["auth", "whoami"])

    assert result.exit_code == 4


def test_whoami_json_error():
    """Whoami --json returns structured error on failure."""
    with (
        respx.mock(base_url=API_BASE) as router,
        patch("ac_cli.client.load_config", return_value=MOCK_CONFIG),
        patch("ac_cli.commands.auth.get_active_env", return_value="staging"),
    ):
        router.get("/whoami").respond(403, json={"detail": "Forbidden"})
        result = runner.invoke(app, ["auth", "whoami", "--json"])

    assert result.exit_code == 4
    parsed = json.loads(result.output)
    assert parsed["error"] is True
    assert parsed["status_code"] == 403


def test_whoami_renders_a_close_tag_in_the_detail():
    """whoami hand-copied _handle_error, so a bracket broke it there too."""
    with (
        respx.mock(base_url=API_BASE) as router,
        patch("ac_cli.client.load_config", return_value=MOCK_CONFIG),
        patch("ac_cli.commands.auth.get_active_env", return_value="staging"),
    ):
        router.get("/whoami").respond(409, json={"detail": "registry [/urgent] failed"})
        result = runner.invoke(app, ["auth", "whoami"])

    assert result.exit_code == 5
    assert "[/urgent]" in result.output


def test_login_renders_a_close_tag_in_the_provider_error():
    """Supabase writes this message, so a bracket in it broke the reason."""
    with (
        patch("ac_cli.client.load_config", return_value=MOCK_CONFIG),
        patch(
            "ac_cli.commands.auth.create_client",
            side_effect=RuntimeError("provider [/urgent] refused"),
        ),
    ):
        result = runner.invoke(
            app, ["auth", "login", "--env", "staging", "--email", "a@b.c", "--password", "x"]
        )

    assert result.exit_code == 1
    assert "[/urgent]" in result.output


def test_login_renders_a_close_tag_in_the_env_name():
    """The env name comes from the shell, and it sits inside a [red] wrapper."""
    result = runner.invoke(app, ["auth", "login", "--env", "[/urgent]"])

    assert result.exit_code == 1
    assert "Unknown environment" in result.output


def test_logout_renders_a_close_tag_in_the_env_name():
    result = runner.invoke(app, ["auth", "logout", "--env", "[/urgent]"])

    assert result.exit_code == 1
    assert "Unknown environment" in result.output
