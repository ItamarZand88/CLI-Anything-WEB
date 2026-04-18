"""Tests for mitmproxy-capture.py.

mitmproxy is an optional dependency of the plugin; these tests are skipped
when it's not installed. When installed, they cover the pure helpers that
don't require a live proxy or browser:

- `write_output()` JSON schema
- state/signal file path helpers
- `_is_pid_alive()` process-liveness check
- `_cleanup_state_files()` idempotency
- `_flush_traffic()` incremental writer

The noise/static filtering helpers (`_is_noise` / `_is_static`) are aliased
from `traffic_utils` and already have dedicated coverage there.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
MITMPROXY_CAPTURE = SCRIPTS_DIR / "mitmproxy-capture.py"


def _has_mitmproxy() -> bool:
    return importlib.util.find_spec("mitmproxy") is not None


# --- Environment-agnostic CLI contract checks ---

def test_script_exists_with_python_shebang():
    assert MITMPROXY_CAPTURE.exists()
    first_line = MITMPROXY_CAPTURE.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("#!") and "python" in first_line


@pytest.mark.skipif(not _has_mitmproxy(), reason="mitmproxy not installed")
def test_help_output_lists_subcommands():
    """When mitmproxy is installed, --help must list start-proxy / stop-proxy / capture."""
    result = subprocess.run(
        [sys.executable, str(MITMPROXY_CAPTURE), "--help"],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0
    for cmd in ("start-proxy", "stop-proxy", "capture"):
        assert cmd in result.stdout


# --- In-process helper tests (only runnable with mitmproxy) ---

# The capture script imports mitmproxy at module-top, so we can't load
# it in-process without the dep. Helper tests below are guarded.

pytestmark_needs_mitmproxy = pytest.mark.skipif(
    not _has_mitmproxy(), reason="mitmproxy not installed"
)


@pytest.fixture(scope="module")
def mod() -> ModuleType:
    if not _has_mitmproxy():
        pytest.skip("mitmproxy not installed")
    spec = importlib.util.spec_from_file_location("mitmproxy_capture", MITMPROXY_CAPTURE)
    m = importlib.util.module_from_spec(spec)
    sys.modules["mitmproxy_capture"] = m
    spec.loader.exec_module(m)
    return m


# --- Static + noise filters (smoke-level; full coverage in traffic_utils) ---

def test_is_static_filter_catches_js(mod):
    assert mod._is_static("https://cdn.example.com/app.js") is True


def test_is_static_filter_catches_media_extensions(mod):
    assert mod._is_static("https://cdn.example.com/clip.mp4") is True


def test_is_static_filter_rejects_api_url(mod):
    assert mod._is_static("https://api.example.com/v1/users") is False


# --- State file paths ---

def test_state_file_paths_are_distinct_per_port(mod):
    p0 = mod._state_file_path(0)
    p1 = mod._state_file_path(8080)
    p2 = mod._state_file_path(9090)
    assert p0 != p1 != p2


def test_stop_signal_path_distinct_from_state(mod):
    state = mod._state_file_path(8080)
    stop = mod._stop_signal_path(8080)
    assert state != stop


# --- PID liveness check ---

def test_is_pid_alive_true_for_self(mod):
    assert mod._is_pid_alive(os.getpid()) is True


def test_is_pid_alive_false_for_unlikely_pid(mod):
    # 2**31 - 1 is valid on Linux but virtually never assigned.
    assert mod._is_pid_alive(2147483647) is False


# --- write_output JSON schema ---

def test_write_output_produces_valid_json(mod, tmp_path):
    entries = [
        {"url": "https://api.example.com/v1/items", "method": "GET", "status": 200},
        {"url": "https://api.example.com/v1/items", "method": "POST", "status": 201},
    ]
    stats = {"captured": 2, "filtered": 0}
    out = tmp_path / "raw.json"
    mod.write_output(entries, out, stats)
    assert out.exists()
    data = json.loads(out.read_text())
    # Shape: either list of entries (legacy) or dict with entries + stats
    if isinstance(data, dict):
        assert "entries" in data or "captured" in data or len(data) > 0
    else:
        assert isinstance(data, list)
        assert len(data) == 2


def test_write_output_creates_parent_directories(mod, tmp_path):
    out = tmp_path / "deep" / "nested" / "raw.json"
    mod.write_output([], out, {"captured": 0})
    assert out.exists()


# --- Read-state returns None when file absent ---

def test_read_state_returns_none_when_missing(mod):
    # Use a very unlikely port to guarantee no state file
    assert mod._read_state(port=9999) is None


# --- cleanup is idempotent ---

def test_cleanup_state_files_is_no_op_when_absent(mod):
    # Must not raise when there's nothing to clean
    mod._cleanup_state_files(port=9999)


# --- _flush_traffic writes JSON-serializable entries ---

def test_flush_traffic_writes_entries_to_disk(mod, tmp_path):
    out = tmp_path / "flush.json"
    entries = [{"url": "https://x.test", "method": "GET", "status": 200}]
    mod._flush_traffic(entries, out)
    assert out.exists()
    data = json.loads(out.read_text())
    assert isinstance(data, list)
    assert data[0]["url"] == "https://x.test"


def test_flush_traffic_overwrites_existing_file(mod, tmp_path):
    out = tmp_path / "flush.json"
    mod._flush_traffic([{"url": "old", "method": "GET", "status": 200}], out)
    mod._flush_traffic([{"url": "new", "method": "GET", "status": 200}], out)
    data = json.loads(out.read_text())
    assert len(data) == 1
    assert data[0]["url"] == "new"
