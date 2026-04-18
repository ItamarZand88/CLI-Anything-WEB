"""Tests for capture-checkpoint.py — Phase-1 sub-step state.

Drives the script via subprocess. Verifies that save → restore → update
→ clear round-trip through a sensible pipeline resume shape.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
CHECKPOINT = SCRIPTS_DIR / "capture-checkpoint.py"


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [sys.executable, str(CHECKPOINT), *args],
        capture_output=True, text=True,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"capture-checkpoint.py failed: {result.stderr}")
    return result


def _restore(app_dir: Path) -> dict:
    return json.loads(_run("restore", str(app_dir)).stdout)


# --- Cold start ---

def test_restore_on_empty_app_reports_no_checkpoint(tmp_path):
    payload = _restore(tmp_path)
    assert payload["exists"] is False


# --- Save lifecycle ---

def test_save_creates_checkpoint_with_step(tmp_path):
    _run("save", str(tmp_path), "--step", "assessment",
         "--session", "sess1", "--url", "https://x.test")
    payload = _restore(tmp_path)
    assert payload["exists"] is True
    assert payload["step"] == "assessment"
    assert payload["session_name"] == "sess1"
    assert payload["url"] == "https://x.test"


def test_save_adds_trace_entry(tmp_path):
    _run("save", str(tmp_path), "--step", "tracing",
         "--trace-id", "trace-42", "--trace-purpose", "probe")
    payload = _restore(tmp_path)
    traces = payload["active_traces"]
    assert len(traces) == 1
    assert traces[0]["id"] == "trace-42"
    assert traces[0]["purpose"] == "probe"
    assert traces[0]["status"] == "active"


def test_save_preserves_prior_fields(tmp_path):
    _run("save", str(tmp_path), "--step", "assessment", "--session", "sess1")
    _run("save", str(tmp_path), "--step", "post-auth", "--auth-saved")
    payload = _restore(tmp_path)
    # session carries over even though the second save didn't pass --session
    assert payload["session_name"] == "sess1"
    assert payload["step"] == "post-auth"
    assert payload["auth_saved"] is True


# --- Update ---

def test_update_changes_specific_fields(tmp_path):
    _run("save", str(tmp_path), "--step", "tracing", "--trace-id", "t1")
    _run("update", str(tmp_path), "--step", "full-capture", "--auth-saved")
    payload = _restore(tmp_path)
    assert payload["step"] == "full-capture"
    assert payload["auth_saved"] is True


def test_update_errors_on_missing_checkpoint(tmp_path):
    result = _run("update", str(tmp_path), "--step", "assessment", check=False)
    assert result.returncode != 0
    assert "No checkpoint" in result.stderr


# --- Step sequencing / guidance ---

def test_restore_computes_step_index_and_next(tmp_path):
    _run("save", str(tmp_path), "--step", "assessment")
    payload = _restore(tmp_path)
    assert payload["step_index"] == 1  # 0=setup, 1=assessment
    assert payload["next_step"] == "post-auth"
    assert "completed_steps" in payload
    assert "assessment" in payload["completed_steps"]


def test_restore_complete_step_gives_ready_guidance(tmp_path):
    _run("save", str(tmp_path), "--step", "complete")
    payload = _restore(tmp_path)
    assert payload["next_step"] == "done"
    assert "Phase 2" in payload["guidance"]


# --- Clear ---

def test_clear_removes_checkpoint(tmp_path):
    _run("save", str(tmp_path), "--step", "assessment")
    _run("clear", str(tmp_path))
    payload = _restore(tmp_path)
    assert payload["exists"] is False


def test_clear_when_no_checkpoint_is_a_no_op(tmp_path):
    # Must not error when there's nothing to clear
    _run("clear", str(tmp_path))


# --- Assessment JSON ---

def test_save_accepts_assessment_json(tmp_path):
    _run("save", str(tmp_path), "--step", "assessment",
         "--assessment", '{"framework":"next","protection":"cloudflare"}')
    payload = _restore(tmp_path)
    assert payload["assessment"]["framework"] == "next"
    assert payload["assessment"]["protection"] == "cloudflare"


def test_save_ignores_malformed_assessment_json(tmp_path):
    # Should not crash; just warn and continue
    result = _run("save", str(tmp_path), "--step", "assessment",
                  "--assessment", "not json at all")
    payload = _restore(tmp_path)
    assert payload["exists"] is True
