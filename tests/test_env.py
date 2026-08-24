"""Tests for environment management commands and config migration."""

import json
from unittest.mock import patch

from typer.testing import CliRunner

from ac_cli.config import (
    DEFAULT_ENV,
    DEV_API_URL,
    STAGING_API_URL,
    STAGING_SUPABASE_ANON_KEY,
    STAGING_SUPABASE_URL,
)
from ac_cli.main import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _multi_env_config(active="staging", envs=None):
    """Build a multi-env config dict."""
    if envs is None:
        envs = {
            "staging": {
                "api_url": STAGING_API_URL,
                "supabase_url": STAGING_SUPABASE_URL,
                "supabase_anon_key": STAGING_SUPABASE_ANON_KEY,
                "access_token": "stg-token",
                "refresh_token": "stg-refresh",
            },
        }
    return {"active": active, "environments": envs}


def _patch_full_config(full):
    return patch("ac_cli.commands.env.load_full_config", return_value=full)


# ---------------------------------------------------------------------------
# env list
# ---------------------------------------------------------------------------


class TestEnvList:
    def test_list_shows_all_envs(self):
        full = _multi_env_config()
        with _patch_full_config(full):
            result = runner.invoke(app, ["env", "list"])
        assert result.exit_code == 0
        assert "production" in result.output
        assert "staging" in result.output
        assert "local" in result.output

    def test_list_json(self):
        full = _multi_env_config()
        with _patch_full_config(full):
            result = runner.invoke(app, ["env", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 3
        names = {e["name"] for e in data}
        assert names == {"production", "staging", "local"}
        # staging should be active and logged in
        stg = next(e for e in data if e["name"] == "staging")
        assert stg["active"] is True
        assert stg["logged_in"] is True

    def test_list_not_logged_in(self):
        full = _multi_env_config(envs={})
        with _patch_full_config(full):
            result = runner.invoke(app, ["env", "list", "--json"])
        data = json.loads(result.output)
        assert all(e["logged_in"] is False for e in data)


# ---------------------------------------------------------------------------
# env show
# ---------------------------------------------------------------------------


class TestEnvShow:
    def test_show_active(self):
        full = _multi_env_config()
        with _patch_full_config(full):
            result = runner.invoke(app, ["env", "show"])
        assert result.exit_code == 0
        assert "staging" in result.output

    def test_show_json(self):
        full = _multi_env_config()
        with _patch_full_config(full):
            result = runner.invoke(app, ["env", "show", "--json"])
        data = json.loads(result.output)
        assert data["environment"] == "staging"
        assert data["logged_in"] is True


# ---------------------------------------------------------------------------
# env use
# ---------------------------------------------------------------------------


class TestEnvUse:
    def test_use_valid(self):
        full = _multi_env_config()
        with _patch_full_config(full), patch("ac_cli.commands.env.set_active_env") as mock_set:
            result = runner.invoke(app, ["env", "use", "production"])
        assert result.exit_code == 0
        mock_set.assert_called_once_with("production")

    def test_use_unknown(self):
        full = _multi_env_config()
        with _patch_full_config(full):
            result = runner.invoke(app, ["env", "use", "bogus"])
        assert result.exit_code == 1
        assert "Unknown environment" in result.output

    def test_use_renders_a_close_tag_in_the_name(self):
        """The name comes from the shell, and it sits inside a [red] wrapper."""
        full = _multi_env_config()
        with _patch_full_config(full):
            result = runner.invoke(app, ["env", "use", "[/urgent]"])
        assert result.exit_code == 1
        assert result.output.startswith("Unknown environment: [/urgent]\n")

    def test_use_warns_not_logged_in(self):
        full = _multi_env_config(envs={})
        with _patch_full_config(full), patch("ac_cli.commands.env.set_active_env"):
            result = runner.invoke(app, ["env", "use", "local"])
        assert result.exit_code == 0
        assert "not logged in" in result.output


# ---------------------------------------------------------------------------
# Config migration (flat → multi-env)
# ---------------------------------------------------------------------------


class TestConfigMigration:
    def test_migrate_staging_config(self, tmp_path):
        flat = {
            "api_url": STAGING_API_URL,
            "supabase_url": STAGING_SUPABASE_URL,
            "supabase_anon_key": STAGING_SUPABASE_ANON_KEY,
            "access_token": "tok",
            "refresh_token": "ref",
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(flat))

        with (
            patch("ac_cli.config.CONFIG_FILE", config_file),
            patch("ac_cli.config.CONFIG_DIR", tmp_path),
        ):
            from ac_cli.config import load_full_config

            full = load_full_config()

        assert full["active"] == "staging"
        assert full["environments"]["staging"] == flat

    def test_migrate_local_config(self, tmp_path):
        flat = {
            "api_url": DEV_API_URL,
            "supabase_url": "http://127.0.0.1:54321",
            "supabase_anon_key": "key",
            "access_token": "tok",
            "refresh_token": "ref",
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(flat))

        with (
            patch("ac_cli.config.CONFIG_FILE", config_file),
            patch("ac_cli.config.CONFIG_DIR", tmp_path),
        ):
            from ac_cli.config import load_full_config

            full = load_full_config()

        assert full["active"] == "local"
        assert full["environments"]["local"] == flat

    def test_already_multi_env_no_migration(self, tmp_path):
        multi = _multi_env_config()
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(multi))

        with (
            patch("ac_cli.config.CONFIG_FILE", config_file),
            patch("ac_cli.config.CONFIG_DIR", tmp_path),
        ):
            from ac_cli.config import load_full_config

            full = load_full_config()

        assert full == multi

    def test_empty_config(self, tmp_path):
        config_file = tmp_path / "config.json"
        # File doesn't exist
        with (
            patch("ac_cli.config.CONFIG_FILE", config_file),
            patch("ac_cli.config.CONFIG_DIR", tmp_path),
        ):
            from ac_cli.config import load_full_config

            full = load_full_config()

        assert full["active"] == DEFAULT_ENV
        assert full["environments"] == {}


# ---------------------------------------------------------------------------
# load_config / save_config backward compat
# ---------------------------------------------------------------------------


class TestLoadSaveCompat:
    def test_load_config_returns_flat_dict(self, tmp_path):
        env_data = {
            "api_url": STAGING_API_URL,
            "access_token": "tok",
            "refresh_token": "ref",
            "supabase_url": STAGING_SUPABASE_URL,
            "supabase_anon_key": STAGING_SUPABASE_ANON_KEY,
        }
        multi = {"active": "staging", "environments": {"staging": env_data}}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(multi))

        with (
            patch("ac_cli.config.CONFIG_FILE", config_file),
            patch("ac_cli.config.CONFIG_DIR", tmp_path),
        ):
            from ac_cli.config import load_config

            cfg = load_config()

        assert cfg == env_data

    def test_save_config_updates_active_env(self, tmp_path):
        multi = {"active": "staging", "environments": {"staging": {}}}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(multi))

        new_data = {"api_url": STAGING_API_URL, "access_token": "new-tok"}
        with (
            patch("ac_cli.config.CONFIG_FILE", config_file),
            patch("ac_cli.config.CONFIG_DIR", tmp_path),
        ):
            from ac_cli.config import save_config

            save_config(new_data)

        saved = json.loads(config_file.read_text())
        assert saved["environments"]["staging"] == new_data
        assert saved["active"] == "staging"
