import json
import os
import stat

from cli_web_devkit.canary import _check_envelope, run_canaries
from cli_web_devkit.paths import repo_root
from cli_web_devkit.registry import Registry

ROOT = repo_root()


def test_check_envelope_accepts_success():
    assert _check_envelope('{"success": true, "data": []}') is None


def test_check_envelope_rejects_error_envelope():
    problem = _check_envelope('{"error": true, "code": "NETWORK_ERROR", "message": "boom"}')
    assert problem is not None and "NETWORK_ERROR" in problem


def test_check_envelope_accepts_legacy_bare_array():
    # Pre-v2.1 fleet CLIs print bare JSON arrays/objects, not the envelope.
    assert _check_envelope("[1, 2, 3]") is None


def test_check_envelope_accepts_legacy_object_without_envelope():
    assert _check_envelope('{"items": [1, 2]}') is None


def test_check_envelope_rejects_false_success():
    problem = _check_envelope('{"success": false}')
    assert problem is not None and "not a success envelope" in problem


def test_check_envelope_tolerates_leading_noise():
    assert _check_envelope('Fetching...\n{"success": true, "data": []}') is None


def test_check_envelope_rejects_non_json():
    assert "not JSON" in _check_envelope("plain text")


def _fake_repo(tmp_path, monkeypatch, script_body: str):
    """Repo with one CLI whose binary is a stub shell script."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "cli-web-demo"
    stub.write_text(f"#!/bin/sh\n{script_body}\n")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    (tmp_path / "demo/agent-harness/cli_web/demo").mkdir(parents=True)
    (tmp_path / "registry.json").write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "clis": [
                    {
                        "name": "cli-web-demo",
                        "website": "demo.example",
                        "protocol": "REST",
                        "auth": "none",
                        "directory": "demo/agent-harness",
                        "namespace": "cli_web.demo",
                        "commands": ["things list"],
                        "install": "pip install -e demo/agent-harness",
                        "canary": [["things", "list", "--json"]],
                    }
                ],
            }
        )
    )
    return tmp_path


def test_run_canaries_pass(tmp_path, monkeypatch):
    root = _fake_repo(tmp_path, monkeypatch, 'echo \'{"success": true, "data": [1]}\'')
    report = run_canaries(root)
    assert report.to_dict()["ok"] is True
    assert report.results[0].ok


def test_run_canaries_fail_on_error_envelope(tmp_path, monkeypatch):
    root = _fake_repo(
        tmp_path, monkeypatch, 'echo \'{"error": true, "code": "SERVER_ERROR", "message": "x"}\''
    )
    report = run_canaries(root)
    assert report.failures and "SERVER_ERROR" in report.failures[0].detail


def test_run_canaries_fail_on_nonzero_exit(tmp_path, monkeypatch):
    root = _fake_repo(tmp_path, monkeypatch, "echo broken >&2; exit 3")
    report = run_canaries(root)
    assert report.failures and "exit 3" in report.failures[0].detail


def test_run_canaries_missing_binary(tmp_path, monkeypatch):
    root = _fake_repo(tmp_path, monkeypatch, "echo unused")
    (tmp_path / "bin/cli-web-demo").unlink()
    report = run_canaries(root)
    assert report.failures and "not installed" in report.failures[0].detail


def test_real_registry_canaries_are_no_auth_and_json():
    """Canary commands must be registered only on no-auth CLIs and use --json."""
    reg = Registry.load(ROOT / "registry.json")
    with_canary = [e for e in reg.clis if e.canary]
    assert len(with_canary) >= 10
    for entry in with_canary:
        assert entry.auth.startswith(("none", "cookie (optional")), (
            f"{entry.name}: canary on auth-required CLI"
        )
        for argv in entry.canary:
            assert "--json" in argv, f"{entry.name}: canary without --json: {argv}"
