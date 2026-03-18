"""Configuration management for FUTBIN CLI."""

from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "cli-web-futbin"


def get_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR
