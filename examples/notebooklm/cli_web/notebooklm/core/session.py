"""Session state management for NotebookLM CLI."""

import json
from pathlib import Path

from cli_web.notebooklm.core.auth import get_config_dir


def get_session_path() -> Path:
    """Get the path to session state file."""
    return get_config_dir() / "session.json"


def load_session() -> dict:
    """Load the current session state."""
    path = get_session_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_session(state: dict):
    """Save session state."""
    path = get_session_path()
    path.write_text(json.dumps(state, indent=2))


def get_current_notebook() -> str | None:
    """Get the currently selected notebook ID."""
    return load_session().get("current_notebook")


def set_current_notebook(notebook_id: str, title: str = ""):
    """Set the currently selected notebook."""
    state = load_session()
    state["current_notebook"] = notebook_id
    state["current_notebook_title"] = title
    save_session(state)
