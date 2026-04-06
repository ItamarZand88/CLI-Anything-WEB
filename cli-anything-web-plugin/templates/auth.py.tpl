"""Auth management for cli-web-${app_name}."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from .exceptions import AuthError

CONFIG_DIR = Path.home() / ".config" / "cli-web-${app_name}"
AUTH_FILE = CONFIG_DIR / "auth.json"
ENV_VAR = "CLI_WEB_${APP_NAME}_AUTH_JSON"


def _ensure_dir() -> None:
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def save_auth(data: dict) -> Path:
    """Save auth data to auth.json with restrictive permissions (600)."""
    _ensure_dir()
    AUTH_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.chmod(AUTH_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass  # Windows may not support chmod
    return AUTH_FILE


def load_auth() -> dict:
    """Load auth from env var or file.

    Returns:
        Auth data dict.

    Raises:
        AuthError: If no auth data is found.
    """
    # 1. Try env var first (CI/CD)
    env_val = os.environ.get(ENV_VAR)
    if env_val:
        try:
            data = json.loads(env_val)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # 2. Try auth file
    if AUTH_FILE.exists():
        try:
            data = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass

    raise AuthError("Not logged in. Run: cli-web-${app_name} auth login")


def clear_auth() -> None:
    """Remove auth file."""
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()


def is_logged_in() -> bool:
    """Check if auth credentials exist."""
    try:
        load_auth()
        return True
    except AuthError:
        return False


# --- Add site-specific login functions below ---
# def login_browser() -> dict:
#     """Open browser for manual login, capture cookies."""
#     ...
