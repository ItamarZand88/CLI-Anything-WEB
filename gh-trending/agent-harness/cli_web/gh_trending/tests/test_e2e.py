"""E2E and subprocess tests for cli-web-gh-trending (live network calls)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest

from cli_web.gh_trending.core.client import GitHubClient


# ─── subprocess resolver ──────────────────────────────────────────────────────

def _resolve_cli(name: str) -> list[str]:
    """Resolve installed CLI command; falls back to python -m for dev."""
    force = os.environ.get("CLI_WEB_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = "cli_web.gh_trending.gh_trending_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


# ─── Live E2E tests ───────────────────────────────────────────────────────────
# GitHub Trending is public — no auth required.

class TestTrendingReposLive:
    def test_repos_today(self):
        client = GitHubClient()
        repos = client.get_trending_repos()
        assert isinstance(repos, list), "Expected list of repos"
        assert len(repos) >= 1, "Expected at least 1 trending repo"
        first = repos[0]
        assert "/" in first.full_name, f"Expected 'owner/name' format, got: {first.full_name}"
        assert first.stars > 0, f"Expected stars > 0, got: {first.stars}"
        assert first.stars_today >= 0
        assert first.rank == 1
        assert first.url.startswith("https://github.com/")
        print(f"[verify] Top repo today: {first.full_name} ({first.stars_today} stars today)")

    def test_repos_python_weekly(self):
        client = GitHubClient()
        repos = client.get_trending_repos(language="python", since="weekly")
        assert isinstance(repos, list)
        assert len(repos) >= 1
        first = repos[0]
        assert first.full_name, "Expected non-empty full_name"
        assert first.stars > 0
        print(f"[verify] Top Python repo (weekly): {first.full_name} ({first.stars:,} stars)")

    def test_repos_monthly(self):
        client = GitHubClient()
        repos = client.get_trending_repos(since="monthly")
        assert isinstance(repos, list)
        assert len(repos) >= 1
        assert repos[0].rank == 1

    def test_repos_typescript_since(self):
        client = GitHubClient()
        repos = client.get_trending_repos(language="typescript", since="weekly")
        assert isinstance(repos, list)
        # TypeScript trending should have results
        if repos:
            assert repos[0].rank == 1
            print(f"[verify] Top TS repo: {repos[0].full_name}")

    def test_repos_to_dict(self):
        client = GitHubClient()
        repos = client.get_trending_repos()
        assert len(repos) >= 1
        d = repos[0].to_dict()
        assert "full_name" in d
        assert "stars" in d
        assert "stars_today" in d
        assert "rank" in d
        assert d["rank"] == 1


class TestTrendingDevelopersLive:
    def test_developers_today(self):
        client = GitHubClient()
        devs = client.get_trending_developers()
        assert isinstance(devs, list)
        assert len(devs) >= 1
        first = devs[0]
        assert first.login, "Expected non-empty login"
        assert first.rank == 1
        assert first.profile_url.startswith("https://github.com/")
        print(f"[verify] Top developer today: {first.login} ({first.name})")

    def test_developers_weekly(self):
        client = GitHubClient()
        devs = client.get_trending_developers(since="weekly")
        assert isinstance(devs, list)
        assert len(devs) >= 1
        assert devs[0].rank == 1

    def test_developers_to_dict(self):
        client = GitHubClient()
        devs = client.get_trending_developers()
        assert len(devs) >= 1
        d = devs[0].to_dict()
        assert "login" in d
        assert "rank" in d
        assert "profile_url" in d


# ─── Subprocess / installed CLI tests ────────────────────────────────────────

class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-web-gh-trending")

    def _run(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            check=check,
        )

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "repos" in result.stdout
        assert "developers" in result.stdout

    def test_repos_list_json(self):
        result = self._run(["repos", "list", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) >= 1
        first = data[0]
        assert "full_name" in first
        assert "stars" in first
        assert "stars_today" in first
        assert "rank" in first
        assert first["rank"] == 1
        print(f"[verify] CLI repos list JSON: top={first['full_name']}")

    def test_repos_list_language_filter_json(self):
        result = self._run(["repos", "list", "--language", "python", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_repos_list_since_weekly_json(self):
        result = self._run(["repos", "list", "--since", "weekly", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_developers_list_json(self):
        result = self._run(["developers", "list", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) >= 1
        first = data[0]
        assert "login" in first
        assert "rank" in first
        assert first["rank"] == 1
        print(f"[verify] CLI developers list JSON: top={first['login']}")

    def test_version(self):
        result = self._run(["--version"])
        assert result.returncode == 0
        assert "1.0.0" in result.stdout
