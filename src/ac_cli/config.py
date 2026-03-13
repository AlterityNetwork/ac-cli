"""Load / save CLI configuration from ~/.agencycore/config.json."""

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".agencycore"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_API_URL = "http://localhost:8008"

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


def load_config() -> dict:
    """Read config JSON. Returns empty dict if file is missing."""
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text())


def save_config(data: dict) -> None:
    """Write config JSON with restricted permissions (owner-only)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    fd = os.open(CONFIG_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)


def clear_config() -> None:
    """Delete the config file."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
