"""Unit tests for cli-web-reddit — mocked HTTP, no network required."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from cli_web.reddit.core.exceptions import (
    AuthError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    RedditError,
    ServerError,
)
from cli_web.reddit.core.models import (
    _collect_comments,
    extract_listing_posts,
    extract_listing_posts_and_comments,
    extract_listing_subreddits,
    format_comment,
    format_post_detail,
    format_post_summary,
    format_subreddit_info,
    format_subreddit_search,
    format_user_info,
)
from cli_web.reddit.utils.helpers import (
    handle_errors,
    json_error,
    resolve_json_mode,
    truncate,
)
from click.testing import CliRunner

# ── Sample fixtures ─────────────────────────────────────────

SAMPLE_POST_CHILD = {
    "kind": "t3",
    "data": {
        "id": "abc123",
        "title": "Test post title",
        "author": "testuser",
        "subreddit": "python",
        "score": 42,
        "num_comments": 5,
        "upvote_ratio": 0.95,
        "created_utc": 1700000000.0,
        "url": "https://example.com",
        "permalink": "/r/python/comments/abc123/test/",
        "is_self": True,
        "over_18": False,
        "stickied": False,
        "link_flair_text": "Discussion",
        "selftext": "Body text here",
    },
}

SAMPLE_COMMENT_CHILD = {
    "kind": "t1",
    "data": {
        "id": "xyz789",
        "author": "commenter",
        "body": "Great post!",
        "score": 10,
        "created_utc": 1700001000.0,
        "is_submitter": False,
        "depth": 0,
    },
}

SAMPLE_SAVED_COMMENT_CHILD = {
    "kind": "t1",
    "data": {
        "id": "saved1",
        "author": "commenter2",
        "body": "Saved this for later",
        "score": 5,
        "created_utc": 1700002000.0,
        "is_submitter": False,
        "depth": 0,
        "subreddit": "learnpython",
        "permalink": "/r/learnpython/comments/xxx/slug/saved1/",
    },
}

SAMPLE_SUBREDDIT_CHILD = {
    "kind": "t5",
    "data": {
        "display_name": "python",
        "title": "Python",
        "public_description": "News about Python",
        "subscribers": 1200000,
        "accounts_active": 5000,
        "created_utc": 1200000000.0,
        "over18": False,
        "subreddit_type": "public",
    },
}

SAMPLE_USER = {
    "data": {
        "name": "spez",
        "link_karma": 100000,
        "comment_karma": 50000,
        "total_karma": 150000,
        "created_utc": 1100000000.0,
        "is_gold": True,
        "has_verified_email": True,
    },
}

SAMPLE_LISTING = {
    "data": {
        "children": [SAMPLE_POST_CHILD],
        "after": "t3_next123",
    },
}


def _mock_response(status_code=200, json_data=None, text="", headers=None):
    """Create a mock response object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.headers = headers or {}
    return resp


# ── Model tests ──────────────────────────────────────────────


@pytest.mark.unit
class TestModels:
    """Test response model formatting functions."""

    def test_format_post_summary(self):
        result = format_post_summary(SAMPLE_POST_CHILD)
        assert result["id"] == "abc123"
        assert result["title"] == "Test post title"
        assert result["author"] == "testuser"
        assert result["subreddit"] == "python"
        assert result["score"] == 42
        assert result["num_comments"] == 5
        assert result["flair"] == "Discussion"
        assert result["is_self"] is True

    def test_format_comment(self):
        result = format_comment(SAMPLE_COMMENT_CHILD)
        assert result["id"] == "xyz789"
        assert result["author"] == "commenter"
        assert result["body"] == "Great post!"
        assert result["score"] == 10
        assert result["depth"] == 0

    def test_format_subreddit_info(self):
        result = format_subreddit_info(SAMPLE_SUBREDDIT_CHILD)
        assert result["name"] == "python"
        assert result["subscribers"] == 1200000
        assert result["type"] == "public"
        assert result["over_18"] is False

    def test_format_subreddit_search(self):
        result = format_subreddit_search(SAMPLE_SUBREDDIT_CHILD)
        assert result["name"] == "python"
        assert result["subscribers"] == 1200000

    def test_format_user_info(self):
        result = format_user_info(SAMPLE_USER)
        assert result["name"] == "spez"
        assert result["total_karma"] == 150000
        assert result["is_gold"] is True

    def test_extract_listing_posts(self):
        posts, after = extract_listing_posts(SAMPLE_LISTING)
        assert len(posts) == 1
        assert posts[0]["id"] == "abc123"
        assert after == "t3_next123"

    def test_extract_listing_posts_empty(self):
        posts, after = extract_listing_posts({"data": {"children": [], "after": None}})
        assert len(posts) == 0
        assert after is None

    def test_extract_listing_subreddits(self):
        listing = {"data": {"children": [SAMPLE_SUBREDDIT_CHILD], "after": None}}
        subs, after = extract_listing_subreddits(listing)
        assert len(subs) == 1
        assert subs[0]["name"] == "python"
        assert after is None

    def test_extract_listing_posts_and_comments_keeps_both_kinds(self):
        """Mixed listing with t3 and t1 should return both."""
        listing = {
            "data": {
                "children": [SAMPLE_POST_CHILD, SAMPLE_SAVED_COMMENT_CHILD],
                "after": "cursor123",
            }
        }
        posts, comments, after = extract_listing_posts_and_comments(listing)
        assert len(posts) == 1
        assert len(comments) == 1
        assert posts[0]["id"] == "abc123"
        assert comments[0]["id"] == "saved1"
        assert comments[0]["subreddit"] == "learnpython"
        assert after == "cursor123"

    def test_format_post_detail_basic(self):
        comments_listing = {
            "data": {"children": [SAMPLE_COMMENT_CHILD]},
        }
        result = format_post_detail(SAMPLE_POST_CHILD, comments_listing)
        assert result["id"] == "abc123"
        assert len(result["comments"]) == 1
        assert result["comments"][0]["id"] == "xyz789"

    def test_format_post_detail_flattens_nested_comments(self):
        """Nested replies should be flattened into the comments list."""
        nested = {
            "data": {
                "children": [
                    {
                        "kind": "t1",
                        "data": {
                            "id": "parent1",
                            "author": "user1",
                            "body": "Top level",
                            "score": 5,
                            "created_utc": 1700000000.0,
                            "is_submitter": False,
                            "depth": 0,
                            "replies": {
                                "data": {
                                    "children": [
                                        {
                                            "kind": "t1",
                                            "data": {
                                                "id": "child1",
                                                "author": "user2",
                                                "body": "Reply",
                                                "score": 3,
                                                "created_utc": 1700001000.0,
                                                "is_submitter": False,
                                                "depth": 1,
                                            },
                                        }
                                    ]
                                }
                            },
                        },
                    }
                ]
            }
        }
        result = format_post_detail(SAMPLE_POST_CHILD, nested)
        assert len(result["comments"]) == 2
        assert result["comments"][0]["id"] == "parent1"
        assert result["comments"][1]["id"] == "child1"

    def test_collect_comments_empty(self):
        comments = []
        _collect_comments([], comments)
        assert len(comments) == 0

    def test_format_post_summary_deleted_author(self):
        child = {"kind": "t3", "data": {"id": "del1"}}
        result = format_post_summary(child)
        assert result["author"] == "[deleted]"


# ── Client tests ──────────────────────────────────────────────


@pytest.mark.unit
class TestClient:
    """Test HTTP client with mocked responses."""

    @patch("cli_web.reddit.core.client.curl_requests.Session")
    @patch("cli_web.reddit.core.client.get_bearer_token", return_value=None)
    def test_feed_hot(self, mock_token, MockSession):
        from cli_web.reddit.core.client import RedditClient

        session = MagicMock()
        MockSession.return_value = session
        session.get.return_value = _mock_response(json_data=SAMPLE_LISTING)

        client = RedditClient()
        data = client.feed_hot(limit=3)
        assert data["data"]["children"][0]["kind"] == "t3"

    @patch("cli_web.reddit.core.client.curl_requests.Session")
    @patch("cli_web.reddit.core.client.get_bearer_token", return_value=None)
    def test_404_raises_not_found(self, mock_token, MockSession):
        from cli_web.reddit.core.client import RedditClient

        session = MagicMock()
        MockSession.return_value = session
        session.get.side_effect = [_mock_response(200), _mock_response(404)]

        client = RedditClient()
        with pytest.raises(NotFoundError):
            client.feed_hot()

    @patch("cli_web.reddit.core.client.curl_requests.Session")
    @patch("cli_web.reddit.core.client.get_bearer_token", return_value=None)
    def test_429_raises_rate_limit(self, mock_token, MockSession):
        from cli_web.reddit.core.client import RedditClient

        session = MagicMock()
        MockSession.return_value = session
        session.get.side_effect = [
            _mock_response(200),
            _mock_response(429, headers={"retry-after": "60"}),
        ]

        client = RedditClient()
        with pytest.raises(RateLimitError) as exc_info:
            client.feed_hot()
        assert exc_info.value.retry_after == 60.0

    @patch("cli_web.reddit.core.client.curl_requests.Session")
    @patch("cli_web.reddit.core.client.get_bearer_token", return_value=None)
    def test_500_raises_server_error(self, mock_token, MockSession):
        from cli_web.reddit.core.client import RedditClient

        session = MagicMock()
        MockSession.return_value = session
        session.get.side_effect = [_mock_response(200), _mock_response(500)]

        client = RedditClient()
        with pytest.raises(ServerError) as exc_info:
            client.feed_hot()
        assert exc_info.value.status_code == 500

    @patch("cli_web.reddit.core.client.curl_requests.Session")
    @patch("cli_web.reddit.core.client.get_bearer_token", return_value=None)
    def test_403_raises_auth_error(self, mock_token, MockSession):
        from cli_web.reddit.core.client import RedditClient

        session = MagicMock()
        MockSession.return_value = session
        session.get.side_effect = [_mock_response(200), _mock_response(403)]

        client = RedditClient()
        with pytest.raises(AuthError):
            client.feed_hot()

    @patch("cli_web.reddit.core.client.curl_requests.Session")
    @patch("cli_web.reddit.core.client.get_bearer_token", return_value=None)
    def test_generic_4xx_raises_reddit_error(self, mock_token, MockSession):
        from cli_web.reddit.core.client import RedditClient

        session = MagicMock()
        MockSession.return_value = session
        session.get.side_effect = [_mock_response(200), _mock_response(418, text="I'm a teapot")]

        client = RedditClient()
        with pytest.raises(RedditError):
            client.feed_hot()

    @patch("cli_web.reddit.core.client.curl_requests.Session")
    @patch("cli_web.reddit.core.client.get_bearer_token", return_value=None)
    def test_network_error(self, mock_token, MockSession):
        from cli_web.reddit.core.client import RedditClient

        session = MagicMock()
        MockSession.return_value = session
        session.get.side_effect = [_mock_response(200), ConnectionError("fail")]

        client = RedditClient()
        with pytest.raises(NetworkError):
            client.feed_hot()


# ── Helpers tests ──────────────────────────────────────────────


