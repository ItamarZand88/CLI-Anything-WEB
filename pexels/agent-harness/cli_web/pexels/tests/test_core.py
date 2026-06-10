"""Unit tests for cli-web-pexels core modules."""

import json
from unittest.mock import MagicMock, patch

import pytest
from cli_web.pexels.core.client import PexelsClient
from cli_web.pexels.core.exceptions import (
    NetworkError,
    NotFoundError,
    ParseError,
    PexelsError,
    RateLimitError,
    ServerError,
    error_code_for,
)
from cli_web.pexels.core.models import (
    normalize_collection,
    normalize_photo,
    normalize_user,
    normalize_video_detail,
)
from cli_web.pexels.utils.helpers import handle_errors, sanitize_filename
from cli_web.pexels.utils.output import print_json, print_pagination

# ── Exception hierarchy tests ─────────────────────────────────────────


class TestExceptionHierarchy:
    def test_pexels_error_is_base(self):
        assert issubclass(RateLimitError, PexelsError)
        assert issubclass(ServerError, PexelsError)
        assert issubclass(NotFoundError, PexelsError)
        assert issubclass(NetworkError, PexelsError)
        assert issubclass(ParseError, PexelsError)

    def test_rate_limit_error_stores_retry_after(self):
        exc = RateLimitError("slow down", retry_after=30.0)
        assert exc.retry_after == 30.0
        assert str(exc) == "slow down"

    def test_rate_limit_error_retry_after_none(self):
        exc = RateLimitError("slow down")
        assert exc.retry_after is None

    def test_server_error_stores_status_code(self):
        exc = ServerError("bad gateway", status_code=502)
        assert exc.status_code == 502
        assert str(exc) == "bad gateway"

    def test_server_error_default_status(self):
        exc = ServerError("fail")
        assert exc.status_code == 500

    def test_error_code_for_known(self):
        assert error_code_for(RateLimitError("x")) == "RATE_LIMITED"
        assert error_code_for(NotFoundError("x")) == "NOT_FOUND"
        assert error_code_for(ServerError("x")) == "SERVER_ERROR"
        assert error_code_for(NetworkError("x")) == "NETWORK_ERROR"
        assert error_code_for(ParseError("x")) == "PARSE_ERROR"

    def test_error_code_for_unknown(self):
        assert error_code_for(ValueError("x")) == "UNKNOWN_ERROR"


# ── Client __NEXT_DATA__ parsing tests ────────────────────────────────


NEXT_DATA_HTML = (
    "<html><head></head><body>"
    '<script id="__NEXT_DATA__" type="application/json">'
    '{"props":{"pageProps":{"initialData":{"data":[{"attributes":{"id":1}}],'
    '"pagination":{"current_page":1,"total_pages":5}}}}}'
    "</script></body></html>"
)

NO_NEXT_DATA_HTML = "<html><head></head><body><p>No data here</p></body></html>"


