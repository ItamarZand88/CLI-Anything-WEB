"""Configuration constants for cli-web-${app_name}."""
from pathlib import Path

APP_NAME = "cli-web-${app_name}"
CONFIG_DIR = Path.home() / ".config" / APP_NAME


def get_config_dir() -> Path:
    """Return (and create) the config directory."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR
