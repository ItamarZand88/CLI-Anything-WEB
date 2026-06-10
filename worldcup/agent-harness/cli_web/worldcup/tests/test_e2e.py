"""End-to-end tests for cli-web-worldcup.

Live-API tests hit the real service and MUST FAIL (never skip) on errors —
including missing auth (see HARNESS.md "Tests FAIL on missing auth").

CLI subprocess tests cover the fully installed `cli-web-worldcup` entry
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
from cli_web.worldcup.core.client import WorldcupClient

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
    return _resolve_cli("cli-web-worldcup")


@pytest.fixture(scope="module")
def client():
    with WorldcupClient() as c:
        yield c


# ─── Live API (Python layer) ────────────────────────────────────────────────


class TestLiveAPI:
    """Live ESPN reads (no auth, no key needed)."""

    def test_teams_returns_nations(self, client):
        raw = client.teams()
        teams = raw["sports"][0]["leagues"][0]["teams"]
        assert len(teams) >= 32  # 48 for 2026; guards against an empty/changed feed
        assert teams[0]["team"]["displayName"]

    def test_scoreboard_returns_fixtures(self, client):
        raw = client.scoreboard(dates="20260611-20260719")
        assert len(raw.get("events", [])) >= 1
        assert raw["events"][0]["competitions"][0]["competitors"]

    def test_standings_has_groups(self, client):
        raw = client.standings()
        assert len(raw.get("children", [])) >= 1
        assert raw["children"][0]["standings"]["entries"]

    def test_roster_returns_players(self, client):
        # Mexico (203) — a confirmed 2026 qualifier with a published squad.
        raw = client.roster("203")
        assert len(raw.get("athletes", [])) >= 1
        assert raw["athletes"][0].get("fullName")


# ─── CLI subprocess tests ───────────────────────────────────────────────────


class TestCLISubprocess:
    def test_help_loads(self, cli_cmd):
        result = _run(cli_cmd, "--help")
        assert result.returncode == 0
        assert "Usage" in result.stdout
        for group in ("fixtures", "teams", "players", "standings", "odds"):
            assert group in result.stdout

    def test_version_works(self, cli_cmd):
        result = _run(cli_cmd, "--version")
        assert result.returncode == 0
        assert "0.1.0" in result.stdout

    def test_repl_exits_cleanly(self, cli_cmd):
        """REPL is the default mode; `exit` must terminate with code 0."""
        result = _run(cli_cmd, stdin="exit\n", timeout=30.0)
        assert result.returncode == 0

    def test_usage_error_exits_2(self, cli_cmd):
        """Exit-code contract (CONVENTIONS.md §Exit Codes): usage errors -> 2."""
        result = _run(cli_cmd, "definitely-not-a-command")
        assert result.returncode == 2

    def test_teams_list_json(self, cli_cmd):
        result = _run(cli_cmd, "--json", "teams", "list")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = _parse_json(result)
        assert data["success"] is True
        assert len(data["data"]) >= 32
        assert data["data"][0]["name"] and data["data"][0]["abbreviation"]

    def test_fixtures_list_json(self, cli_cmd):
        result = _run(cli_cmd, "--json", "fixtures", "list", "--limit", "5")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = _parse_json(result)
        assert data["success"] is True and len(data["data"]) <= 5
        if data["data"]:
            assert {"home", "away", "status"} <= set(data["data"][0])

    def test_fixtures_jsonl(self, cli_cmd):
        result = _run(cli_cmd, "fixtures", "list", "--limit", "3", "--jsonl")
        assert result.returncode == 0
        lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
        assert all(json.loads(ln)["home"] for ln in lines)

    def test_standings_json(self, cli_cmd):
        result = _run(cli_cmd, "--json", "standings", "list", "--group", "A")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = _parse_json(result)
        assert data["success"] is True
        assert all(r["group"].endswith("A") for r in data["data"])

    def test_odds_without_key_exits_3(self, cli_cmd):
        """Odds need an API key — missing key is AuthError -> exit 3."""
        env = {k: v for k, v in os.environ.items() if k != "CLI_WEB_WORLDCUP_ODDS_API_KEY"}
        result = subprocess.run(
            [*cli_cmd, "--json", "odds", "list"],
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
        assert result.returncode == 3
        data = json.loads(result.stdout)
        assert data["error"] is True and data["code"] == "AUTH_EXPIRED"

    def test_team_not_found_exits_4(self, cli_cmd):
        result = _run(cli_cmd, "--json", "teams", "get", "Narnia")
        assert result.returncode == 4
        data = _parse_json(result)
        assert data["error"] is True and data["code"] == "NOT_FOUND"
