"""E2E live tests and subprocess tests for cli-web-stitch.

Requires:
- Auth configured at ~/.config/cli-web-stitch/auth.json
- At least one existing project in Stitch (for read tests)

Run:
    cd stitch/agent-harness
    python -m pytest cli_web/stitch/tests/test_e2e.py -v -s
    python -m pytest cli_web/stitch/tests/test_e2e.py -v -s -m e2e       # E2E only
    python -m pytest cli_web/stitch/tests/test_e2e.py -v -s -m subprocess # subprocess only
"""
import json
import os
import subprocess
import time

import pytest

from cli_web.stitch.core.auth import get_auth_status
from cli_web.stitch.core.client import StitchClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_cli(name: str) -> list[str]:
    """Find the installed CLI command."""
    if os.environ.get("CLI_WEB_FORCE_INSTALLED"):
        return [name]
    return ["python", "-m", "cli_web.stitch"]


def _find_ready_project(client: StitchClient) -> str:
    """Return the ID of a project with status=4 (ready), or pytest.fail."""
    projects = client.list_projects()
    for p in projects:
        if p.status == 4:
            return p.id
    pytest.fail("No ready project (status=4) found -- create one in Stitch first")


# ---------------------------------------------------------------------------
# E2E Live Tests (real API calls)
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestE2E:
    """Live tests against the Stitch batchexecute API."""

    def test_auth_status(self):
        """Auth must be valid for all E2E tests."""
        status = get_auth_status()
        if not status.get("valid"):
            pytest.fail(
                f"Auth not configured or expired. "
                f"Run: cli-web-stitch auth login. "
                f"Error: {status.get('message')}"
            )
        print(f"[verify] Auth OK -- {status.get('cookie_count')} cookies, "
              f"session {status.get('session_id')}")

    def test_list_projects(self):
        """List projects returns at least one project with valid fields."""
        client = StitchClient()
        projects = client.list_projects()
        assert isinstance(projects, list)
        assert len(projects) > 0, "No projects found -- create one in Stitch first"
        p = projects[0]
        assert p.id
        assert p.resource_name.startswith("projects/")
        print(f"[verify] Found {len(projects)} projects, "
              f"first: id={p.id} title={p.title}")

    def test_get_project(self):
        """Get a specific project by ID."""
        client = StitchClient()
        projects = client.list_projects()
        assert len(projects) > 0, "No projects to test with"
        project = client.get_project(projects[0].id)
        assert project is not None
        assert project.id == projects[0].id
        print(f"[verify] Got project: id={project.id} title={project.title}")

    def test_list_screens(self):
        """List screens in a ready project."""
        client = StitchClient()
        pid = _find_ready_project(client)
        screens = client.list_screens(pid)
        assert isinstance(screens, list)
        assert len(screens) > 0, f"No screens in project {pid}"
        s = screens[0]
        assert s.id
        assert s.name
        print(f"[verify] Found {len(screens)} screens, "
              f"first: id={s.id} name={s.name}")

    def test_design_history(self):
        """List generation sessions for a project."""
        client = StitchClient()
        pid = _find_ready_project(client)
        sessions = client.list_sessions(pid)
        assert isinstance(sessions, list)
        # May be empty for some projects, just verify it's a list
        if sessions:
            s = sessions[0]
            assert s.resource_name
            print(f"[verify] Found {len(sessions)} sessions, "
                  f"first prompt: {s.prompt[:50]}")
        else:
            print(f"[verify] No sessions in project {pid} (OK)")

    def test_delete_project(self):
        """Delete a known project and verify it's gone.

        Note: Stitch's CREATE_PROJECT RPC is a client-side operation
        (the browser generates the project ID). We can only test delete
        on existing projects. This test picks the oldest project to delete.
        """
        client = StitchClient()
        projects = client.list_projects()
        assert len(projects) > 0, "No projects to test with"

        # Pick the least important project (oldest, or one with status != 4)
        target = None
        for p in reversed(projects):
            if p.status != 4:  # Not ready — safe to delete
                target = p
                break
        if not target:
            # All projects are ready — skip to avoid deleting user's work
            pytest.skip("All projects are ready — skipping delete to avoid data loss")

        pid = target.id
        print(f"[verify] Deleting project: id={pid} title={target.title}")

        result = client.delete_project(pid)
        assert result is True

        time.sleep(2)
        projects = client.list_projects()
        ids = [p.id for p in projects]
        assert pid not in ids, f"Deleted project {pid} still in list"
        print(f"[verify] Project {pid} successfully deleted")


# ---------------------------------------------------------------------------
# Subprocess Tests
# ---------------------------------------------------------------------------

@pytest.mark.subprocess
class TestCLISubprocess:
    """Test the installed CLI binary via subprocess."""

    def test_help(self):
        """CLI --help works and mentions stitch."""
        result = subprocess.run(
            _resolve_cli("cli-web-stitch") + ["--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        assert result.returncode == 0, (
            f"--help failed (rc={result.returncode}): {result.stderr}"
        )
        out = result.stdout.lower()
        assert "stitch" in out, f"'stitch' not in --help output: {result.stdout[:300]}"

    def test_auth_status_json(self):
        """CLI auth status --json returns valid JSON with success=True."""
        result = subprocess.run(
            _resolve_cli("cli-web-stitch") + ["auth", "status", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        assert result.returncode == 0, (
            f"auth status failed (rc={result.returncode}): {result.stderr}"
        )
        data = json.loads(result.stdout)
        assert data["success"] is True, f"auth status not successful: {data}"

    def test_projects_list_json(self):
        """CLI projects list --json returns valid JSON array."""
        result = subprocess.run(
            _resolve_cli("cli-web-stitch") + ["projects", "list", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        assert result.returncode == 0, (
            f"projects list failed (rc={result.returncode}): {result.stderr}"
        )
        data = json.loads(result.stdout)
        assert data["success"] is True, f"projects list not successful: {data}"
        assert isinstance(data["data"], list), f"data is not a list: {type(data['data'])}"

    def test_screens_list_json(self):
        """CLI screens list --json with --project flag."""
        # Find a ready project to query
        client = StitchClient()
        projects = client.list_projects()
        pid = None
        for p in projects:
            if p.status == 4:
                pid = p.id
                break
        if not pid:
            pytest.skip("No ready project to test screens list")

        result = subprocess.run(
            _resolve_cli("cli-web-stitch") + [
                "screens", "list", "--project", pid, "--json",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        assert result.returncode == 0, (
            f"screens list failed (rc={result.returncode}): {result.stderr}"
        )
        data = json.loads(result.stdout)
        assert data["success"] is True, f"screens list not successful: {data}"
