"""Configuration management for NotebookLM CLI."""

from pathlib import Path


def get_app_dir() -> Path:
    """Get the app config directory."""
    d = Path.home() / ".config" / "cli-web-notebooklm"
    d.mkdir(parents=True, exist_ok=True)
    return d
