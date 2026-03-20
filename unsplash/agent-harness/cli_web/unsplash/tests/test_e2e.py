"""E2E live tests and subprocess tests for cli-web-unsplash.

These tests hit the real Unsplash /napi/ API. No auth required (public API).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest

from cli_web.unsplash.core.client import UnsplashClient


# ── _resolve_cli helper ──────────────────────────────────────────

def _resolve_cli(name):
    """Resolve installed CLI command; falls back to python -m for dev."""
    force = os.environ.get("CLI_WEB_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-web-", "cli_web.").replace("-", ".") + "." + name.split("-")[-1] + "_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


# ── Live API tests ───────────────────────────────────────────────

class TestPhotosLive:
    """Live tests against Unsplash /napi/ (no auth needed)."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = UnsplashClient()
        yield
        self.client.close()

    def test_search_photos(self):
        data = self.client.search_photos("mountains", per_page=5)
        assert "total" in data
        assert data["total"] > 0
        results = data["results"]
        assert len(results) > 0
        # Verify photo has required fields
        photo = results[0]
        assert "id" in photo
        assert "urls" in photo
        assert "user" in photo
        print(f"[verify] Search returned {data['total']} photos, first: {photo['id']}")

    def test_search_photos_with_filters(self):
        data = self.client.search_photos("ocean", orientation="landscape", per_page=3)
        assert data["total"] > 0
        results = data["results"]
        assert len(results) > 0

    def test_get_photo_detail(self):
        # First search to get a valid ID
        search = self.client.search_photos("nature", per_page=1)
        photo_id = search["results"][0]["id"]

        # Get detail
        detail = self.client.get_photo(photo_id)
        assert detail["id"] == photo_id
        assert "exif" in detail
        assert "location" in detail
        assert "tags" in detail
        assert "urls" in detail
        print(f"[verify] Photo {photo_id}: {detail.get('alt_description', 'N/A')}")

    def test_list_search_get_roundtrip(self):
        """List photos via search, then get one by ID — verify fields match."""
        search = self.client.search_photos("sunset", per_page=3)
        results = search["results"]
        assert len(results) > 0

        listed_photo = results[0]
        detail = self.client.get_photo(listed_photo["id"])

        # Verify fields match between list and detail
        assert detail["id"] == listed_photo["id"]
        assert detail["width"] == listed_photo["width"]
        assert detail["height"] == listed_photo["height"]
        assert detail["likes"] == listed_photo["likes"]
        print(f"[verify] Roundtrip OK: {detail['id']} matches search result")

    def test_get_photo_statistics(self):
        search = self.client.search_photos("city", per_page=1)
        photo_id = search["results"][0]["id"]

        stats = self.client.get_photo_statistics(photo_id)
        assert "id" in stats
        assert "downloads" in stats or "views" in stats
        print(f"[verify] Stats for {photo_id}: {stats.get('downloads', {})}")

    def test_random_photos(self):
        photos = self.client.get_random_photos(count=2)
        assert isinstance(photos, list)
        assert len(photos) == 2
        assert "id" in photos[0]
        assert "urls" in photos[0]
        print(f"[verify] Random photos: {[p['id'] for p in photos]}")

    def test_autocomplete(self):
        data = self.client.autocomplete("mount")
        assert "autocomplete" in data or "fuzzy" in data
        suggestions = data.get("autocomplete", data.get("fuzzy", []))
        assert len(suggestions) > 0
        print(f"[verify] Autocomplete: {[s['query'] for s in suggestions[:3]]}")


