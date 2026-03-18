"""Config and file management for cli-web-futbin."""
from __future__ import annotations

import json
from pathlib import Path

APP_NAME = "cli-web-futbin"


def get_config_dir() -> Path:
    config_dir = Path.home() / ".config" / APP_NAME
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file() -> Path:
    return get_config_dir() / "config.json"


def load_config() -> dict:
    config_file = get_config_file()
    if config_file.exists():
        try:
            return json.loads(config_file.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def save_config(data: dict) -> None:
    config_file = get_config_file()
    config_file.write_text(json.dumps(data, indent=2))
    config_file.chmod(0o600)
