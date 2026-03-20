"""Unit tests for cli-web-unsplash core modules."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import httpx
import pytest

from cli_web.unsplash.core.client import UnsplashClient
from cli_web.unsplash.core.exceptions import (
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    UnsplashError,
)
from cli_web.unsplash.core.models import (
    format_collection_summary,
    format_photo_detail,
    format_photo_summary,
    format_topic_summary,
    format_user_summary,
)
from cli_web.unsplash.utils.helpers import handle_errors, json_error, truncate


# ── Exception hierarchy tests ────────────────────────────────────

class TestExceptionHierarchy:
    def test_all_inherit_from_base(self):
        """All domain exceptions inherit from UnsplashError."""
        assert issubclass(NotFoundError, UnsplashError)
        assert issubclass(RateLimitError, UnsplashError)
        assert issubclass(ServerError, UnsplashError)
        assert issubclass(NetworkError, UnsplashError)

    def test_rate_limit_has_retry_after(self):
        exc = RateLimitError("limited", retry_after=60.0)
        assert exc.retry_after == 60.0

    def test_server_error_has_status_code(self):
        exc = ServerError("failed", status_code=503)
        assert exc.status_code == 503


# ── Client HTTP error mapping tests ─────────────────────────────

class TestClientErrorMapping:
    def _mock_response(self, status_code, json_data=None, text="", headers=None):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.text = text
        resp.headers = headers or {}
        if json_data is not None:
            resp.json.return_value = json_data
        return resp

    @patch("cli_web.unsplash.core.client.httpx.Client")
    def test_404_raises_not_found(self, mock_http_cls):
        mock_http = MagicMock()
        mock_http_cls.return_value = mock_http
        mock_http.get.return_value = self._mock_response(404)

        client = UnsplashClient()
        with pytest.raises(NotFoundError):
            client.get_photo("nonexistent")

    @patch("cli_web.unsplash.core.client.httpx.Client")
    def test_429_raises_rate_limit(self, mock_http_cls):
        mock_http = MagicMock()
        mock_http_cls.return_value = mock_http
        mock_http.get.return_value = self._mock_response(
            429, headers={"retry-after": "30"}
        )

        client = UnsplashClient()
        with pytest.raises(RateLimitError) as exc_info:
            client.search_photos("test")
        assert exc_info.value.retry_after == 30.0

    @patch("cli_web.unsplash.core.client.httpx.Client")
    def test_500_raises_server_error(self, mock_http_cls):
        mock_http = MagicMock()
        mock_http_cls.return_value = mock_http
        mock_http.get.return_value = self._mock_response(500)

        client = UnsplashClient()
        with pytest.raises(ServerError) as exc_info:
            client.list_topics()
        assert exc_info.value.status_code == 500

    @patch("cli_web.unsplash.core.client.httpx.Client")
    def test_timeout_raises_network_error(self, mock_http_cls):
        mock_http = MagicMock()
        mock_http_cls.return_value = mock_http
        mock_http.get.side_effect = httpx.TimeoutException("timeout")

        client = UnsplashClient()
        with pytest.raises(NetworkError):
            client.get_user("test")

    @patch("cli_web.unsplash.core.client.httpx.Client")
    def test_connect_error_raises_network_error(self, mock_http_cls):
        mock_http = MagicMock()
        mock_http_cls.return_value = mock_http
        mock_http.get.side_effect = httpx.ConnectError("failed")

        client = UnsplashClient()
        with pytest.raises(NetworkError):
            client.get_topic("test")

    @patch("cli_web.unsplash.core.client.httpx.Client")
    def test_successful_json_response(self, mock_http_cls):
        mock_http = MagicMock()
        mock_http_cls.return_value = mock_http
        expected = {"id": "abc", "slug": "test-photo-abc"}
        mock_http.get.return_value = self._mock_response(200, json_data=expected)

        client = UnsplashClient()
        result = client.get_photo("abc")
        assert result == expected


# ── Client method parameter tests ────────────────────────────────

class TestClientMethods:
    @patch("cli_web.unsplash.core.client.httpx.Client")
    def test_search_photos_passes_params(self, mock_http_cls):
        mock_http = MagicMock()
        mock_http_cls.return_value = mock_http
        mock_http.get.return_value = self._mock_response(
            200, json_data={"total": 0, "results": []}
        )

        client = UnsplashClient()
        client.search_photos("cats", page=2, per_page=10, orientation="landscape", color="blue")

        mock_http.get.assert_called_once()
        call_args = mock_http.get.call_args
        assert call_args[0][0] == "/napi/search/photos"
        params = call_args[1]["params"]
        assert params["query"] == "cats"
        assert params["page"] == 2
        assert params["per_page"] == 10
        assert params["orientation"] == "landscape"
        assert params["color"] == "blue"

    @patch("cli_web.unsplash.core.client.httpx.Client")
    def test_search_photos_omits_none_params(self, mock_http_cls):
        mock_http = MagicMock()
        mock_http_cls.return_value = mock_http
        mock_http.get.return_value = self._mock_response(
            200, json_data={"total": 0, "results": []}
        )

        client = UnsplashClient()
        client.search_photos("dogs")

        params = mock_http.get.call_args[1]["params"]
        assert "orientation" not in params
        assert "color" not in params

    @patch("cli_web.unsplash.core.client.httpx.Client")
    def test_get_random_photos_params(self, mock_http_cls):
        mock_http = MagicMock()
        mock_http_cls.return_value = mock_http
        mock_http.get.return_value = self._mock_response(200, json_data=[])

        client = UnsplashClient()
        client.get_random_photos(count=3, query="nature", orientation="portrait")

        params = mock_http.get.call_args[1]["params"]
        assert params["count"] == 3
        assert params["query"] == "nature"
        assert params["orientation"] == "portrait"

    def _mock_response(self, status_code, json_data=None):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.headers = {}
        if json_data is not None:
            resp.json.return_value = json_data
        return resp


# ── Model formatting tests ───────────────────────────────────────

class TestModels:
    SAMPLE_PHOTO = {
        "id": "abc123",
        "slug": "sunset-over-ocean-abc123",
        "width": 4000,
        "height": 3000,
        "color": "#FF5733",
        "description": "A beautiful sunset",
        "alt_description": "sunset over the ocean",
        "likes": 42,
        "views": 1000,
        "downloads": 200,
        "created_at": "2024-01-15T10:00:00Z",
        "premium": False,
        "user": {"id": "u1", "username": "photographer", "name": "Photo Grapher"},
        "urls": {"raw": "https://raw", "regular": "https://regular"},
        "exif": {"make": "Canon", "model": "EOS R5", "aperture": "2.8", "exposure_time": "1/500", "focal_length": "50", "iso": 200},
        "location": {"name": "Malibu, CA", "city": "Malibu", "country": "USA", "position": {"latitude": 34.03, "longitude": -118.68}},
        "tags": [{"title": "sunset"}, {"title": "ocean"}, {"title": "sky"}],
    }

    def test_format_photo_summary(self):
        result = format_photo_summary(self.SAMPLE_PHOTO)
        assert result["id"] == "abc123"
        assert result["description"] == "sunset over the ocean"
        assert result["width"] == 4000
        assert result["likes"] == 42
        assert result["author"] == "Photo Grapher"
        assert "abc123" in result["link"]

    def test_format_photo_summary_fallback_description(self):
        photo = {**self.SAMPLE_PHOTO, "alt_description": None}
        result = format_photo_summary(photo)
        assert result["description"] == "A beautiful sunset"

    def test_format_photo_detail(self):
        result = format_photo_detail(self.SAMPLE_PHOTO)
        assert result["id"] == "abc123"
        assert result["views"] == 1000
        assert result["downloads"] == 200
        assert result["exif"]["camera"] == "Canon EOS R5"
        assert result["location"]["name"] == "Malibu, CA"
        assert result["tags"] == ["sunset", "ocean", "sky"]

    def test_format_user_summary(self):
        user = {
            "username": "jdoe", "name": "John Doe", "bio": "Photographer",
            "location": "NYC", "total_photos": 100, "total_likes": 500,
            "total_collections": 10,
        }
        result = format_user_summary(user)
        assert result["username"] == "jdoe"
        assert result["total_photos"] == 100
        assert "@jdoe" in result["link"]

    def test_format_collection_summary(self):
        coll = {
            "id": 42, "title": "Nature", "description": "Nature photos",
            "total_photos": 250, "user": {"name": "Jane", "username": "jane"},
        }
        result = format_collection_summary(coll)
        assert result["id"] == 42
        assert result["title"] == "Nature"
        assert result["author"] == "Jane"

    def test_format_topic_summary(self):
        topic = {
            "slug": "nature", "title": "Nature", "description": "A topic",
            "total_photos": 5000, "featured": True,
        }
        result = format_topic_summary(topic)
        assert result["slug"] == "nature"
        assert result["featured"] is True
        assert "/t/nature" in result["link"]


# ── Helper function tests ────────────────────────────────────────

class TestHelpers:
    def test_json_error_format(self):
        result = json.loads(json_error("NOT_FOUND", "Photo xyz not found"))
        assert result["error"] is True
        assert result["code"] == "NOT_FOUND"
        assert "xyz" in result["message"]

    def test_json_error_extra_fields(self):
        result = json.loads(json_error("RATE_LIMITED", "Too fast", retry_after=60))
        assert result["retry_after"] == 60

    def test_truncate_short_text(self):
        assert truncate("hello", 10) == "hello"

    def test_truncate_long_text(self):
        assert truncate("a" * 100, 10) == "a" * 10 + "..."

    def test_truncate_none(self):
        assert truncate(None, 10) == ""

    def test_handle_errors_not_found_exits_1(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise NotFoundError("missing")
        assert exc.value.code == 1

    def test_handle_errors_server_error_exits_2(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise ServerError("down", status_code=500)
        assert exc.value.code == 2

    def test_handle_errors_network_error_exits_2(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise NetworkError("no connection")
        assert exc.value.code == 2

    def test_handle_errors_json_mode_outputs_json(self, capsys):
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise NotFoundError("Photo xyz not found")
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["error"] is True
        assert data["code"] == "NOT_FOUND"

    def test_handle_errors_keyboard_interrupt_exits_130(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise KeyboardInterrupt()
        assert exc.value.code == 130


# ── CLI Click integration tests ──────────────────────────────────

class TestCLIClick:
    @pytest.fixture
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    def test_version_flag(self, runner):
        from cli_web.unsplash.unsplash_cli import cli
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help_flag(self, runner):
        from cli_web.unsplash.unsplash_cli import cli
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "photos" in result.output
        assert "topics" in result.output
        assert "collections" in result.output
        assert "users" in result.output

    def test_photos_search_json(self, runner):
        from cli_web.unsplash.unsplash_cli import cli

        mock_data = {"total": 1, "total_pages": 1, "results": [{
            "id": "x1", "slug": "test-x1", "width": 100, "height": 100,
            "alt_description": "test", "description": None, "likes": 5,
            "color": "#000", "premium": False, "user": {"name": "A", "username": "a"},
            "urls": {"regular": "https://img"},
        }]}
        with patch("cli_web.unsplash.commands.photos.UnsplashClient") as MockClient:
            MockClient.return_value.search_photos.return_value = mock_data
            result = runner.invoke(cli, ["photos", "search", "test", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total"] == 1
        assert data["results"][0]["id"] == "x1"

    def test_photos_get_json(self, runner):
        from cli_web.unsplash.unsplash_cli import cli

        mock_photo = {
            "id": "abc", "slug": "test-abc", "width": 800, "height": 600,
            "description": "test", "alt_description": "alt test", "likes": 10,
            "views": 100, "downloads": 50, "created_at": "2024-01-01T00:00:00Z",
            "color": "#fff", "premium": False, "user": {"username": "u", "name": "U"},
            "urls": {}, "exif": {}, "location": {}, "tags": [],
        }
        with patch("cli_web.unsplash.commands.photos.UnsplashClient") as MockClient:
            MockClient.return_value.get_photo.return_value = mock_photo
            result = runner.invoke(cli, ["photos", "get", "abc", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "abc"

    def test_topics_list_json(self, runner):
        from cli_web.unsplash.unsplash_cli import cli

        mock_topics = [
            {"slug": "nature", "title": "Nature", "description": "", "total_photos": 5000, "featured": True},
        ]
        with patch("cli_web.unsplash.commands.topics.UnsplashClient") as MockClient:
            MockClient.return_value.list_topics.return_value = mock_topics
            result = runner.invoke(cli, ["topics", "list", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["slug"] == "nature"

    def test_json_error_on_not_found(self, runner):
        from cli_web.unsplash.unsplash_cli import cli

        with patch("cli_web.unsplash.commands.photos.UnsplashClient") as MockClient:
            MockClient.return_value.get_photo.side_effect = NotFoundError("not found")
            result = runner.invoke(cli, ["photos", "get", "bad", "--json"])

        data = json.loads(result.output)
        assert data["error"] is True
        assert data["code"] == "NOT_FOUND"