@pytest.mark.unit
class TestHelpers:
    """Test shared utility functions."""

    def test_json_error(self):
        result = json.loads(json_error("NOT_FOUND", "Item not found"))
        assert result["error"] is True
        assert result["code"] == "NOT_FOUND"
        assert result["message"] == "Item not found"

    def test_json_error_with_extra(self):
        result = json.loads(json_error("RATE_LIMITED", "Too fast", retry_after=60))
        assert result["retry_after"] == 60

    def test_truncate_long(self):
        assert truncate("a" * 100, 10) == "a" * 10 + "..."

    def test_truncate_short(self):
        assert truncate("short", 50) == "short"

    def test_truncate_none(self):
        assert truncate(None) == ""

    def test_truncate_empty(self):
        assert truncate("") == ""

    def test_handle_errors_not_found_exit_1(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise NotFoundError("gone")
        assert exc.value.code == 1

    def test_handle_errors_server_error_exit_2(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise ServerError("down", status_code=503)
        assert exc.value.code == 2

    def test_handle_errors_network_error_exit_2(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise NetworkError("timeout")
        assert exc.value.code == 2

    def test_handle_errors_keyboard_interrupt_exit_130(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise KeyboardInterrupt()
        assert exc.value.code == 130

    def test_handle_errors_json_mode_not_found(self, capsys):
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise NotFoundError("gone")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["code"] == "NOT_FOUND"

    def test_handle_errors_json_mode_server_error(self, capsys):
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise ServerError("down")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["code"] == "SERVER_ERROR"

    def test_handle_errors_json_mode_network_error(self, capsys):
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise NetworkError("dns fail")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["code"] == "NETWORK_ERROR"

    def test_handle_errors_rate_limit_exit_1(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise RateLimitError("slow down", retry_after=30)
        assert exc.value.code == 1

    def test_resolve_json_mode_explicit_true(self):
        assert resolve_json_mode(True) is True

    def test_resolve_json_mode_explicit_false_no_ctx(self):
        assert resolve_json_mode(False) is False


# ── CLI Click tests ──────────────────────────────────────────


@pytest.mark.unit
class TestCLIClick:
    """Test CLI commands with Click test runner and mocked client."""

    def test_version(self):
        from cli_web.reddit.reddit_cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self):
        from cli_web.reddit.reddit_cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "feed" in result.output.lower()

    @patch("cli_web.reddit.commands.feed.RedditClient")
    def test_feed_hot_json(self, MockClient):
        from cli_web.reddit.reddit_cli import cli

        instance = MockClient.return_value
        instance.feed_hot.return_value = SAMPLE_LISTING

        runner = CliRunner()
        result = runner.invoke(cli, ["feed", "hot", "--json", "--limit", "3"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "posts" in data
        assert len(data["posts"]) == 1

    @patch("cli_web.reddit.commands.search.RedditClient")
    def test_search_posts_json(self, MockClient):
        from cli_web.reddit.reddit_cli import cli

        instance = MockClient.return_value
        instance.search_posts.return_value = SAMPLE_LISTING

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "posts", "python", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "posts" in data

    @patch("cli_web.reddit.commands.feed.RedditClient")
    def test_root_json_flows_to_subcommand(self, MockClient):
        """Root --json flag should be inherited by subcommands."""
        from cli_web.reddit.reddit_cli import cli

        instance = MockClient.return_value
        instance.feed_hot.return_value = SAMPLE_LISTING

        runner = CliRunner()
        result = runner.invoke(cli, ["--json", "feed", "hot", "--limit", "3"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "posts" in data

    @patch("cli_web.reddit.commands.feed.RedditClient")
    def test_feed_hot_json_error_on_not_found(self, MockClient):
        from cli_web.reddit.reddit_cli import cli

        instance = MockClient.return_value
        instance.feed_hot.side_effect = NotFoundError("not found")

        runner = CliRunner()
        result = runner.invoke(cli, ["feed", "hot", "--json"])
        data = json.loads(result.output)
        assert data["error"] is True
        assert data["code"] == "NOT_FOUND"

    @patch("cli_web.reddit.commands.feed.RedditClient")
    def test_feed_new_json(self, MockClient):
        from cli_web.reddit.reddit_cli import cli

        instance = MockClient.return_value
        instance.feed_new.return_value = SAMPLE_LISTING

        runner = CliRunner()
        result = runner.invoke(cli, ["feed", "new", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "posts" in data

    @patch("cli_web.reddit.commands.search.RedditClient")
    def test_search_posts_json_error_on_network(self, MockClient):
        from cli_web.reddit.reddit_cli import cli

        instance = MockClient.return_value
        instance.search_posts.side_effect = NetworkError("timeout")

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "posts", "test", "--json"])
        data = json.loads(result.output)
        assert data["error"] is True
        assert data["code"] == "NETWORK_ERROR"
