"""Load / save CLI configuration from ~/.agencycore/config.json."""

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".agencycore"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_API_URL = "http://localhost:8008"


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
