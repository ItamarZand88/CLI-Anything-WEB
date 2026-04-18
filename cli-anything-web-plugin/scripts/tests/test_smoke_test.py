"""Tests for smoke-test.py — post-install CLI validation.

Focuses on the pure helpers (check_json_valid, check_leaks,
_parse_commands_from_help) and on SmokeTest's behavior against a
synthetic stub CLI. Doesn't require any generated CLI to be installed.
"""
from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
SMOKE = SCRIPTS_DIR / "smoke-test.py"


@pytest.fixture(scope="module")
def smoke_mod() -> ModuleType:
    spec = importlib.util.spec_from_file_location("smoke_test", SMOKE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["smoke_test"] = mod
    spec.loader.exec_module(mod)
    return mod


# --- Pure helpers ---

def test_check_json_valid_accepts_valid_json(smoke_mod):
    ok, msg = smoke_mod.check_json_valid('{"a": 1}')
    assert ok is True
    assert msg == ""


def test_check_json_valid_rejects_malformed(smoke_mod):
    ok, msg = smoke_mod.check_json_valid('{bad')
    assert ok is False
    assert "Invalid JSON" in msg


def test_check_json_valid_rejects_empty(smoke_mod):
    ok, msg = smoke_mod.check_json_valid("")
    assert ok is False
    assert "Empty" in msg


def test_check_json_valid_strips_whitespace(smoke_mod):
    ok, _ = smoke_mod.check_json_valid('   \n{"ok": true}\n  ')
    assert ok is True


# --- Leak detection ---

def test_check_leaks_detects_batchexecute_wrb(smoke_mod):
    # Actual leak: raw batchexecute array bleeds through as-is, unescaped.
    leaks = smoke_mod.check_leaks('[["wrb.fr","xyz",""]]')
    assert any("wrb.fr" in leak for leak in leaks)


def test_check_leaks_detects_csrf_token_leak(smoke_mod):
    leaks = smoke_mod.check_leaks('{"SNlM0e": "abc123"}')
    assert any("CSRF" in leak for leak in leaks)


def test_check_leaks_detects_session_id(smoke_mod):
    leaks = smoke_mod.check_leaks('{"FdrFJe": "-123"}')
    assert any("Session ID" in leak for leak in leaks)


def test_check_leaks_clean_output(smoke_mod):
    leaks = smoke_mod.check_leaks('{"success": true, "data": {"items": [1, 2, 3]}}')
    assert leaks == []


def test_check_leaks_returns_multiple_when_present(smoke_mod):
    mixed = '"wrb.fr" and "SNlM0e" in one string'
    leaks = smoke_mod.check_leaks(mixed)
    # Should flag both
    assert len(leaks) >= 2


# --- Help parsing ---

def test_parse_commands_extracts_click_subcommands(smoke_mod):
    help_output = """Usage: cli-web-foo [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  feed       Browse posts
  search     Search items
  auth       Auth management
"""
    names = smoke_mod.SmokeTest._parse_commands_from_help(help_output)
    assert names == ["feed", "search", "auth"]


def test_parse_commands_empty_on_flat_cli(smoke_mod):
    names = smoke_mod.SmokeTest._parse_commands_from_help("Usage: foo\n  --help\n")
    assert names == []


def test_parse_commands_stops_at_blank_line(smoke_mod):
    help_output = """Commands:
  first
  second

  not_a_command
"""
    names = smoke_mod.SmokeTest._parse_commands_from_help(help_output)
    assert names == ["first", "second"]


# --- run_cli error paths ---

def test_run_cli_reports_missing_binary(smoke_mod):
    code, out, err = smoke_mod.run_cli(["/nonexistent/cli-web-xxxxx"], ["--help"])
    assert code == -2
    assert "not found" in err


def test_run_cli_timeout_path(smoke_mod, tmp_path):
    """A deliberately slow script should trip the timeout branch."""
    slow = tmp_path / "slow.py"
    slow.write_text("import time; time.sleep(30)\n")
    code, out, err = smoke_mod.run_cli([sys.executable, str(slow)], [], timeout=1)
    assert code == -1
    assert err == "TIMEOUT"


def test_run_cli_captures_stdout_stderr(smoke_mod, tmp_path):
    script = tmp_path / "echo.py"
    script.write_text(
        "import sys; print('hello-stdout'); print('warn', file=sys.stderr)\n"
    )
    code, out, err = smoke_mod.run_cli([sys.executable, str(script)], [])
    assert code == 0
    assert "hello-stdout" in out
    assert "warn" in err


# --- SmokeTest class behavior (using a fake CLI) ---

@pytest.fixture
def fake_cli(tmp_path):
    """Create a tiny executable script that mimics a Click CLI with
    --help, --version, and one JSON-returning subcommand."""
    cli = tmp_path / "cli-web-fake"
    cli.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "args = sys.argv[1:]\n"
        "if args == ['--help']:\n"
        "    print('Usage: cli-web-fake [OPTIONS] COMMAND')\n"
        "    print('Commands:')\n"
        "    print('  hello    Say hi')\n"
        "    sys.exit(0)\n"
        "if args == ['--version']:\n"
        "    print('cli-web-fake 0.1.0')\n"
        "    sys.exit(0)\n"
        "if args == ['hello', '--json']:\n"
        "    print('{\"success\": true, \"data\": \"hi\"}')\n"
        "    sys.exit(0)\n"
        "sys.exit(2)\n"
    )
    cli.chmod(cli.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return cli


def test_smoke_test_resolves_cli_via_path(smoke_mod, fake_cli, monkeypatch):
    """resolve_cli() should find the fake CLI via shutil.which when it's on PATH."""
    monkeypatch.setenv("PATH", f"{fake_cli.parent}{os.pathsep}{os.environ.get('PATH', '')}")
    st = smoke_mod.SmokeTest("cli-web-fake", auth_type="none", skip_auth=True)
    assert st.resolve_cli() is True
    assert st.cli_cmd[0].endswith("cli-web-fake")


def test_smoke_test_check_help_marks_pass(smoke_mod, fake_cli, monkeypatch):
    monkeypatch.setenv("PATH", f"{fake_cli.parent}{os.pathsep}{os.environ.get('PATH', '')}")
    st = smoke_mod.SmokeTest("cli-web-fake", auth_type="none", skip_auth=True)
    assert st.resolve_cli()
    st.check_help()
    assert any(r["name"] == "--help responds" and r["status"] == "pass" for r in st.results)


def test_smoke_test_check_version_marks_pass(smoke_mod, fake_cli, monkeypatch):
    monkeypatch.setenv("PATH", f"{fake_cli.parent}{os.pathsep}{os.environ.get('PATH', '')}")
    st = smoke_mod.SmokeTest("cli-web-fake", auth_type="none", skip_auth=True)
    assert st.resolve_cli()
    st.check_version()
    assert any(r["name"] == "--version responds" and r["status"] == "pass" for r in st.results)


def test_smoke_test_discover_commands_finds_subcommand(smoke_mod, fake_cli, monkeypatch):
    monkeypatch.setenv("PATH", f"{fake_cli.parent}{os.pathsep}{os.environ.get('PATH', '')}")
    st = smoke_mod.SmokeTest("cli-web-fake", auth_type="none", skip_auth=True)
    assert st.resolve_cli()
    st.check_help()
    assert "hello" in st.discover_commands()


def test_smoke_test_missing_cli_reports_fail(smoke_mod):
    st = smoke_mod.SmokeTest("cli-web-does-not-exist-anywhere", auth_type="none", skip_auth=True)
    assert st.resolve_cli() is False
    assert any(r["status"] == "fail" for r in st.results)
