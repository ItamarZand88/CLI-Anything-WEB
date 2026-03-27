"""E2E tests for cli-web-hackernews (live API, no mocks) + subprocess tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest

from cli_web.hackernews.core.client import HackerNewsClient
from cli_web.hackernews.core import auth
from cli_web.hackernews.core.exceptions import AuthError, NotFoundError
from cli_web.hackernews.core.models import Comment, SearchResult, Story, User


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    return HackerNewsClient()


def _resolve_cli(name: str) -> str:
    """Find the CLI binary path for subprocess tests."""
    if os.environ.get("CLI_WEB_FORCE_INSTALLED"):
        path = shutil.which(name)
        if path:
            return path
        raise FileNotFoundError(f"{name} not found in PATH")
    path = shutil.which(name)
    if path:
        return path
    return f"{sys.executable} -m cli_web.hackernews"


# ─── E2E: Stories Feed Tests ─────────────────────────────────────────────────


class TestStoriesFeedE2E:
    def test_top_stories_returns_list(self, client):
        stories = client.get_stories("top", limit=5)
        assert len(stories) >= 1
        assert all(isinstance(s, Story) for s in stories)

    def test_new_stories_returns_list(self, client):
        stories = client.get_stories("new", limit=5)
        assert len(stories) >= 1

    def test_best_stories_returns_list(self, client):
        stories = client.get_stories("best", limit=5)
        assert len(stories) >= 1

    def test_ask_stories_returns_list(self, client):
        stories = client.get_stories("ask", limit=5)
        assert len(stories) >= 1

    def test_show_stories_returns_list(self, client):
        stories = client.get_stories("show", limit=5)
        assert len(stories) >= 1

    def test_job_stories_returns_list(self, client):
        stories = client.get_stories("job", limit=5)
        assert len(stories) >= 1

    def test_story_has_required_fields(self, client):
        stories = client.get_stories("top", limit=1)
        story = stories[0]
        assert story.id > 0
        assert story.title
        assert story.by
        assert story.score >= 0

    def test_story_ids_returns_ints(self, client):
        ids = client.get_story_ids("top")
        assert len(ids) > 0
        assert all(isinstance(i, int) for i in ids[:10])


# ─── E2E: Story View + Comments ──────────────────────────────────────────────


class TestStoryViewE2E:
    def test_get_story_by_id(self, client):
        # Get a real story ID from top stories
        ids = client.get_story_ids("top")
        story = client.get_story(ids[0])
        assert isinstance(story, Story)
        assert story.id == ids[0]
        assert story.title

    def test_get_comments_for_story(self, client):
        # Find a story with comments
        stories = client.get_stories("top", limit=5)
        story_with_comments = None
        for s in stories:
            if s.descendants > 0:
                story_with_comments = s
                break
        if story_with_comments is None:
            pytest.skip("No stories with comments found")
        comments = client.get_comments(story_with_comments.id, limit=3)
        assert len(comments) >= 1
        assert all(isinstance(c, Comment) for c in comments)
        assert comments[0].by  # Has author


# ─── E2E: User Profile ──────────────────────────────────────────────────────


class TestUserE2E:
    def test_get_user_profile(self, client):
        user = client.get_user("dang")
        assert isinstance(user, User)
        assert user.id == "dang"
        assert user.karma > 0
        assert user.created > 0

    def test_get_nonexistent_user_raises(self, client):
        with pytest.raises(NotFoundError):
            client.get_user("thisisanonexistentuser999999")


# ─── E2E: Search ────────────────────────────────────────────────────────────


class TestSearchE2E:
    def test_search_stories(self, client):
        results = client.search("python", tags="story", hits_per_page=5)
        assert len(results) >= 1
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].title

    def test_search_by_date(self, client):
        results = client.search("javascript", sort_by_date=True, hits_per_page=3)
        assert len(results) >= 1

    def test_search_comments(self, client):
        results = client.search("react", tags="comment", hits_per_page=3)
        assert len(results) >= 1


# ─── Subprocess Tests ───────────────────────────────────────────────────────


class TestSubprocess:
    def _run(self, args: str, timeout: int = 30) -> subprocess.CompletedProcess:
        cli_path = _resolve_cli("cli-web-hackernews")
        cmd = f"{cli_path} {args}"
        return subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def test_version(self):
        result = self._run("--version")
        assert result.returncode == 0
        assert "0.2.0" in result.stdout

    def test_help(self):
        result = self._run("--help")
        assert result.returncode == 0
        assert "hackernews" in result.stdout.lower()

    def test_stories_top_json(self):
        result = self._run("stories top -n 3 --json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "title" in data[0]
        assert "score" in data[0]

    def test_search_stories_json(self):
        result = self._run('search stories "python" -n 3 --json')
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_user_view_json(self):
        result = self._run("user view dang --json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["id"] == "dang"
        assert data["karma"] > 0

    def test_stories_view_json(self):
        # Get a story ID first
        result = self._run("stories top -n 1 --json")
        assert result.returncode == 0
        stories = json.loads(result.stdout)
        story_id = stories[0]["id"]

        result = self._run(f"stories view {story_id} --no-comments --json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["id"] == story_id

    def test_auth_status_json(self):
        result = self._run("auth status --json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "logged_in" in data

    def test_auth_help(self):
        result = self._run("auth --help")
        assert result.returncode == 0
        assert "login" in result.stdout.lower()

    def test_upvote_help(self):
        result = self._run("upvote --help")
        assert result.returncode == 0
        assert "item_id" in result.stdout.lower()

    def test_submit_help(self):
        result = self._run("submit --help")
        assert result.returncode == 0
        assert "title" in result.stdout.lower()

    def test_comment_help(self):
        result = self._run("comment --help")
        assert result.returncode == 0
        assert "parent_id" in result.stdout.lower()


# ─── E2E: Auth-Enabled Tests (require auth cookie) ─────────────────────────


@pytest.fixture
def auth_client():
    """Create an authenticated client. Fails if not logged in."""
    cookie = auth.get_user_cookie()
    return HackerNewsClient(user_cookie=cookie)


class TestAuthActionsE2E:
    def test_upvote_story(self, auth_client):
        """Test upvoting a top story."""
        # Get a real story to upvote
        ids = auth_client.get_story_ids("top")
        result = auth_client.upvote(ids[0])
        assert result["success"] is True
        assert result["action"] == "upvoted"

    def test_get_submissions(self, auth_client):
        """Test fetching dang's submissions (well-known user)."""
        stories = auth_client.get_submissions("dang", limit=3)
        assert len(stories) >= 1
        assert all(isinstance(s, Story) for s in stories)

    def test_favorite_and_list(self, auth_client):
        """Test favoriting a story."""
        ids = auth_client.get_story_ids("top")
        result = auth_client.favorite(ids[0])
        assert result["success"] is True
        assert result["action"] == "favorited"

    def test_auth_validate(self):
        """Test auth validation works."""
        result = auth.validate_auth()
        assert result["valid"] is True
        assert result["username"]
