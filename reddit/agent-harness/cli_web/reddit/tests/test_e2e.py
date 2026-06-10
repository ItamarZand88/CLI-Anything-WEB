"""E2E live tests and subprocess tests for cli-web-reddit.

These tests hit the real Reddit JSON API. No auth required (public read-only).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest
from cli_web.reddit.core.client import RedditClient

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
    module = "cli_web.reddit.reddit_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


# ── Helpers ──────────────────────────────────────────────────────


def _posts_from_listing(data: dict) -> list[dict]:
    """Extract post dicts from a Reddit listing response."""
    return [child["data"] for child in data["data"]["children"]]


def _assert_post_fields(post: dict) -> None:
    """Verify a post dict has the required fields."""
    for field in ("id", "title", "subreddit", "author", "score", "num_comments"):
        assert field in post, f"Missing field: {field}"


# ── Live API: Feed ───────────────────────────────────────────────


@pytest.mark.live
class TestFeedLive:
    """Live tests for feed endpoints (no auth)."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = RedditClient()
        yield
        self.client.close()

    def test_feed_hot(self):
        data = self.client.feed_hot(limit=3)
        posts = _posts_from_listing(data)
        assert len(posts) > 0
        for p in posts:
            _assert_post_fields(p)
        print(f"[verify] feed_hot returned {len(posts)} posts, first: {posts[0]['title'][:60]}")

    def test_feed_top(self):
        data = self.client.feed_top(limit=3, time="day")
        posts = _posts_from_listing(data)
        assert len(posts) > 0
        for p in posts:
            _assert_post_fields(p)
        print(f"[verify] feed_top returned {len(posts)} posts")

    def test_feed_popular(self):
        data = self.client.feed_popular(limit=3)
        posts = _posts_from_listing(data)
        assert len(posts) > 0
        for p in posts:
            _assert_post_fields(p)
        print(f"[verify] feed_popular returned {len(posts)} posts")

    def test_pagination(self):
        """Fetch page 1, grab cursor, fetch page 2 — verify different posts."""
        page1 = self.client.feed_hot(limit=3)
        posts1 = _posts_from_listing(page1)
        assert len(posts1) > 0

        after = page1["data"].get("after")
        assert after, "Expected pagination cursor in response"

        page2 = self.client.feed_hot(limit=3, after=after)
        posts2 = _posts_from_listing(page2)
        assert len(posts2) > 0

        ids1 = {p["id"] for p in posts1}
        ids2 = {p["id"] for p in posts2}
        assert ids1 != ids2, "Page 1 and page 2 should have different posts"
        print(f"[verify] Pagination OK: page1 ids={ids1}, page2 ids={ids2}")


# ── Live API: Subreddit ──────────────────────────────────────────


@pytest.mark.live
class TestSubredditLive:
    """Live tests for subreddit endpoints."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = RedditClient()
        yield
        self.client.close()

    def test_sub_posts(self):
        data = self.client.sub_posts("python", limit=3)
        posts = _posts_from_listing(data)
        assert len(posts) > 0
        for p in posts:
            _assert_post_fields(p)
            assert p["subreddit"].lower() == "python"
        print(f"[verify] r/python returned {len(posts)} posts")

    def test_sub_info(self):
        data = self.client.sub_info("python")
        info = data["data"]
        assert info["display_name"].lower() == "python"
        assert "subscribers" in info
        assert info["subscribers"] > 0
        print(f"[verify] r/python: {info['subscribers']} subscribers")

    def test_sub_rules(self):
        data = self.client.sub_rules("python")
        assert "rules" in data
        rules = data["rules"]
        assert len(rules) > 0
        for rule in rules:
            assert "short_name" in rule
        print(f"[verify] r/python has {len(rules)} rules")

    def test_list_get_roundtrip(self):
        """List posts, then get one by ID via post_detail — verify fields match."""
        listing = self.client.sub_posts("python", limit=3)
        posts = _posts_from_listing(listing)
        assert len(posts) > 0

        target = posts[0]
        post_id = target["id"]
        subreddit = target["subreddit"]

        detail = self.client.post_detail(subreddit, post_id)
        assert isinstance(detail, list)
        assert len(detail) >= 1
        detail_post = detail[0]["data"]["children"][0]["data"]
        assert detail_post["id"] == post_id
        assert detail_post["title"] == target["title"]
        print(f"[verify] Roundtrip OK: post {post_id} title matches")


# ── Live API: Search ─────────────────────────────────────────────


@pytest.mark.live
class TestSearchLive:
    """Live tests for search endpoints."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = RedditClient()
        yield
        self.client.close()

    def test_search_posts(self):
        data = self.client.search_posts("python", limit=3)
        posts = _posts_from_listing(data)
        assert len(posts) > 0
        for p in posts:
            _assert_post_fields(p)
        print(f"[verify] search_posts('python') returned {len(posts)} results")

    def test_search_subreddits(self):
        data = self.client.search_subreddits("python", limit=3)
        subs = [child["data"] for child in data["data"]["children"]]
        assert len(subs) > 0
        for s in subs:
            assert "display_name" in s
        print(f"[verify] search_subreddits('python') returned {len(subs)} subreddits")


