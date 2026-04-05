"""Configuration utilities for cli-web-airbnb.

Airbnb is a no-auth, stateless CLI — no credentials, no persistent context.
This module provides locale/currency defaults and the config directory path.
"""

from __future__ import annotations

import os
from pathlib import Path

# Config directory: ~/.config/cli-web-airbnb/ (or ~/.cli-web-airbnb/ fallback)
_CONFIG_DIR = Path.home() / ".config" / "cli-web-airbnb"


def get_config_dir() -> Path:
    """Return the config directory, creating it if needed."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return _CONFIG_DIR


# Default locale and currency (can be overridden via env vars)
DEFAULT_LOCALE: str = os.environ.get("CLI_WEB_AIRBNB_LOCALE", "en")
DEFAULT_CURRENCY: str = os.environ.get("CLI_WEB_AIRBNB_CURRENCY", "USD")
