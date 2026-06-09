"""Unit tests for cli-web-gai core modules (mocked Playwright)."""

import json
import sys
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from cli_web.gai.core.exceptions import (
    AppError,
    BrowserError,
    CaptchaError,
    NetworkError,
    ParseError,
    RequestTimeoutError,
)

from cli_web.gai.core.models import Source, SearchResult
from cli_web.gai.utils.helpers import handle_errors, json_error


# ── Test Exceptions ──────────────────────────────────────────────────

class TestExceptions:
    def test_all_exceptions_inherit_from_gai_error(self):
        for exc_cls in (BrowserError, CaptchaError, NetworkError, ParseError, RequestTimeoutError):
            assert issubclass(exc_cls, AppError)

    def test_timeout_error_has_timeout_seconds(self):
        err = RequestTimeoutError("timed out", timeout_seconds=45)
        assert err.timeout_seconds == 45
        assert "timed out" in str(err)

    def test_captcha_error_message(self):
        err = CaptchaError("CAPTCHA detected")
        assert "CAPTCHA" in str(err)


# ── Test Models ──────────────────────────────────────────────────────

class TestModels:
    def test_source_to_dict_minimal(self):
        src = Source(title="Example", url="https://example.com")
        d = src.to_dict()
        assert d["title"] == "Example"
        assert d["url"] == "https://example.com"
        assert "snippet" not in d

    def test_source_to_dict_with_snippet(self):
        src = Source(title="Ex", url="https://ex.com", snippet="Some text")
        d = src.to_dict()
        assert d["snippet"] == "Some text"

    def test_search_result_to_dict(self):
        result = SearchResult(
            query="test query",
            answer="The answer is 42.",
            sources=[Source(title="Wiki", url="https://wiki.org")],
            follow_up_prompt="Want to know more?",
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["data"]["query"] == "test query"
        assert d["data"]["answer"] == "The answer is 42."
        assert len(d["data"]["sources"]) == 1
        assert d["data"]["sources"][0]["title"] == "Wiki"
        assert d["data"]["follow_up_prompt"] == "Want to know more?"

    def test_search_result_to_dict_no_followup(self):
        result = SearchResult(query="q", answer="a")
        d = result.to_dict()
        assert "follow_up_prompt" not in d["data"]

    def test_search_result_to_dict_is_valid_json(self):
        result = SearchResult(
            query="q",
            answer="a",
            sources=[Source(title="S", url="https://s.com")],
        )
        serialized = json.dumps(result.to_dict())
        parsed = json.loads(serialized)
        assert parsed["success"] is True


# ── Test Helpers ─────────────────────────────────────────────────────

class TestHelpers:
    def test_json_error_format(self):
        err = json_error("TIMEOUT", "Response timed out", retry_after=30)
        parsed = json.loads(err)
        assert parsed["error"] is True
        assert parsed["code"] == "TIMEOUT"
        assert parsed["message"] == "Response timed out"
        assert parsed["retry_after"] == 30

    def test_handle_errors_gai_error_exits_1(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise AppError("some error")
        assert exc.value.code == 1

    def test_handle_errors_unexpected_exits_2(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise ValueError("unexpected bug")
        assert exc.value.code == 2

    def test_handle_errors_keyboard_interrupt_exits_130(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise KeyboardInterrupt()
        assert exc.value.code == 130

    def test_handle_errors_captcha_exits_1(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise CaptchaError("solve it")
        assert exc.value.code == 1

    def test_handle_errors_json_mode_outputs_json(self, capsys):
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise NetworkError("connection failed")
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["error"] is True
        assert parsed["code"] == "NETWORK_ERROR"

    def test_handle_errors_json_mode_captcha(self, capsys):
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise CaptchaError("captcha")
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["code"] == "CAPTCHA_REQUIRED"


# ── Test Client (Mocked Playwright) ─────────────────────────────────

class TestClientMocked:
    """Test client logic with mocked Playwright browser."""

    _SENTINEL = object()

    def _make_mock_page(self, evaluate_return=_SENTINEL, captcha=False):
        """Create a mock page that simulates AI Mode response."""
        page = MagicMock()
        page.is_closed.return_value = False
        page.url = "https://www.google.com/search?q=test&udm=50"
        page.query_selector.return_value = None if not captcha else MagicMock()

        if evaluate_return is self._SENTINEL:
            evaluate_return = {
                "answer": "The answer is 42.",
                "sources": [
                    {"title": "wiki.org", "url": "https://wiki.org/42", "snippet": "About 42"},
                ],
                "followUp": "Want more details?",
            }
        page.evaluate.return_value = evaluate_return
        return page

    @patch("cli_web.gai.core.client.sync_playwright")
    def test_search_returns_search_result(self, mock_pw):
        """Client.search() returns a SearchResult with answer and sources."""
        mock_page = self._make_mock_page()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_pw.return_value.start.return_value.chromium.launch.return_value = mock_browser

        from cli_web.gai.core.client import GAIClient
        client = GAIClient(headless=True)
        result = client.search("test query")

        assert isinstance(result, SearchResult)
        assert result.query == "test query"
        assert result.answer == "The answer is 42."
        assert len(result.sources) == 1
        assert result.sources[0].title == "wiki.org"
        assert result.sources[0].url == "https://wiki.org/42"
        assert result.follow_up_prompt == "Want more details?"

        # Verify URL contains expected params
        call_args = mock_page.goto.assert_called_once
        call_args = str(mock_page.goto.call_args)
        assert "udm=50" in call_args
        assert "test+query" in call_args or "test%20query" in call_args

        client.close()

    @patch("cli_web.gai.core.client.sync_playwright")
    def test_search_raises_captcha_error(self, mock_pw):
        """Client raises CaptchaError when CAPTCHA is detected."""
        mock_page = self._make_mock_page(captcha=True)
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_pw.return_value.start.return_value.chromium.launch.return_value = mock_browser

        from cli_web.gai.core.client import GAIClient
        client = GAIClient(headless=True)
        with pytest.raises(CaptchaError):
            client.search("test")
        client.close()

    @patch("cli_web.gai.core.client.sync_playwright")
    def test_search_raises_parse_error_on_null(self, mock_pw):
        """Client raises ParseError when DOM extraction returns null."""
        mock_page = self._make_mock_page(evaluate_return=None)
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_pw.return_value.start.return_value.chromium.launch.return_value = mock_browser

        from cli_web.gai.core.client import GAIClient
        client = GAIClient(headless=True)
        with pytest.raises(ParseError):
            client.search("test")
        client.close()

    @patch("cli_web.gai.core.client.sync_playwright")
    def test_search_network_error_on_goto_failure(self, mock_pw):
        """Client raises NetworkError when page.goto fails."""
        mock_page = self._make_mock_page()
        mock_page.goto.side_effect = Exception("Connection refused")
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_pw.return_value.start.return_value.chromium.launch.return_value = mock_browser

        from cli_web.gai.core.client import GAIClient
        client = GAIClient(headless=True)
        with pytest.raises(NetworkError):
            client.search("test")
        client.close()

    @patch("cli_web.gai.core.client.sync_playwright")
    def test_client_context_manager(self, mock_pw):
        """Client can be used as context manager."""
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = self._make_mock_page()
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_pw.return_value.start.return_value.chromium.launch.return_value = mock_browser

        from cli_web.gai.core.client import GAIClient
        with GAIClient(headless=True) as client:
            result = client.search("test")
            assert result.answer == "The answer is 42."

        mock_page.close.assert_called()

    @patch("cli_web.gai.core.client.sync_playwright")
    def test_browser_launch_failure_raises_browser_error(self, mock_pw):
        """Client raises BrowserError when browser fails to launch."""
        mock_pw.return_value.start.return_value.chromium.launch.side_effect = Exception("no chromium")

        from cli_web.gai.core.client import GAIClient
        client = GAIClient(headless=True)
        with pytest.raises(BrowserError, match="Failed to launch browser"):
            client.search("test")

    @patch("cli_web.gai.core.client.sync_playwright")
    def test_search_with_empty_sources(self, mock_pw):
        """Client handles responses with no source links."""
        mock_page = self._make_mock_page(
            evaluate_return={"answer": "Simple answer.", "sources": [], "followUp": ""}
        )
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_pw.return_value.start.return_value.chromium.launch.return_value = mock_browser

        from cli_web.gai.core.client import GAIClient
        client = GAIClient(headless=True)
        result = client.search("simple q")
        assert result.answer == "Simple answer."
        assert len(result.sources) == 0
        assert result.follow_up_prompt == ""
        client.close()

    @patch("cli_web.gai.core.client.sync_playwright")
    def test_followup_without_prior_search_raises(self, mock_pw):
        """Client.followup() raises BrowserError without a prior search."""
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.url = "about:blank"
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_pw.return_value.start.return_value.chromium.launch.return_value = mock_browser

        from cli_web.gai.core.client import GAIClient
        client = GAIClient(headless=True)
        # Force _ensure_browser to return our mock_page
        client._ensure_browser()
        with pytest.raises(BrowserError, match="No active conversation"):
            client.followup("follow-up q")
        client.close()
