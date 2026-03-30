"""Unit tests for cli-web-chatgpt core modules."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import click
import pytest

from cli_web.chatgpt.core.exceptions import (
    AuthError,
    ChatGPTError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from cli_web.chatgpt.utils.helpers import handle_errors, json_error, print_json, truncate


# ── Exception hierarchy tests ──────────────────────────────────


class TestExceptions:
    def test_chatgpt_error_is_base(self):
        assert issubclass(AuthError, ChatGPTError)
        assert issubclass(RateLimitError, ChatGPTError)
        assert issubclass(NetworkError, ChatGPTError)
        assert issubclass(ServerError, ChatGPTError)
        assert issubclass(NotFoundError, ChatGPTError)

    def test_auth_error_recoverable(self):
        err = AuthError("expired", recoverable=True)
        assert err.recoverable is True
        assert str(err) == "expired"

    def test_auth_error_not_recoverable_by_default(self):
        err = AuthError("missing")
        assert err.recoverable is False

    def test_rate_limit_error_retry_after(self):
        err = RateLimitError("slow down", retry_after=30.0)
        assert err.retry_after == 30.0

    def test_rate_limit_error_no_retry(self):
        err = RateLimitError("slow down")
        assert err.retry_after is None

    def test_server_error_status_code(self):
        err = ServerError("oops", status_code=503)
        assert err.status_code == 503


# ── handle_errors tests ────────────────────────────────────────


class TestHandleErrors:
    def test_auth_error_exits_1(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise AuthError("expired")
        assert exc.value.code == 1

    def test_not_found_exits_1(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise NotFoundError("gone")
        assert exc.value.code == 1

    def test_rate_limit_exits_1(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise RateLimitError("wait")
        assert exc.value.code == 1

    def test_server_error_exits_2(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise ServerError("500")
        assert exc.value.code == 2

    def test_network_error_exits_2(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise NetworkError("timeout")
        assert exc.value.code == 2

    def test_keyboard_interrupt_exits_130(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise KeyboardInterrupt()
        assert exc.value.code == 130

    def test_json_mode_outputs_json(self, capsys):
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise AuthError("token expired")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["error"] is True
        assert data["code"] == "AUTH_EXPIRED"

    def test_json_mode_rate_limit_includes_retry(self, capsys):
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise RateLimitError("slow", retry_after=42.0)
        data = json.loads(capsys.readouterr().out)
        assert data["code"] == "RATE_LIMITED"
        assert data["retry_after"] == 42.0


# ── json_error tests ───────────────────────────────────────────


class TestJsonError:
    def test_basic_error(self):
        result = json_error("NOT_FOUND", "item not found")
        data = json.loads(result)
        assert data["error"] is True
        assert data["code"] == "NOT_FOUND"
        assert data["message"] == "item not found"

    def test_extra_fields(self):
        result = json_error("RATE_LIMITED", "wait", retry_after=60)
        data = json.loads(result)
        assert data["retry_after"] == 60


# ── truncate tests ─────────────────────────────────────────────


class TestTruncate:
    def test_short_text(self):
        assert truncate("hello", 10) == "hello"

    def test_long_text(self):
        assert truncate("a" * 100, 10) == "a" * 10 + "..."

    def test_none(self):
        assert truncate(None) == ""

    def test_empty(self):
        assert truncate("") == ""


# ── Client HTTP error mapping tests ───────────────────────────


class TestClientErrorMapping:
    """Test that _check_response maps status codes to correct exceptions."""

    def _make_response(self, status_code, text="error", headers=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = text
        resp.headers = headers or {}
        return resp

    def test_401_raises_auth_error(self):
        from cli_web.chatgpt.core.client import ChatGPTClient

        client = ChatGPTClient()
        resp = self._make_response(401)
        with pytest.raises(AuthError):
            client._check_response(resp, "/test")

    def test_403_raises_auth_error(self):
        from cli_web.chatgpt.core.client import ChatGPTClient

        client = ChatGPTClient()
        resp = self._make_response(403)
        with pytest.raises(AuthError):
            client._check_response(resp, "/test")

    def test_404_raises_not_found(self):
        from cli_web.chatgpt.core.client import ChatGPTClient

        client = ChatGPTClient()
        resp = self._make_response(404)
        with pytest.raises(NotFoundError):
            client._check_response(resp, "/test")

    def test_429_raises_rate_limit(self):
        from cli_web.chatgpt.core.client import ChatGPTClient

        client = ChatGPTClient()
        resp = self._make_response(429, headers={"retry-after": "30"})
        with pytest.raises(RateLimitError) as exc_info:
            client._check_response(resp, "/test")
        assert exc_info.value.retry_after == 30.0

    def test_500_raises_server_error(self):
        from cli_web.chatgpt.core.client import ChatGPTClient

        client = ChatGPTClient()
        resp = self._make_response(500)
        with pytest.raises(ServerError) as exc_info:
            client._check_response(resp, "/test")
        assert exc_info.value.status_code == 500

    def test_502_raises_server_error(self):
        from cli_web.chatgpt.core.client import ChatGPTClient

        client = ChatGPTClient()
        resp = self._make_response(502)
        with pytest.raises(ServerError):
            client._check_response(resp, "/test")

    def test_400_raises_chatgpt_error(self):
        from cli_web.chatgpt.core.client import ChatGPTClient

        client = ChatGPTClient()
        resp = self._make_response(400)
        with pytest.raises(ChatGPTError):
            client._check_response(resp, "/test")


# ── Auth module tests ──────────────────────────────────────────


class TestAuth:
    def test_load_auth_from_env(self, monkeypatch, tmp_path):
        auth_data = {"access_token": "test-token", "device_id": "dev-123", "cookies": {}}
        monkeypatch.setenv("CLI_WEB_CHATGPT_AUTH_JSON", json.dumps(auth_data))
        from cli_web.chatgpt.core.auth import load_auth

        result = load_auth()
        assert result["access_token"] == "test-token"
        assert result["device_id"] == "dev-123"

    def test_load_auth_missing_raises(self, monkeypatch, tmp_path):
        monkeypatch.delenv("CLI_WEB_CHATGPT_AUTH_JSON", raising=False)
        monkeypatch.setattr("cli_web.chatgpt.core.auth.AUTH_FILE", tmp_path / "nonexistent.json")
        from cli_web.chatgpt.core.auth import load_auth

        with pytest.raises(AuthError):
            load_auth()

    def test_save_and_load_auth(self, monkeypatch, tmp_path):
        monkeypatch.delenv("CLI_WEB_CHATGPT_AUTH_JSON", raising=False)
        auth_file = tmp_path / "auth.json"
        monkeypatch.setattr("cli_web.chatgpt.core.auth.AUTH_FILE", auth_file)
        monkeypatch.setattr("cli_web.chatgpt.core.auth.CONFIG_DIR", tmp_path)

        from cli_web.chatgpt.core.auth import load_auth, save_auth

        save_auth({"access_token": "tok", "device_id": "d1", "cookies": {}})
        result = load_auth()
        assert result["access_token"] == "tok"

    def test_is_logged_in_false(self, monkeypatch, tmp_path):
        monkeypatch.delenv("CLI_WEB_CHATGPT_AUTH_JSON", raising=False)
        monkeypatch.setattr("cli_web.chatgpt.core.auth.AUTH_FILE", tmp_path / "nope.json")
        from cli_web.chatgpt.core.auth import is_logged_in

        assert is_logged_in() is False

    def test_clear_auth(self, monkeypatch, tmp_path):
        auth_file = tmp_path / "auth.json"
        auth_file.write_text('{"access_token": "x"}')
        monkeypatch.setattr("cli_web.chatgpt.core.auth.AUTH_FILE", auth_file)
        from cli_web.chatgpt.core.auth import clear_auth

        clear_auth()
        assert not auth_file.exists()