class TestTopicsLive:
    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = UnsplashClient()
        yield
        self.client.close()

    def test_list_topics(self):
        topics = self.client.list_topics(per_page=5)
        assert isinstance(topics, list)
        assert len(topics) > 0
        topic = topics[0]
        assert "slug" in topic
        assert "title" in topic
        print(f"[verify] Topics: {[t['slug'] for t in topics[:3]]}")

    def test_get_topic(self):
        topics = self.client.list_topics(per_page=1)
        slug = topics[0]["slug"]

        topic = self.client.get_topic(slug)
        assert topic["slug"] == slug
        assert "total_photos" in topic
        print(f"[verify] Topic '{slug}': {topic['total_photos']} photos")

    def test_topic_photos(self):
        topics = self.client.list_topics(per_page=1)
        slug = topics[0]["slug"]

        photos = self.client.get_topic_photos(slug, per_page=3)
        assert isinstance(photos, list)
        assert len(photos) > 0
        assert "id" in photos[0]


class TestCollectionsLive:
    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = UnsplashClient()
        yield
        self.client.close()

    def test_search_collections(self):
        data = self.client.search_collections("nature", per_page=3)
        assert data["total"] > 0
        results = data["results"]
        assert len(results) > 0
        assert "id" in results[0]
        assert "title" in results[0]

    def test_get_collection_and_photos(self):
        search = self.client.search_collections("wallpapers", per_page=1)
        coll_id = search["results"][0]["id"]

        coll = self.client.get_collection(coll_id)
        assert coll["id"] == coll_id
        assert "total_photos" in coll

        photos = self.client.get_collection_photos(coll_id, per_page=3)
        assert isinstance(photos, list)
        assert len(photos) > 0
        print(f"[verify] Collection {coll_id}: '{coll['title']}' with {coll['total_photos']} photos")


class TestUsersLive:
    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = UnsplashClient()
        yield
        self.client.close()

    def test_search_users(self):
        data = self.client.search_users("landscape", per_page=3)
        assert data["total"] > 0
        results = data["results"]
        assert len(results) > 0
        assert "username" in results[0]

    def test_get_user_profile(self):
        user = self.client.get_user("unsplash")
        assert user["username"] == "unsplash"
        assert "total_photos" in user
        assert "name" in user
        print(f"[verify] User @unsplash: {user['name']}, {user['total_photos']} photos")

    def test_user_photos(self):
        photos = self.client.get_user_photos("unsplash", per_page=3)
        assert isinstance(photos, list)
        # unsplash account has photos
        if len(photos) > 0:
            assert "id" in photos[0]

    def test_user_collections(self):
        colls = self.client.get_user_collections("unsplash", per_page=3)
        assert isinstance(colls, list)


# ── Subprocess tests ─────────────────────────────────────────────

class TestCLISubprocess:
    """Test the installed CLI binary via subprocess."""

    CLI_BASE = _resolve_cli("cli-web-unsplash")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            check=check,
            encoding="utf-8",
            errors="replace",
        )

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "photos" in result.stdout
        assert "topics" in result.stdout

    def test_version(self):
        result = self._run(["--version"])
        assert result.returncode == 0
        assert "0.1.0" in result.stdout

    def test_photos_search_json(self):
        result = self._run(["photos", "search", "cats", "--per-page", "3", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "total" in data
        assert len(data["results"]) > 0
        assert "id" in data["results"][0]

    def test_photos_get_json(self):
        # First get an ID
        search = self._run(["photos", "search", "dog", "--per-page", "1", "--json"])
        photo_id = json.loads(search.stdout)["results"][0]["id"]

        result = self._run(["photos", "get", photo_id, "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["id"] == photo_id

    def test_topics_list_json(self):
        result = self._run(["topics", "list", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_users_get_json(self):
        result = self._run(["users", "get", "unsplash", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["username"] == "unsplash"

    def test_collections_search_json(self):
        result = self._run(["collections", "search", "nature", "--per-page", "3", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["total"] > 0

    def test_photos_random_json(self):
        result = self._run(["photos", "random", "--count", "1", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) == 1
        assert "id" in data[0]

    def test_human_readable_output(self):
        """Verify non-JSON output is human-readable (no crash)."""
        result = self._run(["photos", "search", "flower", "--per-page", "3"])
        assert result.returncode == 0
        assert "flower" in result.stdout.lower() or "Found" in result.stdout
