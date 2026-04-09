"""Comprehensive unit tests for cli-web-linkedin core modules.

Covers: exceptions, models, helpers, CSRF extraction, and HTTP error mapping.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cli_web.linkedin.core.exceptions import (
    AuthError,
    LinkedinError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    RPCError,
    ServerError,
    raise_for_status,
)
from cli_web.linkedin.core.models import (
    Comment,
    Company,
    Job,
    Post,
    Profile,
    SearchResult,
)
from cli_web.linkedin.utils.helpers import handle_errors, resolve_json_mode


# =====================================================================
# 1. TestExceptions
# =====================================================================

class TestExceptions:
    """Verify exception hierarchy, attributes, and to_dict serialization."""

    def test_linkedin_error_base_to_dict(self):
        exc = LinkedinError("something broke")
        d = exc.to_dict()
        assert d["error"] is True
        assert d["code"] == "UNKNOWN_ERROR"
        assert d["message"] == "something broke"

    def test_auth_error_recoverable_flag(self):
        exc = AuthError("expired", recoverable=True)
        assert exc.recoverable is True
        exc2 = AuthError("bad", recoverable=False)
        assert exc2.recoverable is False

    def test_auth_error_to_dict_code(self):
        exc = AuthError("token expired")
        d = exc.to_dict()
        assert d["code"] == "AUTH_EXPIRED"
        assert d["error"] is True
        assert "token expired" in d["message"]

    def test_rate_limit_error_retry_after(self):
        exc = RateLimitError("slow down", retry_after=30.0)
        assert exc.retry_after == 30.0

    def test_rate_limit_error_to_dict_includes_retry_after(self):
        exc = RateLimitError("slow down", retry_after=42.5)
        d = exc.to_dict()
        assert d["code"] == "RATE_LIMITED"
        assert d["retry_after"] == 42.5

    def test_rate_limit_error_to_dict_omits_retry_after_when_none(self):
        exc = RateLimitError("slow down", retry_after=None)
        d = exc.to_dict()
        assert "retry_after" not in d

    def test_server_error_status_code(self):
        exc = ServerError("bad gateway", status_code=502)
        assert exc.status_code == 502
        d = exc.to_dict()
        assert d["code"] == "SERVER_ERROR"

    def test_server_error_default_status_code(self):
        exc = ServerError("internal error")
        assert exc.status_code == 500

    def test_not_found_error_to_dict(self):
        exc = NotFoundError("user not found")
        d = exc.to_dict()
        assert d["code"] == "NOT_FOUND"
        assert d["message"] == "user not found"

    def test_network_error_to_dict(self):
        exc = NetworkError("DNS failure")
        d = exc.to_dict()
        assert d["code"] == "NETWORK_ERROR"
        assert d["message"] == "DNS failure"

    def test_rpc_error_to_dict(self):
        exc = RPCError("decode failed")
        d = exc.to_dict()
        assert d["code"] == "RPC_ERROR"

    def test_all_exceptions_inherit_from_linkedin_error(self):
        for cls in (AuthError, RateLimitError, NetworkError, ServerError, NotFoundError, RPCError):
            assert issubclass(cls, LinkedinError)


# =====================================================================
# 2. TestModels
# =====================================================================

class TestModels:
    """Verify dataclass models and their to_dict round-trip."""

    def test_post_to_dict_all_fields(self):
        p = Post(
            id="123",
            text="Hello LinkedIn",
            author_name="Alice",
            author_headline="Engineer",
            author_urn="urn:li:member:1",
            created_at="2025-01-01",
            num_likes=10,
            num_comments=3,
            num_repins=1,
            url="https://linkedin.com/post/123",
            images=["img1.jpg", "img2.jpg"],
        )
        d = p.to_dict()
        assert d["id"] == "123"
        assert d["text"] == "Hello LinkedIn"
        assert d["author_name"] == "Alice"
        assert d["num_likes"] == 10
        assert d["images"] == ["img1.jpg", "img2.jpg"]
        assert len(d) == 11

    def test_post_defaults(self):
        p = Post(id="1", text="hi", author_name="Bob")
        d = p.to_dict()
        assert d["num_likes"] == 0
        assert d["images"] == []
        assert d["author_headline"] == ""

    def test_profile_to_dict_preserves_fields(self):
        p = Profile(
            urn="urn:li:member:42",
            username="jdoe",
            first_name="John",
            last_name="Doe",
            headline="Software Engineer",
            follower_count=5000,
            connection_count=300,
        )
        d = p.to_dict()
        assert d["username"] == "jdoe"
        assert d["follower_count"] == 5000
        assert d["urn"] == "urn:li:member:42"
        assert d["connection_count"] == 300

    def test_company_to_dict_preserves_fields(self):
        c = Company(
            urn="urn:li:company:99",
            name="Acme Corp",
            universal_name="acme-corp",
            industry="Tech",
            follower_count=100_000,
            employee_count=500,
        )
        d = c.to_dict()
        assert d["name"] == "Acme Corp"
        assert d["universal_name"] == "acme-corp"
        assert d["follower_count"] == 100_000

    def test_job_to_dict_preserves_fields(self):
        j = Job(
            urn="urn:li:job:777",
            title="Backend Developer",
            company_name="Acme Corp",
            location="Remote",
            workplace_type="remote",
            employment_type="Full-time",
        )
        d = j.to_dict()
        assert d["urn"] == "urn:li:job:777"
        assert d["title"] == "Backend Developer"
        assert d["company_name"] == "Acme Corp"
        assert d["workplace_type"] == "remote"

    def test_search_result_to_dict_all_fields(self):
        sr = SearchResult(
            urn="urn:li:member:11",
            name="Jane",
            headline="CTO",
            location="NYC",
            url="https://linkedin.com/in/jane",
            type="person",
            image_url="https://img.com/jane.jpg",
        )
        d = sr.to_dict()
        assert d["name"] == "Jane"
        assert d["type"] == "person"
        assert d["headline"] == "CTO"
        assert len(d) == 7

    def test_comment_to_dict_all_fields(self):
        c = Comment(
            id="c1",
            text="Great post!",
            author_name="Bob",
            author_urn="urn:li:member:5",
            created_at="2025-06-01",
            num_likes=7,
        )
        d = c.to_dict()
        assert d["id"] == "c1"
        assert d["text"] == "Great post!"
        assert d["author_name"] == "Bob"
        assert d["num_likes"] == 7
        assert len(d) == 6


# =====================================================================
# 3. TestHelpers
# =====================================================================

class TestHelpers:
    """Verify handle_errors context manager and resolve_json_mode."""

    def test_handle_errors_catches_auth_error_exit_1(self):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors():
                raise AuthError("expired")
        assert exc_info.value.code == 1

    def test_handle_errors_catches_not_found_error_exit_1(self):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors():
                raise NotFoundError("no such user")
        assert exc_info.value.code == 1

    def test_handle_errors_catches_server_error_exit_2(self):
        """ServerError is a LinkedinError so exits with code 1."""
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors():
                raise ServerError("internal error", status_code=500)
        assert exc_info.value.code == 1

    def test_handle_errors_catches_network_error_exit_1(self):
        """NetworkError is a LinkedinError so exits with code 1."""
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors():
                raise NetworkError("DNS failed")
        assert exc_info.value.code == 1

    def test_handle_errors_catches_generic_exception_exit_2(self):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors():
                raise RuntimeError("unexpected")
        assert exc_info.value.code == 2

    def test_handle_errors_keyboard_interrupt_exit_130(self):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors():
                raise KeyboardInterrupt()
        assert exc_info.value.code == 130

    def test_handle_errors_json_mode_outputs_json(self, capsys):
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise AuthError("token expired")
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["error"] is True
        assert data["code"] == "AUTH_EXPIRED"
        assert "token expired" in data["message"]

    def test_handle_errors_json_mode_generic_exception(self, capsys):
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise ValueError("oops")
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["code"] == "INTERNAL_ERROR"

    def test_resolve_json_mode_true(self):
        assert resolve_json_mode(True) is True

    def test_resolve_json_mode_false(self):
        assert resolve_json_mode(False) is False

    def test_resolve_json_mode_from_context(self):
        ctx = MagicMock()
        ctx.obj = {"json": True}
        assert resolve_json_mode(False, ctx=ctx) is True

    def test_resolve_json_mode_context_no_json(self):
        ctx = MagicMock()
        ctx.obj = {}
        assert resolve_json_mode(False, ctx=ctx) is False


# =====================================================================
# 4. TestCSRFExtraction
# =====================================================================

class TestCSRFExtraction:
    """Verify _extract_csrf from client.py."""

    def test_extract_csrf_strips_quotes(self):
        from cli_web.linkedin.core.client import _extract_csrf
        result = _extract_csrf({"JSESSIONID": '"ajax:1234567890"'})
        assert result == "ajax:1234567890"

    def test_extract_csrf_no_quotes(self):
        from cli_web.linkedin.core.client import _extract_csrf
        result = _extract_csrf({"JSESSIONID": "ajax:abcdef"})
        assert result == "ajax:abcdef"

    def test_extract_csrf_missing_jsessionid_raises_auth_error(self):
        from cli_web.linkedin.core.client import _extract_csrf
        with pytest.raises(AuthError, match="JSESSIONID cookie missing"):
            _extract_csrf({})

    def test_extract_csrf_empty_jsessionid_raises_auth_error(self):
        from cli_web.linkedin.core.client import _extract_csrf
        with pytest.raises(AuthError):
            _extract_csrf({"JSESSIONID": ""})


# =====================================================================
# 5. TestClientHTTPErrors (raise_for_status)
# =====================================================================

class TestClientHTTPErrors:
    """Verify raise_for_status maps HTTP codes to typed exceptions."""

    @staticmethod
    def _mock_response(status_code: int, text: str = "", headers: dict | None = None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = text
        resp.headers = headers or {}
        return resp

    def test_401_raises_auth_error(self):
        resp = self._mock_response(401, "Unauthorized")
        with pytest.raises(AuthError):
            raise_for_status(resp)

    def test_403_raises_auth_error(self):
        resp = self._mock_response(403, "Forbidden")
        with pytest.raises(AuthError):
            raise_for_status(resp)

    def test_404_raises_not_found_error(self):
        resp = self._mock_response(404, "Not Found")
        with pytest.raises(NotFoundError):
            raise_for_status(resp)

    def test_429_raises_rate_limit_error(self):
        resp = self._mock_response(429, "Too Many Requests", headers={"Retry-After": "60"})
        with pytest.raises(RateLimitError) as exc_info:
            raise_for_status(resp)
        assert exc_info.value.retry_after == 60.0

    def test_429_without_retry_after_header(self):
        resp = self._mock_response(429, "Too Many Requests")
        with pytest.raises(RateLimitError) as exc_info:
            raise_for_status(resp)
        assert exc_info.value.retry_after is None

    def test_500_raises_server_error(self):
        resp = self._mock_response(500, "Internal Server Error")
        with pytest.raises(ServerError) as exc_info:
            raise_for_status(resp)
        assert exc_info.value.status_code == 500

    def test_502_raises_server_error(self):
        resp = self._mock_response(502, "Bad Gateway")
        with pytest.raises(ServerError) as exc_info:
            raise_for_status(resp)
        assert exc_info.value.status_code == 502

    def test_200_does_not_raise(self):
        resp = self._mock_response(200, "OK")
        raise_for_status(resp)  # Should not raise

    def test_400_raises_linkedin_error(self):
        """Unknown 4xx falls back to base LinkedinError."""
        resp = self._mock_response(400, "Bad Request")
        with pytest.raises(LinkedinError):
            raise_for_status(resp)


# =====================================================================
# 6. TestTruncate (from commands/search.py)
# =====================================================================

class TestTruncate:
    """Verify the _truncate helper from search module."""

    def test_short_string_unchanged(self):
        from cli_web.linkedin.commands.search import _truncate
        assert _truncate("hello", 60) == "hello"

    def test_exact_length_unchanged(self):
        from cli_web.linkedin.commands.search import _truncate
        text = "a" * 60
        assert _truncate(text, 60) == text

    def test_long_string_truncated_with_ellipsis(self):
        from cli_web.linkedin.commands.search import _truncate
        text = "a" * 100
        result = _truncate(text, 60)
        assert len(result) == 60
        assert result.endswith("\u2026")

    def test_empty_string(self):
        from cli_web.linkedin.commands.search import _truncate
        assert _truncate("", 60) == ""
