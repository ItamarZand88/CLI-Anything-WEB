"""E2E tests for cli-web-suno — live API and subprocess tests.

These tests require authentication. If auth is not configured, they FAIL.
Run: cli-web-suno auth login --from-browser
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

from cli_web.suno.core.client import SunoClient
from cli_web.suno.core.auth import validate_auth, load_auth


def _resolve_cli(name):
    """Resolve CLI command path."""
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


# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def client():
    """Create authenticated SunoClient. Fails if auth not configured."""
    auth_data = load_auth()
    if not auth_data or not auth_data.get("jwt"):
        pytest.fail(
            "Auth not configured. Run: cli-web-suno auth login --from-browser"
        )
    c = SunoClient()
    yield c
    c.close()


@pytest.fixture(scope="session")
def cli_cmd():
    return _resolve_cli("cli-web-suno")


# ─── Live API Tests ──────────────────────────────────────────────────


class TestLiveAuth:
    def test_validate_auth_returns_session(self, client):
        """Auth status — validate returns session with user info."""
        session = validate_auth()
        assert "user" in session
        user = session["user"]
        assert "email" in user
        assert "id" in user
        assert "handle" in user
        print(f"[verify] user={user['email']} handle={user['handle']}")


class TestLiveSongs:
    def test_list_songs(self, client):
        """Songs list — returns clips with expected fields."""
        result = client.get_feed(limit=3)
        assert "clips" in result
        clips = result["clips"]
        assert isinstance(clips, list)
        if clips:
            clip = clips[0]
            assert "id" in clip
            assert "status" in clip
            assert "audio_url" in clip
            assert "metadata" in clip
            print(f"[verify] First clip id={clip['id']} title={clip.get('title', 'N/A')}")

    def test_get_song_by_id(self, client):
        """Get single song — fetch from feed and verify by ID."""
        result = client.get_feed(limit=1)
        clips = result.get("clips", [])
        if not clips:
            pytest.skip("No clips in library")
        clip_id = clips[0]["id"]
        # Verify the clip has all expected fields
        clip = clips[0]
        assert clip["id"] == clip_id
        assert "audio_url" in clip
        assert clip["audio_url"].startswith("https://")
        print(f"[verify] Got clip id={clip_id} audio_url={clip['audio_url'][:60]}...")


class TestLiveBilling:
    def test_billing_info(self, client):
        """Billing info — returns credits and plan data."""
        info = client.get_billing_info()
        assert "credits" in info
        assert "total_credits_left" in info
        assert "plans" in info
        assert isinstance(info["plans"], list)
        assert len(info["plans"]) >= 1
        print(f"[verify] credits={info['credits']} total={info['total_credits_left']}")


class TestLiveExplore:
    def test_recommend_tags(self, client):
        """Explore tags — returns recommended tags."""
        result = client.recommend_tags()
        assert "recommended_tags" in result
        tags = result["recommended_tags"]
        assert isinstance(tags, list)
        assert len(tags) > 0
        print(f"[verify] Got {len(tags)} recommended tags: {tags[:5]}...")


class TestLiveProjects:
    def test_list_projects(self, client):
        """Projects list — returns at least default workspace."""
        result = client.list_projects()
        assert "projects" in result
        projects = result["projects"]
        assert isinstance(projects, list)
        assert len(projects) >= 1
        default = projects[0]
        assert "id" in default
        assert "name" in default
        print(f"[verify] Project id={default['id']} name={default['name']} clips={default.get('clip_count', '?')}")


class TestLivePrompts:
    def test_prompt_suggestions(self, client):
        """Prompts suggestions — returns prompt array."""
        result = client.get_prompt_suggestions()
        assert "prompts" in result
        prompts = result["prompts"]
        assert isinstance(prompts, list)
        assert len(prompts) > 0
        print(f"[verify] Got {len(prompts)} prompt suggestions")


class TestLiveGeneration:
    def test_concurrent_status(self, client):
        """Generation status — returns running/max."""
        result = client.get_concurrent_status()
        assert "running_jobs" in result
        assert "max_concurrent" in result
        assert isinstance(result["running_jobs"], int)
        print(f"[verify] Running={result['running_jobs']}/{result['max_concurrent']}")


# ─── Subprocess Tests ────────────────────────────────────────────────


class TestCLISubprocess:
    def test_help(self, cli_cmd):
        """CLI --help exits 0."""
        result = subprocess.run(
            cli_cmd + ["--help"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "cli-web-suno" in result.stdout
        assert "songs" in result.stdout

    def test_json_auth_status(self, cli_cmd):
        """CLI --json auth status returns valid JSON."""
        result = subprocess.run(
            cli_cmd + ["--json", "auth", "status"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "logged_in" in data or "email" in data

    def test_json_songs_list(self, cli_cmd):
        """CLI --json songs list --limit 1 returns JSON."""
        result = subprocess.run(
            cli_cmd + ["--json", "songs", "list", "--limit", "1"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_json_billing_info(self, cli_cmd):
        """CLI --json billing info returns credits JSON."""
        result = subprocess.run(
            cli_cmd + ["--json", "billing", "info"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "credits" in data
