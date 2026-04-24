"""Tests for validate-capture.py — Phase-1 output validation."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
VALIDATE = SCRIPTS_DIR / "validate-capture.py"


def _write_capture(app_dir: Path, entries: list[dict], analysis: dict | None = None) -> None:
    capture_dir = app_dir / "traffic-capture"
    capture_dir.mkdir(parents=True, exist_ok=True)
    (capture_dir / "raw-traffic.json").write_text(json.dumps(entries))
    if analysis is not None:
        (capture_dir / "traffic-analysis.json").write_text(json.dumps(analysis))


def _entry(
    url: str = "https://api.example.com/v1/items",
    method: str = "GET",
    status: int = 200,
    mime: str = "application/json",
    body: object = None,
) -> dict:
    return {
        "url": url,
        "method": method,
        "status": status,
        "mime_type": mime,
        "response_body": body if body is not None else {"ok": True},
    }


def _run(app_dir: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATE), str(app_dir), "--json", *extra],
        capture_output=True,
        text=True,
    )


# --- Happy paths ---

def test_passes_on_healthy_capture(tmp_path):
    entries = [
        _entry(f"https://api.example.com/v1/items/{i}")
        for i in range(20)
    ] + [_entry(method="POST", url="https://api.example.com/v1/items")]
    analysis = {"protocol": {"protocol": "rest", "confidence": 90}}
    _write_capture(tmp_path, entries, analysis)

    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout
    report = json.loads(result.stdout)
    assert report["overall"] == "pass"


def test_read_only_flag_skips_write_check(tmp_path):
    entries = [_entry(f"https://api.example.com/v1/items/{i}") for i in range(20)]
    analysis = {"protocol": {"protocol": "rest", "confidence": 90}}
    _write_capture(tmp_path, entries, analysis)

    result = _run(tmp_path, "--read-only")
    assert result.returncode == 0
    report = json.loads(result.stdout)
    write = next(c for c in report["checks"] if c["name"] == "write_ops")
    assert write["status"] == "pass"


# --- Blocking failures ---

def test_fails_on_empty_capture(tmp_path):
    _write_capture(tmp_path, [])
    result = _run(tmp_path)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["overall"] == "fail"
    entry_check = next(c for c in report["checks"] if c["name"] == "entry_count")
    assert entry_check["status"] == "fail"


def test_fails_on_sparse_capture(tmp_path):
    entries = [_entry() for _ in range(5)]
    _write_capture(tmp_path, entries, {"protocol": {"protocol": "rest", "confidence": 80}})
    result = _run(tmp_path)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    entry_check = next(c for c in report["checks"] if c["name"] == "entry_count")
    assert entry_check["status"] == "fail"


def test_fails_on_unknown_protocol(tmp_path):
    entries = [_entry(f"https://api.example.com/v1/items/{i}") for i in range(20)]
    entries.append(_entry(method="POST"))
    _write_capture(tmp_path, entries, {"protocol": {"protocol": "unknown", "confidence": 0}})
    result = _run(tmp_path)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(c["name"] == "protocol" and c["status"] == "fail" for c in report["checks"])


def test_fails_on_missing_write_ops(tmp_path):
    entries = [_entry(f"https://api.example.com/v1/items/{i}") for i in range(20)]
    _write_capture(tmp_path, entries, {"protocol": {"protocol": "rest", "confidence": 90}})
    result = _run(tmp_path)  # no --read-only
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(c["name"] == "write_ops" and c["status"] == "fail" for c in report["checks"])


def test_fails_on_dominant_errors(tmp_path):
    entries = [_entry(status=401) for _ in range(20)]
    entries.append(_entry(method="POST", status=401))
    _write_capture(tmp_path, entries, {"protocol": {"protocol": "rest", "confidence": 80}})
    result = _run(tmp_path)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(c["name"] == "error_rate" and c["status"] == "fail" for c in report["checks"])


def test_fails_on_low_endpoint_diversity(tmp_path):
    # 20 hits against a single URL — passes count but flat
    entries = [_entry() for _ in range(20)] + [_entry(method="POST")]
    _write_capture(tmp_path, entries, {"protocol": {"protocol": "rest", "confidence": 90}})
    result = _run(tmp_path)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(
        c["name"] == "endpoint_diversity" and c["status"] == "fail"
        for c in report["checks"]
    )


# --- Missing inputs ---

def test_exit_code_2_when_raw_traffic_missing(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 2
    assert "not found" in result.stderr


def test_handles_missing_analysis_gracefully(tmp_path):
    """raw-traffic.json present, traffic-analysis.json missing — should still run."""
    entries = [_entry(f"https://api.example.com/v1/items/{i}") for i in range(20)]
    entries.append(_entry(method="POST"))
    capture_dir = tmp_path / "traffic-capture"
    capture_dir.mkdir(parents=True)
    (capture_dir / "raw-traffic.json").write_text(json.dumps(entries))

    result = _run(tmp_path)
    # Protocol check will fail because analysis is empty
    assert result.returncode == 1
    report = json.loads(result.stdout)
    proto = next(c for c in report["checks"] if c["name"] == "protocol")
    assert proto["status"] == "fail"
