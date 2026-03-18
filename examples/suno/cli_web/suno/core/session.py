"""Session state management for Suno CLI.

Tracks current workspace/project context and output preferences.
"""

import json
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".config" / "cli-web-suno"
SESSION_FILE = CONFIG_DIR / "session.json"


def _ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_session() -> dict:
    """Load session state."""
    if not SESSION_FILE.exists():
        return {"project_id": "default", "output_format": "table"}
    try:
        return json.loads(SESSION_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {"project_id": "default", "output_format": "table"}


def save_session(state: dict):
    """Save session state."""
    _ensure_config_dir()
    SESSION_FILE.write_text(json.dumps(state, indent=2))


def get_current_project() -> str:
    """Get current project ID."""
    return load_session().get("project_id", "default")


def set_current_project(project_id: str):
    """Set current project ID."""
    state = load_session()
    state["project_id"] = project_id
    save_session(state)
