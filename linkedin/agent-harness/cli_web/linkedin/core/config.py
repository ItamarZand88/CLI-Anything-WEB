"""Configuration constants for cli-web-linkedin."""
from pathlib import Path

APP_NAME = "cli-web-linkedin"
CONFIG_DIR = Path.home() / ".config" / APP_NAME
AUTH_FILE = "auth.json"
AUTH_ENV_VAR = "CLI_WEB_LINKEDIN_AUTH_JSON"


def get_config_dir() -> Path:
    """Return (and create) the config directory."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def get_auth_path() -> Path:
    """Return the path to auth.json, creating config dir if needed."""
    return get_config_dir() / AUTH_FILE
