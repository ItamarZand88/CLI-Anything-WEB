"""End-to-end tests — subprocess invocation of the installed CLI.

Auth-dependent tests FAIL (do not skip) when credentials are missing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


# ── Helper ─────────────────────────────────────────────────────────────

def _resolve_cli(name: str = "cli-web-notebooklm") -> list[str]:
    """Resolve the CLI entry point for subprocess invocation.

    Tries the installed console_script first, then falls back
    to `python -m cli_web.notebooklm`.
    """
    exe = shutil.which(name)
    if exe:
        return [exe]
    return [sys.executable, "-m", "cli_web.notebooklm"]


CLI = _resolve_cli()


def _run(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess:
    """Run the CLI with given arguments."""
    return subprocess.run(
        [*CLI, *args],
        capture_output=True,
        text=True,
        timeout=30,
        input=input_text,
    )


def _has_auth() -> bool:
    """Check if auth cookies are configured."""
    auth_file = Path.home() / ".config" / "cli-web-notebooklm" / "auth.json"
    if not auth_file.exists():
        return False
    try:
        data = json.loads(auth_file.read_text())
        return bool(data.get("cookies"))
    except Exception:
        return False


# ── Basic CLI tests ────────────────────────────────────────────────────

def test_help():
    result = _run("--help")
    assert result.returncode == 0
    assert "notebooks" in result.stdout
    assert "sources" in result.stdout
    assert "notes" in result.stdout
    assert "chat" in result.stdout
    assert "artifacts" in result.stdout
    assert "auth" in result.stdout


def test_version():
    result = _run("--version")
    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_auth_help():
    result = _run("auth", "--help")
    assert result.returncode == 0
    assert "login" in result.stdout
    assert "status" in result.stdout
    assert "export" in result.stdout


def test_notebooks_help():
    result = _run("notebooks", "--help")
    assert result.returncode == 0
    assert "list" in result.stdout
    assert "get" in result.stdout
    assert "create" in result.stdout
    assert "delete" in result.stdout
    assert "rename" in result.stdout


# ── Auth status (no auth) ─────────────────────────────────────────────

def test_auth_status_no_cookies():
    """Without auth, 'auth status' must fail (exit non-zero)."""
    if _has_auth():
        pytest.fail(
            "Auth is configured — this test validates the no-auth path. "
            "Remove ~/.config/cli-web-notebooklm/auth.json to test properly."
        )
    result = _run("auth", "status")
    assert result.returncode != 0
    # Response body must contain meaningful error text
    combined = result.stdout + result.stderr
    assert "auth" in combined.lower() or "cookie" in combined.lower() or "not found" in combined.lower()


# ── Live tests (require auth) ─────────────────────────────────────────

def test_notebooks_list_json():
    """List notebooks as JSON. FAILS if auth is not configured."""
    if not _has_auth():
        pytest.fail(
            "Auth not configured. Export cookies to "
            "~/.config/cli-web-notebooklm/auth.json to run live tests."
        )
    result = _run("notebooks", "list", "--json")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert isinstance(data, list)


def test_notebooks_list_table():
    """List notebooks as table. FAILS if auth is not configured."""
    if not _has_auth():
        pytest.fail(
            "Auth not configured. Export cookies to "
            "~/.config/cli-web-notebooklm/auth.json to run live tests."
        )
    result = _run("notebooks", "list")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    # Should contain either table headers or "No notebooks" message
    assert "ID" in result.stdout or "No notebooks" in result.stdout


def test_chat_query_json():
    """Chat query as JSON. FAILS if auth is not configured."""
    if not _has_auth():
        pytest.fail(
            "Auth not configured. Export cookies to "
            "~/.config/cli-web-notebooklm/auth.json to run live tests."
        )
    # This test needs a real notebook_id — we'll fetch one first
    list_result = _run("notebooks", "list", "--json")
    assert list_result.returncode == 0, f"stderr: {list_result.stderr}"
    notebooks = json.loads(list_result.stdout)
    if not notebooks:
        pytest.fail("No notebooks available for chat test.")

    nb_id = notebooks[0]["id"]
    result = _run("chat", "query", nb_id, "What is this notebook about?", "--json")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert "question" in data
    assert "response" in data
    assert isinstance(data["response"], str)
