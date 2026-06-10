"""E2E + subprocess tests for cli-web-pexels.

These tests make REAL network calls to pexels.com.
No mocking — validates the full pipeline against live data.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest
from cli_web.pexels.core.client import PexelsClient
from cli_web.pexels.core.exceptions import NotFoundError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_cli(name):
    force = os.environ.get("CLI_WEB_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    parts = name.split("-")
    module = f"cli_web.{parts[-1]}.{parts[-1]}_cli"
    return [sys.executable, "-m", module]


# ---------------------------------------------------------------------------
# Live E2E tests — uses PexelsClient directly
# ---------------------------------------------------------------------------


class TestPexelsLive:
    """Live tests against pexels.com via PexelsClient."""

    @pytest.fixture(autouse=True)
    def _client(self):
        self.client = PexelsClient(timeout=30.0)

    def test_search_photos(self):
        result = self.client.search_photos("nature")
        assert len(result["data"]) > 0
        first = result["data"][0]
        assert first["id"] is not None
        assert first["title"] is not None
        assert first["photographer"] is not None

    def test_search_photos_with_filters(self):
        result = self.client.search_photos("nature", orientation="landscape")
        assert len(result["data"]) > 0

    def test_search_photos_pagination(self):
        result = self.client.search_photos("nature", page=2)
        assert result["pagination"]["current_page"] == 2

    def test_get_photo(self):
        result = self.client.get_photo("green-leaves-1072179")
        assert result["id"] == 1072179
        assert result["image"]["download"] is not None

    def test_search_videos(self):
        result = self.client.search_videos("ocean")
        assert len(result["data"]) > 0
        assert result["data"][0]["type"] == "video"

    def test_get_video(self):
        result = self.client.get_video("long-narrow-road-856479")
        assert len(result["video_files"]) > 0
        assert any(f["link"] for f in result["video_files"])

    def test_get_user(self):
        result = self.client.get_user("pixabay")
        user = result["user"]
        assert user["username"] is not None
        assert user["photos_count"] is not None and user["photos_count"] > 0

    def test_get_user_media(self):
        result = self.client.get_user_media("pixabay")
        assert len(result["data"]) > 0

    def test_get_collection(self):
        result = self.client.get_collection("spring-aesthetic-fvku5ng")
        coll = result["collection"]
        assert coll["title"] is not None
        assert coll["media_count"] is not None

    def test_discover(self):
        result = self.client.discover()
        assert len(result["popular"]) > 0 or len(result["collections"]) > 0

    def test_search_suggestions(self):
        result = self.client.search_suggestions("cat")
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(s, str) for s in result)

    def test_not_found_raises(self):
        with pytest.raises(NotFoundError):
            self.client.get_photo("this-photo-definitely-does-not-exist-99999999")


# ---------------------------------------------------------------------------
# Subprocess tests — runs cli-web-pexels as a real process
# ---------------------------------------------------------------------------


class TestCLISubprocess:
    """Subprocess tests that exercise the installed CLI binary."""

    CLI_BASE = _resolve_cli("cli-web-pexels")

    def _run(self, args, check=False):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=check,
        )

    def test_help(self):
        r = self._run(["--help"])
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "photos" in out
        assert "videos" in out

    def test_version(self):
        r = self._run(["--version"])
        assert r.returncode == 0
        assert "1.0.0" in r.stdout

    def test_photos_search_json(self):
        r = self._run(["photos", "search", "nature", "--json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data["data"]) > 0

    def test_photos_get_json(self):
        r = self._run(["photos", "get", "green-leaves-1072179", "--json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["id"] == 1072179

    def test_videos_search_json(self):
        r = self._run(["videos", "search", "ocean", "--json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data["results"]) > 0

    def test_users_get_json(self):
        r = self._run(["users", "get", "pixabay", "--json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["user"]["username"] is not None

    def test_collections_discover_json(self):
        r = self._run(["collections", "discover", "--json"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "popular" in data or "collections" in data
