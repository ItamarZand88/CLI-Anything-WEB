"""Configuration helpers for cli-web-tripadvisor.

TripAdvisor is a public, no-auth site. This module provides only
the config directory path (for future use) and basic constants.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "tripadvisor"
CONFIG_DIR = Path(os.environ.get("CLI_WEB_TRIPADVISOR_CONFIG_DIR", "")) or (
    Path.home() / ".config" / f"cli-web-{APP_NAME}"
)


def ensure_config_dir() -> Path:
    """Create config directory if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR
