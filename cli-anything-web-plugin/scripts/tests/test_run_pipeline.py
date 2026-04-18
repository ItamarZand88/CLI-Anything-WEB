"""Tests for run-pipeline.py orchestrator."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
ORCH = SCRIPTS_DIR / "run-pipeline.py"
PHASE_STATE = SCRIPTS_DIR / "phase-state.py"


def test_status_reports_all_phases_pending_for_new_app(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ORCH), "status", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["current_phase"] == "capture"
    assert report["phases"]["capture"]["status"] == "pending"
    assert report["next_action"]["skill"] == "capture"


def test_status_advances_after_capture_done(tmp_path):
    subprocess.check_call([
        sys.executable, str(PHASE_STATE), "complete", str(tmp_path),
        "--phase", "capture", "--output", "/tmp/foo.json",
    ])
    result = subprocess.run(
        [sys.executable, str(ORCH), "status", str(tmp_path)],
        capture_output=True, text=True,
    )
    report = json.loads(result.stdout)
    assert report["current_phase"] == "methodology"
    assert report["phases"]["capture"]["status"] == "done"
    assert report["next_action"]["skill"] == "methodology"


def test_status_complete_when_all_phases_done(tmp_path):
    for phase in ("capture", "methodology", "testing", "standards"):
        subprocess.check_call([
            sys.executable, str(PHASE_STATE), "complete", str(tmp_path),
            "--phase", phase,
        ])
    result = subprocess.run(
        [sys.executable, str(ORCH), "status", str(tmp_path)],
        capture_output=True, text=True,
    )
    report = json.loads(result.stdout)
    assert report["current_phase"] is None
    assert "complete" in report["next_action"]["summary"].lower()


def test_help_lists_subcommands():
    result = subprocess.run(
        [sys.executable, str(ORCH), "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "status" in result.stdout
    assert "parse" in result.stdout
    assert "validate" in result.stdout
