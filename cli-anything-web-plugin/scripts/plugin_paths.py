"""Canonical path discovery for cli-anything-web-plugin scripts.

Every script that needs to locate plugin resources (templates, other scripts,
skills, etc.) should import from this module instead of re-deriving paths
relative to `__file__`. This is the single source of truth — if the plugin
directory layout changes, only this file updates.

Usage:
    from plugin_paths import get_plugin_root, get_templates_dir

    tpl = get_templates_dir() / "exceptions.py.tpl"
"""
from __future__ import annotations

from pathlib import Path


def get_plugin_root() -> Path:
    """Return the cli-anything-web-plugin directory (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def get_scripts_dir() -> Path:
    """Return the scripts/ directory."""
    return get_plugin_root() / "scripts"


def get_templates_dir() -> Path:
    """Return the templates/ directory."""
    return get_plugin_root() / "templates"


def get_skills_dir() -> Path:
    """Return the skills/ directory."""
    return get_plugin_root() / "skills"


def get_agents_dir() -> Path:
    """Return the agents/ directory."""
    return get_plugin_root() / "agents"


def get_commands_dir() -> Path:
    """Return the commands/ directory."""
    return get_plugin_root() / "commands"
