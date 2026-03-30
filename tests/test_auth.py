"""Tests for auth commands: login environment handling."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ac_cli.main import app

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