class TestClientParsing:
    @patch("cli_web.pexels.core.client.curl_requests.get")
    def test_get_page_extracts_page_props(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = NEXT_DATA_HTML
        mock_get.return_value = mock_resp

        client = PexelsClient()
        result = client._get_page("/search/cats/")

        assert "initialData" in result
        assert result["initialData"]["data"][0]["attributes"]["id"] == 1

    @patch("cli_web.pexels.core.client.curl_requests.get")
    def test_get_page_raises_parse_error_no_next_data(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = NO_NEXT_DATA_HTML
        mock_get.return_value = mock_resp

        client = PexelsClient()
        with pytest.raises(ParseError, match="No __NEXT_DATA__"):
            client._get_page("/search/cats/")

    def test_check_status_404(self):
        resp = MagicMock()
        resp.status_code = 404
        resp.text = "page not found"
        with pytest.raises(NotFoundError):
            PexelsClient._check_status(resp, "https://pexels.com/x")

    def test_check_status_429(self):
        resp = MagicMock()
        resp.status_code = 429
        resp.text = "rate limited"
        resp.headers = {"Retry-After": "10"}
        with pytest.raises(RateLimitError) as exc_info:
            PexelsClient._check_status(resp, "https://pexels.com/x")
        assert exc_info.value.retry_after == 10.0

    def test_check_status_500(self):
        resp = MagicMock()
        resp.status_code = 503
        resp.text = "service unavailable"
        with pytest.raises(ServerError) as exc_info:
            PexelsClient._check_status(resp, "https://pexels.com/x")
        assert exc_info.value.status_code == 503


# ── Normalizer tests ──────────────────────────────────────────────────


class TestNormalizers:
    def test_normalize_photo(self):
        item = {
            "attributes": {
                "id": 1072179,
                "slug": "green-leaves-1072179",
                "title": "Green Leaves",
                "description": "Beautiful leaves",
                "width": 4000,
                "height": 3000,
                "license": "free",
                "user": {"first_name": "John", "last_name": "Doe", "username": "johndoe"},
                "image": {
                    "large": "https://img.pexels.com/large.jpg",
                    "download_link": "https://dl.pexels.com/1072179",
                },
                "tags": [{"name": "nature"}, {"name": "green"}],
                "colors": ["#2E8B57"],
            }
        }
        result = normalize_photo(item)
        assert result["id"] == 1072179
        assert result["type"] == "photo"
        assert result["photographer"] == "John Doe"
        assert result["photographer_username"] == "johndoe"
        assert result["image_url"] == "https://img.pexels.com/large.jpg"
        assert result["tags"] == ["nature", "green"]

    def test_normalize_video_detail(self):
        medium = {
            "attributes": {
                "id": 5000,
                "slug": "sunset-5000",
                "title": "Sunset Timelapse",
                "description": "A timelapse of a sunset",
                "width": 1920,
                "height": 1080,
                "license": "free",
                "created_at": "2024-01-15",
                "user": {
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "username": "jsmith",
                    "slug": "jsmith-123",
                },
                "video": {
                    "thumbnail": {
                        "small": "https://thumb/s.jpg",
                        "medium": "https://thumb/m.jpg",
                        "large": "https://thumb/l.jpg",
                    },
                    "src": "https://video/src.mp4",
                    "preview_src": "https://video/preview.mp4",
                    "video_files": [
                        {
                            "quality": "hd",
                            "width": 1920,
                            "height": 1080,
                            "fps": 30.0,
                            "file_type": "video/mp4",
                            "link": "https://dl/hd.mp4",
                        },
                        {
                            "quality": "sd",
                            "width": 960,
                            "height": 540,
                            "fps": 25.0,
                            "file_type": "video/mp4",
                            "link": "https://dl/sd.mp4",
                        },
                    ],
                },
                "tags": [{"name": "sunset"}, {"name": "timelapse"}],
            }
        }
        result = normalize_video_detail(medium)
        assert result["id"] == 5000
        assert result["type"] == "video"
        assert result["photographer"] == "Jane Smith"
        assert len(result["video_files"]) == 2
        assert result["video_files"][0]["quality"] == "hd"
        assert result["video_files"][1]["link"] == "https://dl/sd.mp4"
        assert result["video_src"] == "https://video/src.mp4"
        assert result["tags"] == ["sunset", "timelapse"]

    def test_normalize_user(self):
        user = {
            "attributes": {
                "id": 42,
                "username": "naturephotog",
                "first_name": "Alice",
                "last_name": "Wonderland",
                "location": "London, UK",
                "bio": "Loves nature",
                "avatar": {"medium": "https://avatar/m.jpg", "small": "https://avatar/s.jpg"},
                "photos_count": 150,
                "media_count": 200,
                "followers_count": 5000,
                "hero": True,
                "slug": "naturephotog-42",
            }
        }
        result = normalize_user(user)
        assert result["id"] == 42
        assert result["username"] == "naturephotog"
        assert result["first_name"] == "Alice"
        assert result["location"] == "London, UK"
        assert result["avatar"] == "https://avatar/m.jpg"
        assert result["hero"] is True
        assert result["url"] == "https://www.pexels.com/@naturephotog-42"

    def test_normalize_collection(self):
        collection = {
            "attributes": {
                "id": 99,
                "title": "Mountain Views",
                "description": "Epic mountain shots",
                "slug": "mountain-views-99",
                "collection_media_count": 50,
                "photos_count": 40,
                "videos_count": 10,
            }
        }
        result = normalize_collection(collection)
        assert result["id"] == 99
        assert result["title"] == "Mountain Views"
        assert result["media_count"] == 50
        assert result["photos_count"] == 40
        assert result["videos_count"] == 10


# ── Helper tests ──────────────────────────────────────────────────────


class TestHelpers:
    def test_sanitize_filename_removes_invalid_chars(self):
        assert sanitize_filename('photo/of:stars*"cool"') == "photo_of_stars__cool_"

    def test_sanitize_filename_empty_string(self):
        assert sanitize_filename("") == "untitled"

    def test_sanitize_filename_whitespace_only(self):
        assert sanitize_filename("   ") == "untitled"

    def test_sanitize_filename_truncates(self):
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) == 240

    def test_handle_errors_catches_pexels_error(self):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors(json_mode=False):
                raise NotFoundError("no such photo")
        assert exc_info.value.code == 1

    def test_handle_errors_catches_unknown_exception(self):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors(json_mode=False):
                raise ValueError("unexpected")
        assert exc_info.value.code == 2

    def test_handle_errors_json_mode(self, capsys):
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise NotFoundError("missing resource")
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["error"] is True
        assert data["code"] == "NOT_FOUND"
        assert "missing resource" in data["message"]


# ── Output tests ──────────────────────────────────────────────────────


class TestOutput:
    def test_print_json_valid(self, capsys):
        print_json({"id": 1, "title": "Test"})
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["id"] == 1
        assert data["title"] == "Test"

    def test_print_pagination_shows_info(self, capsys):
        pagination = {"current_page": 2, "total_pages": 10, "total_results": 500}
        print_pagination(pagination)
        captured = capsys.readouterr()
        assert "Page 2/10" in captured.out
        assert "500" in captured.out

    def test_print_pagination_empty(self, capsys):
        print_pagination({})
        captured = capsys.readouterr()
        assert captured.out == ""
