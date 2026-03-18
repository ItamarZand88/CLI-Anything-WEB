"""Unit tests for cli-web-suno core modules."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli_web.suno.core import auth
from cli_web.suno.core.client import SunoClient, SunoAuthError, SunoRateLimitError, SunoClientError
from cli_web.suno.core.models import Clip, BillingInfo, Project, User


# ─── auth tests ──────────────────────────────────────────────────────


class TestAuthSaveLoad:
    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
        monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")

        data = {"jwt": "test-jwt-123", "cookies": [{"name": "x", "value": "y"}]}
        auth.save_auth(data)
        loaded = auth.load_auth()
        assert loaded["jwt"] == "test-jwt-123"
        assert len(loaded["cookies"]) == 1

    def test_load_returns_none_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "nonexistent.json")
        assert auth.load_auth() is None


class TestAuthHeaders:
    def test_get_auth_headers_with_jwt(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
        monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")
        auth.save_auth({"jwt": "my-jwt-token"})

        headers = auth.get_auth_headers()
        assert headers["Authorization"] == "Bearer my-jwt-token"
        assert "browser-token" in headers
        assert "device-id" in headers
        assert headers["origin"] == "https://suno.com"

    def test_get_auth_headers_raises_without_auth(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "nonexistent.json")
        with pytest.raises(RuntimeError, match="Not authenticated"):
            auth.get_auth_headers()

    def test_browser_token_is_valid_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
        monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")
        auth.save_auth({"jwt": "test"})

        headers = auth.get_auth_headers()
        bt = json.loads(headers["browser-token"])
        assert "token" in bt

    def test_device_id_persists(self, tmp_path, monkeypatch):
        monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
        id1 = auth._get_device_id()
        id2 = auth._get_device_id()
        assert id1 == id2
        assert len(id1) == 36  # UUID format


# ─── client tests ────────────────────────────────────────────────────


class TestSunoClient:
    def _mock_response(self, status_code=200, json_data=None, headers=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        resp.text = json.dumps(json_data or {})
        resp.headers = headers or {}
        return resp

    @patch("cli_web.suno.core.client.get_auth_headers")
    def test_get_request(self, mock_headers):
        mock_headers.return_value = {"Authorization": "Bearer test"}
        client = SunoClient()
        client._client = MagicMock()
        client._client.is_closed = False
        client._client.request.return_value = self._mock_response(
            200, {"key": "value"}
        )

        result = client.get("/api/test")
        assert result == {"key": "value"}
        client._client.request.assert_called_once()

    @patch("cli_web.suno.core.client.get_auth_headers")
    def test_post_request_with_body(self, mock_headers):
        mock_headers.return_value = {"Authorization": "Bearer test"}
        client = SunoClient()
        client._client = MagicMock()
        client._client.is_closed = False
        client._client.request.return_value = self._mock_response(
            200, {"clips": []}
        )

        result = client.post("/api/feed/v3", json_body={"limit": 5})
        assert result == {"clips": []}

    @patch("cli_web.suno.core.client.get_auth_headers")
    @patch("cli_web.suno.core.client.load_auth")
    def test_401_raises_auth_error(self, mock_load, mock_headers):
        mock_headers.return_value = {"Authorization": "Bearer expired"}
        mock_load.return_value = None
        client = SunoClient()
        client._client = MagicMock()
        client._client.is_closed = False
        client._client.request.return_value = self._mock_response(401)

        with pytest.raises(SunoAuthError):
            client.get("/api/session/")

    @patch("cli_web.suno.core.client.get_auth_headers")
    def test_429_raises_rate_limit_error(self, mock_headers):
        mock_headers.return_value = {"Authorization": "Bearer test"}
        client = SunoClient()
        client._client = MagicMock()
        client._client.is_closed = False
        client._client.request.return_value = self._mock_response(
            429, headers={"retry-after": "10"}
        )

        with pytest.raises(SunoRateLimitError) as exc_info:
            client.get("/api/test")
        assert exc_info.value.retry_after == 10.0

    @patch("cli_web.suno.core.client.get_auth_headers")
    def test_500_raises_client_error(self, mock_headers):
        mock_headers.return_value = {"Authorization": "Bearer test"}
        client = SunoClient()
        client._client = MagicMock()
        client._client.is_closed = False
        client._client.request.return_value = self._mock_response(
            500, {"error": "internal"}
        )

        with pytest.raises(SunoClientError) as exc_info:
            client.get("/api/test")
        assert exc_info.value.status_code == 500

    @patch("cli_web.suno.core.client.get_auth_headers")
    def test_get_feed_builds_correct_body(self, mock_headers):
        mock_headers.return_value = {"Authorization": "Bearer test"}
        client = SunoClient()
        client._client = MagicMock()
        client._client.is_closed = False
        client._client.request.return_value = self._mock_response(
            200, {"clips": []}
        )

        client.get_feed(limit=5, workspace_id="myproject")
        call_args = client._client.request.call_args
        body = call_args.kwargs.get("json") or call_args[1].get("json")
        assert body["limit"] == 5
        assert body["filters"]["workspace"]["workspaceId"] == "myproject"


# ─── model tests ─────────────────────────────────────────────────────


class TestModels:
    def test_clip_from_dict_full(self):
        data = {
            "id": "abc-123",
            "title": "My Song",
            "status": "complete",
            "audio_url": "https://cdn1.suno.ai/abc.mp3",
            "play_count": 42,
            "metadata": {"tags": "pop, rock", "duration": 65.5, "task": "generate"},
            "major_model_version": "v4",
            "created_at": "2026-01-01T00:00:00Z",
        }
        clip = Clip.from_dict(data)
        assert clip.id == "abc-123"
        assert clip.title == "My Song"
        assert clip.duration == 65.5
        assert clip.tags == "pop, rock"

    def test_clip_from_dict_minimal(self):
        clip = Clip.from_dict({"id": "x", "title": "Y", "status": "submitted"})
        assert clip.id == "x"
        assert clip.duration == 0.0
        assert clip.tags == ""

    def test_clip_to_summary(self):
        clip = Clip(
            id="abc", title="Test", status="complete", duration=60.0,
            major_model_version="v4", play_count=10, upvote_count=5,
            created_at="2026-01-01T12:00:00Z",
        )
        s = clip.to_summary()
        assert s["id"] == "abc"
        assert s["duration"] == "60.0s"
        assert s["plays"] == 10

    def test_billing_info_from_dict(self):
        data = {
            "credits": 70,
            "total_credits_left": 120,
            "is_active": False,
            "monthly_usage": 10,
            "monthly_limit": 50,
        }
        bi = BillingInfo.from_dict(data)
        assert bi.credits == 70
        assert bi.total_credits_left == 120
        assert bi.is_active is False
