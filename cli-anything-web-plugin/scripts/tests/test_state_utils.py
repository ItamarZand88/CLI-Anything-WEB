"""Tests for state_utils.py — shared JSON-state I/O."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import state_utils  # noqa: E402


def test_utc_now_iso_format():
    value = state_utils.utc_now_iso()
    # ISO-8601 UTC: "YYYY-MM-DDTHH:MM:SS.microseconds+00:00"
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*\+00:00$", value)


def test_load_json_state_returns_default_when_missing(tmp_path):
    path = tmp_path / "missing.json"
    default = {"hello": "world"}
    assert state_utils.load_json_state(path, default=default) == default


def test_load_json_state_returns_none_when_missing_no_default(tmp_path):
    assert state_utils.load_json_state(tmp_path / "missing.json") is None


def test_save_and_reload_round_trip(tmp_path):
    path = tmp_path / "state.json"
    state_utils.save_json_state(path, {"phase": "capture", "status": "done"})
    loaded = state_utils.load_json_state(path)
    assert loaded["phase"] == "capture"
    assert loaded["status"] == "done"
    assert "updated_at" in loaded  # stamped on save


def test_save_creates_parent_dirs(tmp_path):
    path = tmp_path / "deep" / "nested" / "state.json"
    state_utils.save_json_state(path, {"x": 1})
    assert path.exists()


def test_save_stamps_updated_at(tmp_path):
    path = tmp_path / "state.json"
    s = {"a": 1}
    state_utils.save_json_state(path, s)
    assert "updated_at" in s  # mutates in place
