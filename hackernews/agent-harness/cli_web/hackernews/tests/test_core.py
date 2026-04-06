"""Unit tests for cli-web-hackernews core modules (mocked HTTP, no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from cli_web.hackernews.core.client import HackerNewsClient
from cli_web.hackernews.core.exceptions import (
    AppError,
    AuthError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from cli_web.hackernews.core.models import Comment, SearchResult, Story, User


# ─── Model tests ─────────────────────────────────────────────────────────────


class TestStoryModel:
    def test_to_dict_includes_computed(self):
        story = Story(
            id=123,
            title="Test Story",
            url="https://example.com/article",
            score=42,
            by="testuser",
            time=0,
            descendants=5,
        )
        d = story.to_dict()
        assert d["id"] == 123
        assert d["title"] == "Test Story"
        assert d["domain"] == "example.com"
        assert "age" in d

    def test_domain_extraction(self):
        story = Story(id=1, title="T", url="https://www.example.com/path")
        assert story.domain == "example.com"

    def test_domain_empty_when_no_url(self):
        story = Story(id=1, title="T")
        assert story.domain == ""

    def test_age_empty_when_no_time(self):
        story = Story(id=1, title="T")
        assert story.age == ""


class TestCommentModel:
    def test_text_plain_strips_html(self):
        comment = Comment(id=1, text="<p>Hello <b>world</b></p>")
        assert comment.text_plain == "Hello world"

    def test_text_plain_unescapes_entities(self):
        comment = Comment(id=1, text="&amp; &lt;tag&gt;")
        assert comment.text_plain == "& <tag>"

    def test_text_plain_empty(self):
        comment = Comment(id=1)
        assert comment.text_plain == ""


class TestUserModel:
    def test_to_dict_trims_submitted(self):
        user = User(id="test", submitted=list(range(100)))
        d = user.to_dict()
        assert len(d["submitted"]) == 20
        assert d["total_submissions"] == 100

    def test_about_plain(self):
        user = User(id="test", about="<p>Hello &amp; welcome</p>")
        assert user.about_plain == "Hello & welcome"


class TestSearchResultModel:
    def test_to_dict(self):
        result = SearchResult(
            objectID="123",
            title="Test",
            author="user",
            points=42,
            num_comments=10,
        )
        d = result.to_dict()
        assert d["objectID"] == "123"
        assert d["points"] == 42


# ─── Client HTTP error handling tests ───────────────────────────────────────


class TestClientHTTPErrors:
    def _mock_response(self, status_code: int, headers: dict | None = None, json_data=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.headers = headers or {}
        resp.json.return_value = json_data
        return resp

    def test_rate_limit_raises(self):
        client = HackerNewsClient()
        client._client = MagicMock()
        client._client.get.return_value = self._mock_response(
            429, headers={"retry-after": "30"}
        )
        with pytest.raises(RateLimitError) as exc_info:
            client._get_json("https://hacker-news.firebaseio.com/v0/topstories.json")
        assert exc_info.value.retry_after == 30

    def test_server_error_raises(self):
        client = HackerNewsClient()
        client._client = MagicMock()
        client._client.get.return_value = self._mock_response(503)
        with pytest.raises(ServerError):
            client._get_json("https://hacker-news.firebaseio.com/v0/topstories.json")

    def test_404_raises_not_found(self):
        client = HackerNewsClient()
        client._client = MagicMock()
        client._client.get.return_value = self._mock_response(404)
        with pytest.raises(NotFoundError):
            client._get_json("https://hacker-news.firebaseio.com/v0/item/999999999.json")

    def test_network_error_raises(self):
        client = HackerNewsClient()
        client._client = MagicMock()
        client._client.get.side_effect = httpx.ConnectError("Connection refused")
        with pytest.raises(NetworkError):
            client._get_json("https://hacker-news.firebaseio.com/v0/topstories.json")

    def test_timeout_raises_network_error(self):
        client = HackerNewsClient()
        client._client = MagicMock()
        client._client.get.side_effect = httpx.TimeoutException("Timed out")
        with pytest.raises(NetworkError):
            client._get_json("https://hacker-news.firebaseio.com/v0/topstories.json")


# ─── Client data parsing tests ──────────────────────────────────────────────


class TestClientParsing:
    def test_get_story_builds_model(self):
        mock_data = {
            "id": 123,
            "title": "Test Story",
            "url": "https://example.com",
            "score": 42,
            "by": "user",
            "time": 1700000000,
            "descendants": 5,
            "type": "story",
        }
        with patch.object(HackerNewsClient, "get_item", return_value=mock_data):
            client = HackerNewsClient()
            story = client.get_story(123)
            assert isinstance(story, Story)
            assert story.id == 123
            assert story.title == "Test Story"
            assert story.score == 42

    def test_get_user_builds_model(self):
        mock_data = {
            "id": "testuser",
            "karma": 1000,
            "created": 1187454947,
            "about": "Hi",
            "submitted": [1, 2, 3],
        }
        with patch.object(HackerNewsClient, "_get_json", return_value=mock_data):
            client = HackerNewsClient()
            user = client.get_user("testuser")
            assert isinstance(user, User)
            assert user.id == "testuser"
            assert user.karma == 1000

    def test_get_user_not_found(self):
        with patch.object(HackerNewsClient, "_get_json", return_value=None):
            client = HackerNewsClient()
            with pytest.raises(NotFoundError):
                client.get_user("nonexistent")

    def test_search_builds_results(self):
        mock_data = {
            "hits": [
                {
                    "objectID": "123",
                    "title": "Result 1",
                    "url": "https://example.com",
                    "author": "user",
                    "points": 42,
                    "num_comments": 10,
                    "created_at": "2024-01-01T00:00:00Z",
                },
            ]
        }
        with patch.object(HackerNewsClient, "_get_json", return_value=mock_data):
            client = HackerNewsClient()
            results = client.search("test")
            assert len(results) == 1
            assert results[0].objectID == "123"
            assert results[0].points == 42


# ─── Exception serialization tests ──────────────────────────────────────────


class TestExceptionsToDicts:
    def test_app_error_to_dict(self):
        exc = AppError("something broke", "TEST_ERROR")
        d = exc.to_dict()
        assert d["error"] is True
        assert d["code"] == "TEST_ERROR"
        assert "something broke" in d["message"]

    def test_rate_limit_error_to_dict(self):
        exc = RateLimitError(60)
        d = exc.to_dict()
        assert d["code"] == "RATE_LIMITED"
        assert d["retry_after"] == 60

    def test_server_error_to_dict(self):
        exc = ServerError(503)
        d = exc.to_dict()
        assert d["code"] == "SERVER_ERROR"
        assert "503" in d["message"]

    def test_not_found_to_dict(self):
        exc = NotFoundError("Item 123")
        d = exc.to_dict()
        assert d["code"] == "NOT_FOUND"
        assert "Item 123" in d["message"]

    def test_auth_error_to_dict(self):
        exc = AuthError()
        d = exc.to_dict()
        assert d["error"] is True
        assert d["code"] == "AUTH_EXPIRED"
        assert "login" in d["message"].lower()

    def test_auth_error_recoverable(self):
        exc = AuthError("token expired", recoverable=True)
        assert exc.recoverable is True


# ─── Auth module tests ───────────────────────────────────────────────────────


class TestAuthModule:
    def test_require_auth_raises_without_cookie(self):
        client = HackerNewsClient()
        with pytest.raises(AuthError):
            client._require_auth()

    def test_require_auth_returns_cookie(self):
        client = HackerNewsClient(user_cookie="test_cookie")
        assert client._require_auth() == "test_cookie"

    def test_extract_auth_token_from_html(self):
        html = '<a id="up_12345" href="vote?id=12345&amp;how=up&amp;auth=abc123def456"></a>'
        client = HackerNewsClient(user_cookie="test")
        token = client._extract_auth_token(html, 12345)
        assert token == "abc123def456"

    def test_extract_auth_token_missing_raises(self):
        html = "<html><body>No tokens here</body></html>"
        client = HackerNewsClient(user_cookie="test")
        with pytest.raises(AuthError):
            client._extract_auth_token(html, 99999)

    def test_parse_stories_from_html_extracts_ids(self):
        html = '''
        <tr class="athing submission" id="12345"><td></td></tr>
        <tr class="athing submission" id="67890"><td></td></tr>
        '''
        client = HackerNewsClient(user_cookie="test")
        # Mock _fetch_items_parallel to return stories based on IDs
        with patch.object(client, "_fetch_items_parallel", return_value=[
            Story(id=12345, title="Story 1"),
            Story(id=67890, title="Story 2"),
        ]):
            stories = client._parse_stories_from_html(html)
            assert len(stories) == 2

    def test_authenticated_get_html_403_raises_auth_error(self):
        client = HackerNewsClient(user_cookie="expired_cookie")
        resp = MagicMock()
        resp.status_code = 403
        client._web_client = MagicMock()
        client._web_client.get.return_value = resp
        with pytest.raises(AuthError):
            client._get_html("https://news.ycombinator.com/item?id=1")
