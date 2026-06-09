"""End-to-end tests for cli-web-${app_name}.

Live-API tests hit the real service and MUST FAIL (never skip) on errors —
including missing auth (see HARNESS.md "Tests FAIL on missing auth").

CLI subprocess tests cover the fully installed `cli-web-${app_name}` entry
point. Set CLI_WEB_FORCE_INSTALLED=1 to require the installed binary
(instead of the `python -m` fallback).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest
from cli_web.${app_name_underscore}.core.client import ${AppName}Client

# ─── Canonical subprocess fixtures (_resolve_cli / _run / _parse_json) ──────


def _resolve_cli(cli_name: str) -> list[str]:
    """Locate the installed CLI binary, or fall back to `python -m ...`.

    If CLI_WEB_FORCE_INSTALLED=1 is set, raise if the binary is not on PATH.
    """
    forced = os.environ.get("CLI_WEB_FORCE_INSTALLED") == "1"
    path = shutil.which(cli_name)
    if path:
        return [path]
    if forced:
        raise RuntimeError(
            f"CLI_WEB_FORCE_INSTALLED=1 but '{cli_name}' not found on PATH. "
            "Run `pip install -e .` in agent-harness/ before running subprocess tests."
        )
    # Fallback: module invocation
    module = cli_name.replace("cli-web-", "cli_web.").replace("-", "_")
    return [sys.executable, "-m", module]


def _run(
    cli_cmd: list[str],
    *args: str,
    timeout: float = 60.0,
    stdin: str | None = None,
) -> subprocess.CompletedProcess:
    """Run the CLI with the given args and return the completed process."""
    return subprocess.run(
        [*cli_cmd, *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _parse_json(result: subprocess.CompletedProcess) -> dict:
    """Parse CLI stdout as JSON, failing loudly with stdout/stderr context."""
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"CLI output is not valid JSON ({exc}).\n"
            f"stdout: {result.stdout[:500]!r}\n"
            f"stderr: {result.stderr[:500]!r}"
        )


@pytest.fixture(scope="module")
def cli_cmd():
    return _resolve_cli("cli-web-${app_name}")


@pytest.fixture(scope="module")
def client():
    with ${AppName}Client() as c:
        yield c


# ─── Live API (Python layer) ────────────────────────────────────────────────


class TestLiveAPI:
    """FILL_IN: live-API tests against the client layer.

    Example:

        def test_list_items_returns_rows(self, client):
            rows = client.list_items()
            assert len(rows) >= 1
            assert rows[0]["id"]
    """

    # FILL_IN: add at least one live test per client endpoint method.


# ─── CLI subprocess tests ───────────────────────────────────────────────────


class TestCLISubprocess:
    def test_help_loads(self, cli_cmd):
        result = _run(cli_cmd, "--help")
        assert result.returncode == 0
        assert "Usage" in result.stdout
        # FILL_IN: assert each registered command group appears in --help

    def test_version_works(self, cli_cmd):
        result = _run(cli_cmd, "--version")
        assert result.returncode == 0
        assert "0.1.0" in result.stdout

    def test_repl_exits_cleanly(self, cli_cmd):
        """REPL is the default mode; `exit` must terminate with code 0."""
        result = _run(cli_cmd, stdin="exit\n", timeout=30.0)
        assert result.returncode == 0

    # FILL_IN: subprocess tests for real commands with --json, e.g.:
    #
    # def test_items_list_json(self, cli_cmd):
    #     result = _run(cli_cmd, "--json", "items", "list")
    #     assert result.returncode == 0, f"stderr: {result.stderr}"
    #     data = _parse_json(result)
    #     assert data["success"] is True
    #     assert len(data["data"]) >= 1
{%- if auth_type != "none" %}
    #
    # Auth-required commands: tests MUST FAIL (not skip) when auth.json is
    # missing — never add pytest.skip for missing credentials.
{%- endif %}
