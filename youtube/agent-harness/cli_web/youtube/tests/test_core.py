"""Unit tests for cli-web-youtube core modules (mocked HTTP, no network)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from cli_web.youtube.core.exceptions import (
    AuthError,
    NetworkError,
    NotFoundError,
    ParseError,
    RateLimitError,
    ServerError,
    YouTubeError,
)
from cli_web.youtube.core.models import (
    format_channel,
    format_video_detail,
    format_video_from_renderer,
)
from cli_web.youtube.utils.helpers import handle_errors
from cli_web.youtube.youtube_cli import cli
from click.testing import CliRunner

# ── Sample Data ──────────────────────────────────────────────

SAMPLE_VIDEO_RENDERER = {
    "videoId": "abc123",
    "title": {"runs": [{"text": "Test Video Title"}]},
    "ownerText": {
        "runs": [
            {
                "text": "Test Channel",
                "navigationEndpoint": {"browseEndpoint": {"browseId": "UC_test123"}},
            }
        ]
    },
    "viewCountText": {"simpleText": "1,234,567 views"},
    "lengthText": {"simpleText": "10:30"},
    "publishedTimeText": {"simpleText": "2 days ago"},
    "thumbnail": {
        "thumbnails": [
            {"url": "https://i.ytimg.com/vi/abc123/default.jpg"},
            {"url": "https://i.ytimg.com/vi/abc123/hqdefault.jpg"},
        ]
    },
}

SAMPLE_VIDEO_DETAILS = {
    "videoId": "abc123",
    "title": "Full Video Title",
    "author": "Test Channel",
    "channelId": "UC_test123",
    "viewCount": "1234567",
    "lengthSeconds": "630",
    "shortDescription": "This is a test video description",
    "keywords": ["test", "python", "tutorial"],
    "thumbnail": {
        "thumbnails": [
            {"url": "https://i.ytimg.com/vi/abc123/maxresdefault.jpg"},
        ]
    },
    "isLiveContent": False,
}

SAMPLE_MICROFORMAT = {
    "playerMicroformatRenderer": {
        "publishDate": "2026-03-20",
        "category": "Education",
        "isFamilySafe": True,
    }
}

SAMPLE_SEARCH_RESPONSE = {
    "estimatedResults": "5000",
    "contents": {
        "twoColumnSearchResultsRenderer": {
            "primaryContents": {
                "sectionListRenderer": {
                    "contents": [
                        {
                            "itemSectionRenderer": {
                                "contents": [
                                    {"videoRenderer": SAMPLE_VIDEO_RENDERER},
                                    {
                                        "videoRenderer": {
                                            **SAMPLE_VIDEO_RENDERER,
                                            "videoId": "def456",
                                        }
                                    },
                                ]
                            }
                        }
                    ]
                }
            }
        }
    },
}

SAMPLE_PLAYER_RESPONSE = {
    "videoDetails": SAMPLE_VIDEO_DETAILS,
    "microformat": SAMPLE_MICROFORMAT,
}


# ── Model Tests ──────────────────────────────────────────────


class TestModels:
    def test_format_video_from_renderer(self):
        result = format_video_from_renderer(SAMPLE_VIDEO_RENDERER)
        assert result["id"] == "abc123"
        assert result["title"] == "Test Video Title"
        assert result["channel"] == "Test Channel"
        assert result["channel_id"] == "UC_test123"
        assert result["views"] == "1,234,567 views"
        assert result["duration"] == "10:30"
        assert result["published"] == "2 days ago"
        assert "youtube.com/watch?v=abc123" in result["url"]
        assert "hqdefault" in result["thumbnail"]

    def test_format_video_from_renderer_empty(self):
        result = format_video_from_renderer({})
        assert result["id"] == ""
        assert result["title"] == ""
        assert result["channel"] == ""

    def test_format_video_detail(self):
        result = format_video_detail(SAMPLE_VIDEO_DETAILS, SAMPLE_MICROFORMAT)
        assert result["id"] == "abc123"
        assert result["title"] == "Full Video Title"
        assert result["channel"] == "Test Channel"
        assert result["views"] == 1234567
        assert result["duration_seconds"] == 630
        assert result["keywords"] == ["test", "python", "tutorial"]
        assert result["publish_date"] == "2026-03-20"
        assert result["category"] == "Education"
        assert result["is_live"] is False

    def test_format_video_detail_no_microformat(self):
        result = format_video_detail(SAMPLE_VIDEO_DETAILS, None)
        assert result["id"] == "abc123"
        assert "publish_date" not in result

    def test_format_channel_page_header(self):
        header = {
            "pageHeaderRenderer": {
                "pageTitle": "Test Channel",
                "content": {
                    "pageHeaderViewModel": {
                        "description": {
                            "descriptionPreviewViewModel": {
                                "description": {"content": "About this channel"}
                            }
                        },
                        "metadata": {
                            "contentMetadataViewModel": {
                                "metadataRows": [
                                    {"metadataParts": [{"text": {"content": "1M subscribers"}}]},
                                    {"metadataParts": [{"text": {"content": "500 videos"}}]},
                                ]
                            }
                        },
                    }
                },
            }
        }
        result = format_channel(header)
        assert result["title"] == "Test Channel"
        assert result["subscriber_count"] == "1M subscribers"
        assert result["video_count"] == "500 videos"


# ── Exception Tests ──────────────────────────────────────────


class TestExceptions:
    def test_youtube_error_to_dict(self):
        exc = YouTubeError("something broke")
        d = exc.to_dict()
        assert d["error"] is True
        assert d["code"] == "YOUTUBE_ERROR"
        assert "something broke" in d["message"]

    def test_auth_error_code(self):
        exc = AuthError()
        assert exc.to_dict()["code"] == "AUTH_EXPIRED"
        assert exc.recoverable is False

    def test_rate_limit_to_dict_includes_retry_after(self):
        exc = RateLimitError(retry_after=60)
        d = exc.to_dict()
        assert d["code"] == "RATE_LIMITED"
        assert d["retry_after"] == 60

    def test_server_error_stores_status_code(self):
        exc = ServerError("Internal error", status_code=503)
        assert exc.status_code == 503
        assert exc.to_dict()["code"] == "SERVER_ERROR"

    def test_not_found_error(self):
        exc = NotFoundError("Video not found")
        assert exc.to_dict()["code"] == "NOT_FOUND"

    def test_parse_error(self):
        exc = ParseError("Bad JSON")
        assert exc.to_dict()["code"] == "PARSE_ERROR"

    def test_network_error(self):
        exc = NetworkError("Timeout")
        assert exc.to_dict()["code"] == "NETWORK_ERROR"


# ── Helper Tests ─────────────────────────────────────────────


class TestHelpers:
    def test_handle_errors_youtube_error_exits_1(self):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors():
                raise YouTubeError("test error")
        assert exc_info.value.code == 1

    def test_handle_errors_unexpected_exits_1(self):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors():
                raise ValueError("unexpected")
        assert exc_info.value.code == 1

    def test_handle_errors_json_mode_outputs_json(self, capsys):
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise NotFoundError("video xyz not found")
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["error"] is True
        assert data["code"] == "NOT_FOUND"

    def test_handle_errors_json_mode_rate_limit(self, capsys):
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise RateLimitError(retry_after=30)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["retry_after"] == 30


# ── Client Tests (Mocked) ───────────────────────────────────


class TestClientMocked:
    @patch("cli_web.youtube.core.client.httpx.Client")
    def test_search_returns_videos(self, mock_client_class):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_SEARCH_RESPONSE
        mock_session.post.return_value = mock_response
        mock_client_class.return_value = mock_session

        from cli_web.youtube.core.client import YouTubeClient

        client = YouTubeClient()
        result = client.search("python")
        assert result["query"] == "python"
        assert result["estimated_results"] == 5000
        assert len(result["videos"]) == 2
        assert result["videos"][0]["id"] == "abc123"

    @patch("cli_web.youtube.core.client.httpx.Client")
    def test_video_detail_returns_info(self, mock_client_class):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_PLAYER_RESPONSE
        mock_session.post.return_value = mock_response
        mock_client_class.return_value = mock_session

        from cli_web.youtube.core.client import YouTubeClient

        client = YouTubeClient()
        result = client.video_detail("abc123")
        assert result["id"] == "abc123"
        assert result["title"] == "Full Video Title"
        assert result["views"] == 1234567

    @patch("cli_web.youtube.core.client.httpx.Client")
    def test_404_raises_not_found(self, mock_client_class):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_session.post.return_value = mock_response
        mock_client_class.return_value = mock_session

        from cli_web.youtube.core.client import YouTubeClient

        client = YouTubeClient()
        with pytest.raises(NotFoundError):
            client.search("test")

    @patch("cli_web.youtube.core.client.httpx.Client")
    def test_429_raises_rate_limit(self, mock_client_class):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"retry-after": "60"}
        mock_session.post.return_value = mock_response
        mock_client_class.return_value = mock_session

        from cli_web.youtube.core.client import YouTubeClient

        client = YouTubeClient()
        with pytest.raises(RateLimitError) as exc_info:
            client.search("test")
        assert exc_info.value.retry_after == 60.0

    @patch("cli_web.youtube.core.client.httpx.Client")
    def test_500_raises_server_error(self, mock_client_class):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_session.post.return_value = mock_response
        mock_client_class.return_value = mock_session

        from cli_web.youtube.core.client import YouTubeClient

        client = YouTubeClient()
        with pytest.raises(ServerError) as exc_info:
            client.search("test")
        assert exc_info.value.status_code == 500


# ── CLI Click Tests ──────────────────────────────────────────


class TestCLIClick:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "search" in result.output
        assert "video" in result.output
        assert "trending" in result.output
        assert "channel" in result.output

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_search_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "videos" in result.output

    def test_video_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["video", "--help"])
        assert result.exit_code == 0
        assert "get" in result.output

    @patch("cli_web.youtube.commands.search.YouTubeClient")
    def test_search_json(self, mock_class):
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "query": "test",
            "estimated_results": 100,
            "videos": [{"id": "abc", "title": "Test"}],
        }
        mock_class.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "videos", "test", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["query"] == "test"
        assert len(data["videos"]) == 1

    @patch("cli_web.youtube.commands.video.YouTubeClient")
    def test_video_get_json(self, mock_class):
        mock_client = MagicMock()
        mock_client.video_detail.return_value = {
            "id": "abc123",
            "title": "Test",
            "views": 1000,
        }
        mock_class.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["video", "get", "abc123", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "abc123"

    @patch("cli_web.youtube.commands.video.YouTubeClient")
    def test_video_get_extracts_id_from_url(self, mock_class):
        mock_client = MagicMock()
        mock_client.video_detail.return_value = {"id": "dQw4w9WgXcQ"}
        mock_class.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(
            cli, ["video", "get", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "--json"]
        )
        assert result.exit_code == 0
        mock_client.video_detail.assert_called_once_with("dQw4w9WgXcQ")


# ── Transcripts ──────────────────────────────────────────────


class TestTranscript:
    PLAYER_WITH_CAPTIONS = {
        "videoDetails": {"videoId": "abc123", "title": "Test Video"},
        "captions": {
            "playerCaptionsTracklistRenderer": {
                "captionTracks": [
                    {
                        "baseUrl": "https://www.youtube.com/api/timedtext?v=abc123&lang=en",
                        "languageCode": "en",
                        "name": {"simpleText": "English (auto-generated)"},
                        "kind": "asr",
                        "isTranslatable": True,
                    },
                    {
                        "baseUrl": "https://www.youtube.com/api/timedtext?v=abc123&lang=es",
                        "languageCode": "es",
                        "name": {"runs": [{"text": "Spanish"}]},
                        "isTranslatable": True,
                    },
                ]
            }
        },
    }

    JSON3 = json.dumps(
        {
            "events": [
                {
                    "tStartMs": 0,
                    "dDurationMs": 1500,
                    "segs": [{"utf8": "Hello"}, {"utf8": " world"}],
                },
                {"tStartMs": 1500, "dDurationMs": 2000, "segs": [{"utf8": "second line"}]},
                {"tStartMs": 3500, "segs": [{"utf8": "\n"}]},  # whitespace-only → skipped
                {"tStartMs": 4000},  # no segs → skipped
            ]
        }
    )

    def _client(self):
        from cli_web.youtube.core.client import YouTubeClient

        return YouTubeClient()

    def test_list_transcripts(self):
        c = self._client()
        with patch.object(c, "_post", return_value=self.PLAYER_WITH_CAPTIONS):
            out = c.list_transcripts("abc123")
        assert out["title"] == "Test Video"
        assert [t["language_code"] for t in out["transcripts"]] == ["en", "es"]
        assert out["transcripts"][0]["kind"] == "auto"
        assert out["transcripts"][1]["kind"] == "manual"
        assert out["transcripts"][1]["name"] == "Spanish"

    def test_transcript_parses_json3_and_prefers_manual(self):
        c = self._client()
        mock_resp = MagicMock(status_code=200, text=self.JSON3)
        with (
            patch.object(c, "_post", return_value=self.PLAYER_WITH_CAPTIONS),
            patch.object(c._session, "get", return_value=mock_resp) as mget,
        ):
            out = c.transcript("abc123")
        # Spanish is human-authored; English is asr → prefer Spanish.
        assert out["language_code"] == "es"
        assert out["kind"] == "manual"
        assert out["segment_count"] == 2
        assert out["segments"][0] == {"text": "Hello world", "start": 0.0, "duration": 1.5}
        assert out["text"] == "Hello world second line"
        assert "fmt=json3" in mget.call_args[0][0]

    def test_transcript_language_selection_and_translate(self):
        c = self._client()
        mock_resp = MagicMock(status_code=200, text=self.JSON3)
        with (
            patch.object(c, "_post", return_value=self.PLAYER_WITH_CAPTIONS),
            patch.object(c._session, "get", return_value=mock_resp) as mget,
        ):
            out = c.transcript("abc123", languages=["en"], translate="fr")
        assert out["language_code"] == "fr"
        assert out["is_translated"] is True
        url = mget.call_args[0][0]
        assert "lang=en" in url and "tlang=fr" in url

    def test_transcript_unknown_language_raises(self):
        c = self._client()
        with patch.object(c, "_post", return_value=self.PLAYER_WITH_CAPTIONS):
            with pytest.raises(NotFoundError):
                c.transcript("abc123", languages=["de"])

    def test_transcript_no_captions_raises(self):
        c = self._client()
        player = {"videoDetails": {"videoId": "x", "title": "t"}}
        with patch.object(c, "_post", return_value=player):
            with pytest.raises(NotFoundError):
                c.transcript("x")

    def test_extract_video_id(self):
        from cli_web.youtube.utils.helpers import extract_video_id

        assert extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=5") == "dQw4w9WgXcQ"
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ?si=x") == "dQw4w9WgXcQ"
        assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    @patch("cli_web.youtube.commands.transcript.YouTubeClient")
    def test_transcript_get_command_json(self, mock_class):
        mock_client = MagicMock()
        mock_client.transcript.return_value = {
            "video_id": "abc123",
            "title": "T",
            "language_code": "en",
            "kind": "manual",
            "is_translated": False,
            "segment_count": 1,
            "segments": [{"text": "hi", "start": 0.0, "duration": 1.0}],
            "text": "hi",
        }
        mock_class.return_value = mock_client
        result = CliRunner().invoke(cli, ["transcript", "get", "abc123", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.output)["text"] == "hi"

    @patch("cli_web.youtube.commands.transcript.YouTubeClient")
    def test_transcript_get_text_only(self, mock_class):
        mock_client = MagicMock()
        mock_client.transcript.return_value = {
            "text": "just the words",
            "segments": [],
            "segment_count": 0,
        }
        mock_class.return_value = mock_client
        result = CliRunner().invoke(cli, ["transcript", "get", "abc123", "--text-only"])
        assert result.exit_code == 0
        assert result.output.strip() == "just the words"