# ── Live API: User ───────────────────────────────────────────────


@pytest.mark.live
class TestUserLive:
    """Live tests for user endpoints."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = RedditClient()
        yield
        self.client.close()

    def test_user_about(self):
        data = self.client.user_about("spez")
        info = data["data"]
        assert info["name"].lower() == "spez"
        assert "link_karma" in info
        print(f"[verify] u/spez: link_karma={info['link_karma']}")

    def test_user_posts(self):
        data = self.client.user_posts("spez", limit=3)
        posts = _posts_from_listing(data)
        assert len(posts) > 0
        for p in posts:
            assert p["author"].lower() == "spez"
        print(f"[verify] u/spez has {len(posts)} posts returned")


# ── Subprocess tests ─────────────────────────────────────────────


@pytest.mark.subprocess
class TestCLISubprocess:
    """Test the CLI binary via subprocess (installed or python -m fallback)."""

    @pytest.fixture(autouse=True)
    def setup_cmd(self):
        self.cmd = _resolve_cli("cli-web-reddit")

    def _run(self, *args, check: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [*self.cmd, *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if check and result.returncode != 0:
            print(f"[stderr] {result.stderr}")
        return result

    def test_help(self):
        r = self._run("--help")
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "feed" in out
        assert "sub" in out
        assert "search" in out
        assert "user" in out
        print("[verify] --help lists all command groups")

    def test_version(self):
        r = self._run("--version")
        assert r.returncode == 0
        assert "0.2.0" in r.stdout
        print(f"[verify] --version: {r.stdout.strip()}")

    def test_feed_hot_json(self):
        r = self._run("feed", "hot", "--limit", "3", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "posts" in data or isinstance(data, list)
        # Accept either {"posts": [...]} or [...] depending on output format
        posts = data.get("posts", data) if isinstance(data, dict) else data
        assert len(posts) > 0
        print(f"[verify] feed hot --json returned {len(posts)} posts")

    def test_search_posts_json(self):
        r = self._run("search", "posts", "python", "--limit", "3", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        # Flexible: accept list or dict with posts key
        if isinstance(data, dict):
            posts = data.get("posts", data.get("results", []))
        else:
            posts = data
        assert len(posts) > 0
        print(f"[verify] search posts --json returned {len(posts)} results")

    def test_sub_info_json(self):
        r = self._run("sub", "info", "python", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert isinstance(data, dict)
        # Should contain subreddit name field
        name = data.get("display_name", data.get("name", ""))
        assert name.lower() == "python"
        print(f"[verify] sub info python --json: {name}")

    def test_user_info_json(self):
        r = self._run("user", "info", "spez", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert isinstance(data, dict)
        name = data.get("name", "")
        assert name.lower() == "spez"
        print(f"[verify] user info spez --json: {name}")

    def test_human_readable_output(self):
        """Non-JSON output should produce human-readable table/text."""
        r = self._run("feed", "hot", "--limit", "3")
        assert r.returncode == 0
        out = r.stdout
        # Should have some text output, not raw JSON
        assert len(out.strip()) > 0
        # Should NOT start with '{' or '[' (not raw JSON)
        stripped = out.strip()
        assert not stripped.startswith("{"), "Expected human-readable output, got JSON"
        assert not stripped.startswith("["), "Expected human-readable output, got JSON"
        print(f"[verify] Human-readable output: {len(out)} chars")
