"""Tests for validate-checklist.py — the 65-point quality gate.

Two test styles:
1. End-to-end via subprocess against scaffolded CLIs (realistic).
2. Synthetic minimal harnesses that trigger specific checks in isolation
   (catches regressions on individual check IDs).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
VALIDATE = SCRIPTS_DIR / "validate-checklist.py"
SCAFFOLD = SCRIPTS_DIR / "scaffold-cli.py"


def _validate(harness: Path, app_name: str, auth_type: str = "cookie") -> dict:
    """Run the validator in --json mode and return the parsed report."""
    result = subprocess.run(
        [
            sys.executable, str(VALIDATE), str(harness),
            "--app-name", app_name,
            "--auth-type", auth_type,
            "--json",
        ],
        capture_output=True, text=True,
    )
    # Non-zero exit is normal when there are failures — we parse anyway.
    assert result.stdout, f"no stdout; stderr: {result.stderr}"
    return json.loads(result.stdout)


def _check(report: dict, check_id: str) -> dict:
    """Return the single check entry matching check_id."""
    for entry in report["checks"]:
        if entry["id"] == check_id:
            return entry
    raise AssertionError(f"check id {check_id!r} not found in report")


# --- Fixture: freshly scaffolded CLI (incomplete but structurally valid) ---

@pytest.fixture(scope="module")
def scaffolded_harness(tmp_path_factory):
    harness = tmp_path_factory.mktemp("harness") / "agent-harness"
    subprocess.check_call([
        sys.executable, str(SCAFFOLD), str(harness),
        "--app-name", "vcapp",
        "--protocol", "rest",
        "--http-client", "httpx",
        "--auth-type", "cookie",
        "--resources", "items",
    ])
    return harness


def test_scaffolded_cli_has_correct_directory_structure(scaffolded_harness):
    """Check 1.1, 1.3, 1.4, 1.5 — structural correctness of scaffold output."""
    report = _validate(scaffolded_harness, "vcapp")
    assert _check(report, "1.1")["status"] == "pass"  # cli_web/<app>/ exists
    assert _check(report, "1.3")["status"] == "pass"  # NO cli_web/__init__.py
    assert _check(report, "1.4")["status"] == "pass"  # <app>/__init__.py present
    assert _check(report, "1.5")["status"] == "pass"  # core/commands/utils/tests all there


def test_scaffolded_cli_has_required_files(scaffolded_harness):
    """Check 2.x — required files from scaffold."""
    report = _validate(scaffolded_harness, "vcapp")
    assert _check(report, "2.1")["status"] == "pass"  # <app>_cli.py
    assert _check(report, "2.2")["status"] == "pass"  # __main__.py
    assert _check(report, "2.3")["status"] == "pass"  # core/client.py
    assert _check(report, "2.4")["status"] == "pass"  # core/exceptions.py
    assert _check(report, "2.5")["status"] == "pass"  # core/auth.py (auth_type=cookie)
    assert _check(report, "2.8")["status"] == "pass"  # utils/repl_skin.py
    assert _check(report, "2.9")["status"] == "pass"  # utils/output.py


def test_scaffolded_auth_none_skips_auth_file_check(tmp_path):
    """For --auth-type none, check 2.5 should report N/A, not FAIL."""
    harness = tmp_path / "no-auth"
    subprocess.check_call([
        sys.executable, str(SCAFFOLD), str(harness),
        "--app-name", "noauth",
        "--protocol", "rest",
        "--http-client", "httpx",
        "--auth-type", "none",
        "--resources", "x",
    ])
    report = _validate(harness, "noauth", auth_type="none")
    assert _check(report, "2.5")["status"] == "na"


def test_json_output_includes_summary_counts(scaffolded_harness):
    report = _validate(scaffolded_harness, "vcapp")
    assert "summary" in report
    for key in ("pass", "fail", "skip", "na"):
        assert key in report["summary"]
        assert isinstance(report["summary"][key], int)
    # At least one pass and some meaningful volume of checks
    assert report["summary"]["pass"] > 10
    assert len(report["checks"]) >= 40


def test_validator_reports_app_name_and_auth_type(scaffolded_harness):
    report = _validate(scaffolded_harness, "vcapp")
    assert report["app_name"] == "vcapp"
    assert report["auth_type"] == "cookie"


# --- Synthetic failure detection ---

def _make_minimal_harness(tmp_path: Path, app_name: str = "tapp",
                          auth_type: str = "cookie") -> Path:
    """Create a minimal valid harness so we can mutate it per test."""
    harness = tmp_path / "harness"
    subprocess.check_call([
        sys.executable, str(SCAFFOLD), str(harness),
        "--app-name", app_name,
        "--protocol", "rest",
        "--http-client", "httpx",
        "--auth-type", auth_type,
        "--resources", "items",
    ])
    return harness


def test_detects_missing_sub_package_init(tmp_path):
    """Check 1.4 must fail when <app>/__init__.py is deleted."""
    harness = _make_minimal_harness(tmp_path)
    init = harness / "cli_web" / "tapp" / "__init__.py"
    init.unlink()
    report = _validate(harness, "tapp")
    assert _check(report, "1.4")["status"] == "fail"


def test_detects_stray_namespace_init(tmp_path):
    """Check 1.3 must fail when cli_web/__init__.py exists (breaks namespace pkg)."""
    harness = _make_minimal_harness(tmp_path)
    (harness / "cli_web" / "__init__.py").write_text("# oops\n")
    report = _validate(harness, "tapp")
    assert _check(report, "1.3")["status"] == "fail"


def test_detects_missing_required_directory(tmp_path):
    """Check 1.5 — removing tests/ must fail the all-dirs check."""
    harness = _make_minimal_harness(tmp_path)
    tests = harness / "cli_web" / "tapp" / "tests"
    for child in tests.iterdir():
        child.unlink()
    tests.rmdir()
    report = _validate(harness, "tapp")
    assert _check(report, "1.5")["status"] == "fail"


def test_detects_missing_setup_py(tmp_path):
    """Check 1.6 fails when setup.py is missing."""
    harness = _make_minimal_harness(tmp_path)
    (harness / "setup.py").unlink()
    report = _validate(harness, "tapp")
    assert _check(report, "1.6")["status"] == "fail"


def test_detects_missing_core_client(tmp_path):
    """Check 2.3 fails when core/client.py is missing."""
    harness = _make_minimal_harness(tmp_path)
    (harness / "cli_web" / "tapp" / "core" / "client.py").unlink()
    report = _validate(harness, "tapp")
    assert _check(report, "2.3")["status"] == "fail"


def test_detects_missing_auth_when_required(tmp_path):
    """Check 2.5 fails when auth_type != none but auth.py is absent."""
    harness = _make_minimal_harness(tmp_path, auth_type="cookie")
    (harness / "cli_web" / "tapp" / "core" / "auth.py").unlink()
    report = _validate(harness, "tapp", auth_type="cookie")
    assert _check(report, "2.5")["status"] == "fail"


# --- Error handling / argparse ---

def test_rejects_non_existent_harness_dir(tmp_path):
    result = subprocess.run(
        [
            sys.executable, str(VALIDATE), str(tmp_path / "nonexistent"),
            "--app-name", "x", "--json",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "not a directory" in result.stderr


def test_rejects_unknown_auth_type(scaffolded_harness):
    result = subprocess.run(
        [
            sys.executable, str(VALIDATE), str(scaffolded_harness),
            "--app-name", "vcapp", "--auth-type", "oauth",
            "--json",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode != 0


def test_run_without_app_name_errors(tmp_path):
    harness = _make_minimal_harness(tmp_path)
    result = subprocess.run(
        [sys.executable, str(VALIDATE), str(harness), "--json"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
