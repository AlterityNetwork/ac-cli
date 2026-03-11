"""Load / save CLI configuration from ~/.agencycore/config.json."""

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".agencycore"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    """Read config JSON. Returns empty dict if file is missing."""
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text())


def save_config(data: dict) -> None:
    """Write config JSON with restricted permissions (owner-only)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))
    os.chmod(CONFIG_FILE, 0o600)


def clear_config() -> None:
    """Delete the config file."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
