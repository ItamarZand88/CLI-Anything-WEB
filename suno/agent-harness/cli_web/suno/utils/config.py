"""Configuration file management."""

from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "cli-web-suno"


def get_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR
