"""Load / save CLI configuration from ~/.agencycore/config.json."""

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".agencycore"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_API_URL = "http://localhost:8008"

# Production environment defaults
PROD_API_URL = "https://api-eu.agencycore.io"
PROD_SUPABASE_URL = "https://mteekxbqwargphfcfsyr.supabase.co"
PROD_SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im10ZWVreGJxd2FyZ3BoZmNmc3lyIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NTA3NTA2MzEsImV4cCI6MjA2NjMyNjYzMX0"
    ".Vq2s-9EXBKOrGMAQbqZwYNyOGlldXZ2pgYS-6KEN8Q4"
)

# Staging environment defaults
STAGING_API_URL = "https://api.agencycore.dev"
STAGING_SUPABASE_URL = "https://tjzxfwiqommgrzxaflar.supabase.co"
STAGING_SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRqenhmd2lxb21tZ3J6eGFmbGFyIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NDkxNDAxODYsImV4cCI6MjA2NDcxNjE4Nn0"
    ".oq3bhnDBJtWA1K0Hs0GgrZeWxHSC4TuT1IjnvFo2Sig"
)

# Local development defaults
DEV_API_URL = "http://localhost:8008"
DEV_SUPABASE_URL = "http://127.0.0.1:54321"
DEV_SUPABASE_ANON_KEY = (
    "eyJhbGciOiJFUzI1NiIsImtpZCI6Ijk3YWQzMDY1LTdhM2UtNDQxNy1iYmRhLWVkOTNmOWJkYjY2NSIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjIwODUzOTEyMTV9"
    ".zKYmobkoFPZI-GYaPICU1E3UYzBOmsRxJqeuPL0X9s5PotMN3LW0d6HV5cTMGy7k3dWBlAQ0dJ7sqHXR1liRcA"
)

# Environment registry
ENVIRONMENTS: dict[str, dict[str, str]] = {
    "production": {
        "api_url": PROD_API_URL,
        "supabase_url": PROD_SUPABASE_URL,
        "supabase_anon_key": PROD_SUPABASE_ANON_KEY,
    },
    "staging": {
        "api_url": STAGING_API_URL,
        "supabase_url": STAGING_SUPABASE_URL,
        "supabase_anon_key": STAGING_SUPABASE_ANON_KEY,
    },
    "local": {
        "api_url": DEV_API_URL,
        "supabase_url": DEV_SUPABASE_URL,
        "supabase_anon_key": DEV_SUPABASE_ANON_KEY,
    },
}
ENV_NAMES = list(ENVIRONMENTS.keys())
DEFAULT_ENV = "production"


def _infer_env(flat: dict) -> str:
    """Infer environment name from a flat config's api_url."""
    api_url = flat.get("api_url", "")
    if "localhost" in api_url or "127.0.0.1" in api_url:
        return "local"
    if "agencycore.dev" in api_url:
        return "staging"
    return "production"


def _migrate_flat_config(flat: dict) -> dict:
    """Convert a flat (legacy) config to multi-env format."""
    env_name = _infer_env(flat)
    return {
        "active": env_name,
        "environments": {env_name: flat},
    }


def _read_raw() -> dict:
    """Read raw config JSON from disk."""
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text())


def _write_raw(data: dict) -> None:
    """Write raw config JSON to disk with restricted permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    fd = os.open(CONFIG_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)


def load_full_config() -> dict:
    """Load the full multi-env config, migrating from flat format if needed."""
    raw = _read_raw()
    if not raw:
        return {"active": DEFAULT_ENV, "environments": {}}
    # Already multi-env format
    if "environments" in raw:
        return raw
    # Legacy flat format — migrate and persist
    migrated = _migrate_flat_config(raw)
    _write_raw(migrated)
    return migrated


def save_full_config(full: dict) -> None:
    """Save the full multi-env config to disk."""
    _write_raw(full)


def load_config() -> dict:
    """Read config for the active environment.

    Returns a flat dict with api_url, supabase_url, supabase_anon_key,
    access_token, refresh_token — or empty dict if not logged in.
    """
    full = load_full_config()
    active = full.get("active", DEFAULT_ENV)
    return full.get("environments", {}).get(active, {})


def save_config(data: dict) -> None:
    """Save config for the active environment (flat dict)."""
    full = load_full_config()
    active = full.get("active", DEFAULT_ENV)
    envs = full.get("environments", {})
    envs[active] = data
    full["environments"] = envs
    save_full_config(full)


def get_active_env() -> str:
    """Return the name of the currently active environment."""
    full = load_full_config()
    return full.get("active", DEFAULT_ENV)


def set_active_env(env_name: str) -> None:
    """Switch the active environment."""
    full = load_full_config()
    full["active"] = env_name
    save_full_config(full)


def clear_env_config(env_name: str) -> None:
    """Remove stored credentials for a specific environment."""
    full = load_full_config()
    envs = full.get("environments", {})
    envs.pop(env_name, None)
    full["environments"] = envs
    save_full_config(full)


def clear_config() -> None:
    """Delete the config file (logs out of all environments)."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
