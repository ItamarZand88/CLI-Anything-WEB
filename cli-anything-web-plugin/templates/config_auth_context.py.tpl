"""Configuration constants for cli-web-${app_name}."""
from pathlib import Path

APP_NAME = "cli-web-${app_name}"
CONFIG_DIR = Path.home() / ".config" / APP_NAME
AUTH_FILE = "auth.json"
AUTH_ENV_VAR = "CLI_WEB_${APP_NAME}_AUTH_JSON"
CONTEXT_FILE = "context.json"


def get_config_dir() -> Path:
    """Return (and create) the config directory."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def get_auth_path() -> Path:
    """Return the path to auth.json, creating config dir if needed."""
    return get_config_dir() / AUTH_FILE
