"""Tests for phase-state.py — pipeline phase tracking (4-phase CLI lifecycle).

phase-state.py is a CLI tool used by every Phase 2/3/4 skill to check whether
the previous phase is done and to mark the current one complete/failed. These
tests drive it via subprocess to mirror real usage.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
PHASE_STATE = SCRIPTS_DIR / "phase-state.py"


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [sys.executable, str(PHASE_STATE), *args],
        capture_output=True, text=True,
    )
    if check and result.returncode not in (0, 1):
        raise AssertionError(f"phase-state.py failed: {result.stderr}")
    return result


def _status(app_dir: Path) -> dict:
    return json.loads(_run("status", str(app_dir)).stdout)


# --- Fresh state ---

def test_status_on_fresh_app_reports_all_phases_pending(tmp_path):
    report = _status(tmp_path)
    for phase in ("capture", "methodology", "testing", "standards"):
        assert report["phases"][phase]["status"] == "pending"
    assert report["current_phase"] == "capture"
    assert "Run capture phase" in report["next_action"]


# --- complete ---

def test_complete_marks_phase_done_and_persists_output(tmp_path):
    _run("complete", str(tmp_path), "--phase", "capture", "--output", "/tmp/raw.json", "--notes", "went fine")
    report = _status(tmp_path)
    assert report["phases"]["capture"]["status"] == "done"
    assert report["phases"]["capture"]["output"] == "/tmp/raw.json"
    assert report["phases"]["capture"]["notes"] == "went fine"
    assert "completed_at" in report["phases"]["capture"]
    assert report["current_phase"] == "methodology"


def test_completing_phase_writes_state_file(tmp_path):
    _run("complete", str(tmp_path), "--phase", "capture")
    state_file = tmp_path / "phase-state.json"
    assert state_file.exists()
    state = json.loads(state_file.read_text())
    assert state["phases"]["capture"]["status"] == "done"
    assert "updated_at" in state


# --- fail ---

def test_fail_marks_phase_with_error_and_type(tmp_path):
    _run("fail", str(tmp_path), "--phase", "testing",
         "--error", "3 tests failed", "--error-type", "retryable")
    report = _status(tmp_path)
    assert report["phases"]["testing"]["status"] == "failed"
    assert report["phases"]["testing"]["error"] == "3 tests failed"
    assert report["phases"]["testing"]["error_type"] == "retryable"


def test_failed_phase_shows_in_next_action(tmp_path):
    # Mark capture done so the next-action logic picks up on a real failure
    _run("complete", str(tmp_path), "--phase", "capture")
    _run("fail", str(tmp_path), "--phase", "methodology",
         "--error", "boom", "--error-type", "retryable")
    report = _status(tmp_path)
    # current_phase should point at the failed phase
    assert report["current_phase"] == "methodology"
    assert "Retry" in report["next_action"] or "fix" in report["next_action"].lower()


def test_fail_with_fatal_error_type_suggests_force(tmp_path):
    _run("fail", str(tmp_path), "--phase", "capture", "--error", "boom", "--error-type", "fatal")
    report = _status(tmp_path)
    assert "--force" in report["next_action"] or "Fix" in report["next_action"]


# --- reset ---

def test_reset_returns_phase_to_pending(tmp_path):
    _run("complete", str(tmp_path), "--phase", "capture")
    _run("reset", str(tmp_path), "--phase", "capture")
    report = _status(tmp_path)
    assert report["phases"]["capture"]["status"] == "pending"


# --- check (exit code contract) ---

def test_check_exit_0_when_phase_done(tmp_path):
    _run("complete", str(tmp_path), "--phase", "capture")
    result = _run("check", str(tmp_path), "--phase", "capture", check=False)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["skip"] is True


def test_check_exit_1_when_phase_pending(tmp_path):
    result = _run("check", str(tmp_path), "--phase", "capture", check=False)
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["skip"] is False


def test_check_with_force_always_exits_1(tmp_path):
    _run("complete", str(tmp_path), "--phase", "capture")
    result = _run("check", str(tmp_path), "--phase", "capture", "--force", check=False)
    assert result.returncode == 1


# --- Pipeline-complete terminal state ---

def test_all_phases_complete_shows_ready_message(tmp_path):
    for phase in ("capture", "methodology", "testing", "standards"):
        _run("complete", str(tmp_path), "--phase", phase)
    report = _status(tmp_path)
    assert report["current_phase"] is None
    assert "complete" in report["next_action"].lower()


# --- Argparse contract ---

@pytest.mark.parametrize("bad_phase", ["setup", "build", "deploy", "CAPTURE"])
def test_rejects_unknown_phase_name(tmp_path, bad_phase):
    result = _run("complete", str(tmp_path), "--phase", bad_phase, check=False)
    assert result.returncode != 0
