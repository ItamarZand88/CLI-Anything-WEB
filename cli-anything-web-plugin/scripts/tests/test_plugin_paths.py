"""Tests for plugin_paths.py — canonical path discovery."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import plugin_paths  # noqa: E402


def test_plugin_root_is_parent_of_scripts():
    assert plugin_paths.get_plugin_root() == SCRIPTS_DIR.parent


def test_scripts_dir_matches_scripts_location():
    assert plugin_paths.get_scripts_dir() == SCRIPTS_DIR


def test_templates_dir_exists():
    assert plugin_paths.get_templates_dir().is_dir()
