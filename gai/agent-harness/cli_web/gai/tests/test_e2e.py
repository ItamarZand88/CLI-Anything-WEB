"""E2E tests for cli-web-gai \u2014 live Google AI Mode queries + subprocess tests."""

import json
import os
import shutil
import subprocess
import sys

import pytest


def _resolve_cli(name: str) -> list:
    """Resolve the CLI command, preferring installed binary."""
    if os.environ.get("CLI_WEB_FORCE_INSTALLED"):
        path = shutil.which(name)
        if not path:
            pytest.fail(f"{name} not found on PATH. Install with: pip install -e .")
        return [path]
    path = shutil.which(name)
    if path:
        return [path]
    return [sys.executable, "-m", "cli_web.gai"]


class TestLiveSearch:
    """Live E2E tests \u2014 requires internet connection.

    Note: Google rate-limits headless browsers. Running too many queries
    in succession triggers CAPTCHA. Tests are designed to be minimal.
    """

    @pytest.fixture(autouse=True)
    def _client(self):
        from cli_web.gai.core.client import GAIClient

        self.client = GAIClient(headless=True, lang="en", timeout=45000)
        yield
        self.client.close()

    def test_search_returns_answer_with_structure(self):
        """Search returns a well-structured result with answer and valid JSON."""
        from cli_web.gai.core.exceptions import CaptchaError

        try:
            result = self.client.search("What is the capital of France?")
        except CaptchaError:
            pytest.skip("CAPTCHA triggered \u2014 Google rate-limiting headless browsers")

        assert result.query == "What is the capital of France?"
        assert len(result.answer) > 10
        assert "paris" in result.answer.lower()
        print("[verify] Answer: ", result.answer[:80])

        # Verify JSON serialization
        d = result.to_dict()
        assert d["success"] is True
        assert "query" in d["data"]
        assert "answer" in d["data"]
        assert "sources" in d["data"]

        serialized = json.dumps(d, ensure_ascii=False)
        parsed = json.loads(serialized)
        assert parsed["success"] is True

        # Validate sources have URLs
        for src in result.sources:
            assert src.url.startswith("http")
            assert len(src.title) > 0


class TestCLISubprocess:
    """Test the installed CLI via subprocess."""

    @pytest.fixture(autouse=True)
    def _cli(self):
        self.cli_cmd = _resolve_cli("cli-web-gai")

    def _run(self, *args, timeout=60) -> subprocess.CompletedProcess:
        cmd = self.cli_cmd + list(args)
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )

    def test_help_output(self):
        """CLI --help works and shows expected content."""
        result = self._run("--help")
        assert result.returncode == 0
        assert "Google AI Mode" in result.stdout
        assert "search" in result.stdout

    def test_search_help(self):
        """search subcommand help works."""
        result = self._run("search", "--help")
        assert result.returncode == 0
        assert "ask" in result.stdout
        assert "followup" in result.stdout

    def test_version(self):
        """--version outputs version string."""
        result = self._run("--version")
        assert result.returncode == 0
        assert "0.1.0" in result.stdout

    def test_search_ask_json(self):
        """search ask with --json returns valid JSON."""
        result = self._run("search", "ask", "capital of France", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert "paris" in data["data"]["answer"].lower()
        print("[verify] Answer: ", data["data"]["answer"][:80])

    def test_search_ask_plain(self):
        """search ask without --json returns human-readable output."""
        result = self._run("search", "ask", "capital of Germany")
        assert result.returncode == 0
        assert "berlin" in result.stdout.lower() or "Berlin" in result.stdout

    def test_search_ask_with_lang(self):
        """search ask with --lang parameter works."""
        result = self._run("search", "ask", "capital of Italy", "--json", "--lang", "en")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert len(data["data"]["answer"]) > 5
