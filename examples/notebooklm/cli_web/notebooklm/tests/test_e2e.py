"""E2E tests for cli-web-notebooklm — requires live auth."""

import json
import os
import shutil
import subprocess
import sys

import pytest

from cli_web.notebooklm.core.auth import load_cookies, check_required_cookies, fetch_tokens
from cli_web.notebooklm.core.client import NotebookLMClient


def _resolve_cli(name):
    force = os.environ.get("CLI_WEB_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-web-", "cli_web.") + "." + name.split("-")[-1] + "_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


# ── Auth Verification ──────────────────────────────────────────────

class TestAuthLive:
    def test_auth_cookies_present(self):
        cookies = load_cookies()
        if not cookies:
            pytest.fail("Auth not configured. Run: cli-web-notebooklm auth login --from-browser")
        ok, missing = check_required_cookies(cookies)
        if not ok:
            pytest.fail(f"Missing required cookies: {missing}")
        print(f"[verify] {len(cookies)} cookies present, all required OK")

    def test_auth_live_validation(self):
        cookies = load_cookies()
        if not cookies:
            pytest.fail("Auth not configured. Run: cli-web-notebooklm auth login --from-browser")
        tokens = fetch_tokens(cookies)
        assert tokens.get("at"), "CSRF token extraction failed — cookies may be expired"
        assert tokens.get("bl"), "Build label extraction failed"
        print(f"[verify] Live validation OK: at={tokens['at'][:20]}...")


# ── Live API Tests ─────────────────────────────────────────────────

class TestNotebooksLive:
    def test_list_notebooks(self):
        client = NotebookLMClient()
        notebooks = client.list_notebooks()
        assert isinstance(notebooks, list), f"Expected list, got {type(notebooks)}"
        assert len(notebooks) > 0, "No notebooks found"
        print(f"[verify] Found {len(notebooks)} notebooks")
        # Verify first notebook has expected structure
        from cli_web.notebooklm.core.models import parse_notebook
        nb = parse_notebook(notebooks[0])
        assert nb.get("id"), "Notebook missing ID"
        assert nb.get("title"), "Notebook missing title"
        print(f"[verify] First notebook: id={nb['id']} title={nb['title'][:40]}")

    def test_get_notebook(self):
        client = NotebookLMClient()
        notebooks = client.list_notebooks()
        assert len(notebooks) > 0
        from cli_web.notebooklm.core.models import parse_notebook
        first = parse_notebook(notebooks[0])
        nb_id = first["id"]

        details = client.get_notebook(nb_id)
        assert details is not None
        parsed = parse_notebook(details)
        assert parsed["id"] == nb_id
        print(f"[verify] Got notebook {nb_id}: {parsed['title'][:40]}")


class TestSourcesLive:
    def test_list_sources(self):
        client = NotebookLMClient()
        notebooks = client.list_notebooks()
        # Find a notebook with sources
        from cli_web.notebooklm.core.models import parse_notebook
        nb_with_sources = None
        for nb_raw in notebooks:
            nb = parse_notebook(nb_raw)
            if nb["source_count"] > 0:
                nb_with_sources = nb
                break
        if not nb_with_sources:
            pytest.skip("No notebooks with sources found")

        sources = client.list_sources(nb_with_sources["id"])
        assert isinstance(sources, list)
        assert len(sources) > 0
        print(f"[verify] Found {len(sources)} sources in notebook {nb_with_sources['id']}")


class TestArtifactsLive:
    def test_list_artifacts(self):
        client = NotebookLMClient()
        notebooks = client.list_notebooks()
        from cli_web.notebooklm.core.models import parse_notebook
        first = parse_notebook(notebooks[0])
        artifacts = client.list_artifacts(first["id"])
        assert artifacts is not None
        print(f"[verify] Artifacts response type: {type(artifacts)}")


class TestChatLive:
    def test_get_summary(self):
        client = NotebookLMClient()
        notebooks = client.list_notebooks()
        from cli_web.notebooklm.core.models import parse_notebook
        # Find notebook with sources for summary
        for nb_raw in notebooks:
            nb = parse_notebook(nb_raw)
            if nb["source_count"] > 0:
                result = client.get_summary(nb["id"])
                assert result is not None
                print(f"[verify] Got summary for {nb['id']}")
                return
        pytest.skip("No notebooks with sources for summary test")


# ── Subprocess Tests ───────────────────────────────────────────────

class TestCLISubprocess:
    def test_help(self):
        cmd = _resolve_cli("cli-web-notebooklm")
        result = subprocess.run(cmd + ["--help"], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0
        assert "notebooks" in result.stdout
        assert "auth" in result.stdout

    def test_version(self):
        cmd = _resolve_cli("cli-web-notebooklm")
        result = subprocess.run(cmd + ["--version"], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0
        assert "1.0.0" in result.stdout

    def test_json_notebooks_list(self):
        cmd = _resolve_cli("cli-web-notebooklm")
        result = subprocess.run(
            cmd + ["--json", "notebooks", "list"],
            capture_output=True, timeout=60,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        assert result.returncode == 0, f"Exit {result.returncode}: {result.stderr}"
        stdout = result.stdout.decode("utf-8", errors="replace")
        data = json.loads(stdout)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        print(f"[verify] Subprocess returned {len(data)} notebooks")

    def test_json_auth_status(self):
        cmd = _resolve_cli("cli-web-notebooklm")
        result = subprocess.run(
            cmd + ["--json", "auth", "status"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        assert result.returncode == 0, f"Exit {result.returncode}: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["status"] == "ok"
        assert data["live_validation"] == "ok"
