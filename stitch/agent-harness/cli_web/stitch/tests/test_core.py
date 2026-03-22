"""Comprehensive unit tests for cli-web-stitch core modules.

Covers: RPC encoder/decoder, exceptions, models, client (mocked HTTP),
helpers, and auth (mocked filesystem).

All tests use ``@pytest.mark.unit`` and never make real network calls.
"""
import json
import os
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import click
import httpx
import pytest

# ── Imports under test ────────────────────────────────────────────────
from cli_web.stitch.core.exceptions import (
    AuthError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    RPCError,
    ServerError,
    StitchError,
)
from cli_web.stitch.core.rpc.encoder import build_url, encode_request
from cli_web.stitch.core.rpc.decoder import (
    decode_response,
    extract_result,
    parse_chunks,
    strip_prefix,
)
from cli_web.stitch.core.models import (
    Project,
    Screen,
    Session,
    parse_project,
    parse_screen,
    parse_session,
)
from cli_web.stitch.utils.helpers import (
    get_context_value,
    handle_errors,
    resolve_partial_id,
    sanitize_filename,
    set_context_value,
)

# =====================================================================
# 1. RPC Codec Tests
# =====================================================================


class TestEncoder:
    """Tests for ``core/rpc/encoder.py``."""

    @pytest.mark.unit
    def test_encode_request_produces_url_encoded_body(self):
        body = encode_request("A7f2qf", [["projects/123"]], "csrf_tok")
        parsed = urllib.parse.parse_qs(body)
        assert "f.req" in parsed
        assert "at" in parsed
        assert parsed["at"] == ["csrf_tok"]
        # f.req should contain the rpc_id and params as nested JSON
        freq = json.loads(parsed["f.req"][0])
        assert freq[0][0][0] == "A7f2qf"
        assert json.loads(freq[0][0][1]) == [["projects/123"]]
        assert freq[0][0][2] is None
        assert freq[0][0][3] == "generic"

    @pytest.mark.unit
    def test_encode_request_empty_params(self):
        body = encode_request("A7f2qf", [], "tok")
        parsed = urllib.parse.parse_qs(body)
        freq = json.loads(parsed["f.req"][0])
        assert json.loads(freq[0][0][1]) == []

    @pytest.mark.unit
    def test_build_url_contains_rpc_id_and_session_id(self):
        url = build_url("A7f2qf", "12345", "bl_label", "/projects/abc")
        assert "rpcids=A7f2qf" in url
        assert "f.sid=12345" in url
        assert "bl=bl_label" in url
        assert "source-path" in url
        assert url.startswith("https://stitch.withgoogle.com/_/Nemo/data/batchexecute?")

    @pytest.mark.unit
    def test_build_url_omits_bl_when_empty(self):
        url = build_url("A7f2qf", "12345", "", "/")
        assert "bl=" not in url

    @pytest.mark.unit
    def test_build_url_default_params(self):
        url = build_url("A7f2qf", "12345")
        assert "hl=en" in url
        assert "rt=c" in url


class TestDecoder:
    """Tests for ``core/rpc/decoder.py``."""

    REALISTIC_RESPONSE = (
        b')]}\'\n'
        b'\n'
        b'69\n'
        b'[["wrb.fr","A7f2qf","[[\\"projects/123\\",\\"Test Project\\"]]",null,null,null,"generic"]]\n'
        b'59\n'
        b'[["di",157],["af.httprm",157,"6840575780498300498",12]]\n'
    )

    @pytest.mark.unit
    def test_strip_prefix_bytes(self):
        result = strip_prefix(b")]}'\\nfoo")
        # Removes prefix and leading newlines
        assert not result.startswith(")]}'")

    @pytest.mark.unit
    def test_strip_prefix_str(self):
        result = strip_prefix(")]}'  \nfoo")
        # Code strips )]}' prefix (4 chars) then lstrip("\n") — spaces remain
        assert result == "  \nfoo"

    @pytest.mark.unit
    def test_strip_prefix_str_newline_only(self):
        result = strip_prefix(")]}'  \n\nfoo")
        # After removing 4 chars: "  \n\nfoo", lstrip("\n") doesn't strip spaces
        assert result == "  \n\nfoo"

    @pytest.mark.unit
    def test_strip_prefix_immediate_newline(self):
        result = strip_prefix(")]}'  \n\nhello")
        # prefix removed: "  \n\nhello" — lstrip("\n") only strips leading \n, not spaces
        assert "hello" in result

    @pytest.mark.unit
    def test_strip_prefix_no_prefix(self):
        result = strip_prefix("just plain text")
        assert result == "just plain text"

    @pytest.mark.unit
    def test_strip_prefix_bytes_decoded(self):
        result = strip_prefix(b")]}'  \nhello")
        assert isinstance(result, str)
        assert "hello" in result

    @pytest.mark.unit
    def test_parse_chunks_extracts_json_arrays(self):
        text = (
            '69\n'
            '[["wrb.fr","A7f2qf","[[1,2,3]]",null,null,null,"generic"]]\n'
            '59\n'
            '[["di",157],["af.httprm",157,"123",12]]\n'
        )
        chunks = parse_chunks(text)
        assert len(chunks) == 2
        # First chunk is the wrb.fr chunk
        parsed = json.loads(chunks[0])
        assert parsed[0][0] == "wrb.fr"
        assert parsed[0][1] == "A7f2qf"

    @pytest.mark.unit
    def test_parse_chunks_empty_input(self):
        assert parse_chunks("") == []

    @pytest.mark.unit
    def test_parse_chunks_whitespace_only(self):
        assert parse_chunks("   \n\n  ") == []

    @pytest.mark.unit
    def test_extract_result_finds_wrb_fr_entry(self):
        chunks = [
            json.dumps([["wrb.fr", "A7f2qf", '[["projects/123","Test"]]', None, None, None, "generic"]]),
            json.dumps([["di", 157], ["af.httprm", 157, "123", 12]]),
        ]
        result = extract_result(chunks, "A7f2qf")
        assert result == [["projects/123", "Test"]]

    @pytest.mark.unit
    def test_extract_result_returns_none_for_null_data(self):
        chunks = [
            json.dumps([["wrb.fr", "A7f2qf", None, None, None, None, "generic"]]),
        ]
        result = extract_result(chunks, "A7f2qf")
        assert result is None

    @pytest.mark.unit
    def test_extract_result_raises_auth_error_code_7(self):
        chunks = [json.dumps([["er", 7]])]
        with pytest.raises(AuthError, match="Auth error"):
            extract_result(chunks, "A7f2qf")

    @pytest.mark.unit
    def test_extract_result_raises_auth_error_code_9(self):
        chunks = [json.dumps([["er", 9]])]
        with pytest.raises(AuthError, match="Auth error"):
            extract_result(chunks, "A7f2qf")

    @pytest.mark.unit
    def test_extract_result_raises_rpc_error_on_other_codes(self):
        chunks = [json.dumps([["er", 3]])]
        with pytest.raises(RPCError, match="RPC error code 3"):
            extract_result(chunks, "A7f2qf")

    @pytest.mark.unit
    def test_extract_result_raises_rpc_error_when_not_found(self):
        chunks = [json.dumps([["wrb.fr", "XYZ123", '"data"', None]])]
        with pytest.raises(RPCError, match="not found"):
            extract_result(chunks, "A7f2qf")

    @pytest.mark.unit
    def test_extract_result_raises_rpc_error_empty_chunks(self):
        with pytest.raises(RPCError, match="not found"):
            extract_result([], "A7f2qf")

    @pytest.mark.unit
    def test_decode_response_full_pipeline(self):
        raw = (
            ")]}'  \n"
            "69\n"
            '[["wrb.fr","A7f2qf","[[\\"id1\\",\\"Title\\"]]",null,null,null,"generic"]]\n'
            "59\n"
            '[["di",157],["af.httprm",157,"123",12]]\n'
        )
        result = decode_response(raw, "A7f2qf")
        assert result == [["id1", "Title"]]

    @pytest.mark.unit
    def test_decode_response_from_bytes(self):
        raw = (
            b")]}'  \n"
            b"69\n"
            b'[["wrb.fr","A7f2qf","[1,2,3]",null,null,null,"generic"]]\n'
        )
        result = decode_response(raw, "A7f2qf")
        assert result == [1, 2, 3]


# =====================================================================
# 2. Exception Tests
# =====================================================================


class TestExceptions:
    """Tests for ``core/exceptions.py``."""

    @pytest.mark.unit
    def test_stitch_error_is_base(self):
        assert issubclass(AuthError, StitchError)
        assert issubclass(RateLimitError, StitchError)
        assert issubclass(NetworkError, StitchError)
        assert issubclass(ServerError, StitchError)
        assert issubclass(NotFoundError, StitchError)
        assert issubclass(RPCError, StitchError)

    @pytest.mark.unit
    def test_stitch_error_inherits_exception(self):
        assert issubclass(StitchError, Exception)

    @pytest.mark.unit
    def test_auth_error_recoverable_default(self):
        err = AuthError()
        assert err.recoverable is True

    @pytest.mark.unit
    def test_auth_error_recoverable_false(self):
        err = AuthError("fatal", recoverable=False)
        assert err.recoverable is False
        assert str(err) == "fatal"

    @pytest.mark.unit
    def test_rate_limit_error_retry_after(self):
        err = RateLimitError("slow down", retry_after=30.0)
        assert err.retry_after == 30.0

    @pytest.mark.unit
    def test_rate_limit_error_retry_after_none(self):
        err = RateLimitError()
        assert err.retry_after is None

    @pytest.mark.unit
    def test_server_error_status_code(self):
        err = ServerError("bad gateway", status_code=502)
        assert err.status_code == 502

    @pytest.mark.unit
    def test_server_error_default_status(self):
        err = ServerError()
        assert err.status_code == 500

    @pytest.mark.unit
    def test_not_found_error_message(self):
        err = NotFoundError("project 123")
        assert str(err) == "project 123"

    @pytest.mark.unit
    def test_rpc_error_message(self):
        err = RPCError("method not found")
        assert str(err) == "method not found"

    @pytest.mark.unit
    def test_network_error_message(self):
        err = NetworkError("timeout")
        assert str(err) == "timeout"


# =====================================================================
# 3. Model Parser Tests
# =====================================================================


class TestParseProject:
    """Tests for ``parse_project``."""

    @pytest.mark.unit
    def test_full_project(self):
        raw = [
            "projects/456",      # [0] resource_name
            "My Design",         # [1] title
            2,                   # [2] type
            [1711000000, 0],     # [3] created_at
            [1711100000, 0],     # [4] modified_at
            4,                   # [5] status
            ["file/res", None, "https://thumb.example.com/img.png"],  # [6] thumbnail
            1,                   # [7] owner
            1,                   # [8] theme_mode
        ]
        p = parse_project(raw)
        assert isinstance(p, Project)
        assert p.id == "456"
        assert p.resource_name == "projects/456"
        assert p.title == "My Design"
        assert p.created_at == 1711000000.0
        assert p.modified_at == 1711100000.0
        assert p.status == 4
        assert p.thumbnail_url == "https://thumb.example.com/img.png"
        assert p.owner is True
        assert p.theme_mode == 1

    @pytest.mark.unit
    def test_missing_optional_fields(self):
        raw = ["projects/789", None, None, None, None, None, None, None, None]
        p = parse_project(raw)
        assert p is not None
        assert p.id == "789"
        assert p.title is None
        assert p.created_at is None
        assert p.modified_at is None
        assert p.thumbnail_url is None

    @pytest.mark.unit
    def test_short_list(self):
        raw = ["projects/10"]
        p = parse_project(raw)
        assert p is not None
        assert p.id == "10"

    @pytest.mark.unit
    def test_returns_none_for_none(self):
        assert parse_project(None) is None

    @pytest.mark.unit
    def test_returns_none_for_empty_list(self):
        assert parse_project([]) is None

    @pytest.mark.unit
    def test_returns_none_for_non_list(self):
        assert parse_project("not a list") is None

    @pytest.mark.unit
    def test_returns_none_for_empty_resource_name(self):
        assert parse_project([None, "title"]) is None
        assert parse_project(["", "title"]) is None


class TestParseScreen:
    """Tests for ``parse_screen``."""

    @pytest.mark.unit
    def test_full_screen(self):
        raw = [
            ["file/thumb", None, "https://thumb.example.com/screen.png"],   # [0] thumbnail
            ["file/html", None, "https://dl.example.com/screen.html", None, None, "text/html"],  # [1] html
            None,  # [2]
            None,  # [3]
            "screen_abc",   # [4] id
            "AgentX",       # [5] agent_name
            390,            # [6] width
            844,            # [7] height
            "Login Page",   # [8] name
            "A login form", # [9] description
            "projects/1/screens/screen_abc",  # [10] resource_name
        ]
        s = parse_screen(raw)
        assert isinstance(s, Screen)
        assert s.id == "screen_abc"
        assert s.name == "Login Page"
        assert s.description == "A login form"
        assert s.html_url == "https://dl.example.com/screen.html"
        assert s.thumbnail_url == "https://thumb.example.com/screen.png"
        assert s.agent_name == "AgentX"
        assert s.width == 390
        assert s.height == 844

    @pytest.mark.unit
    def test_missing_thumbnail_and_html(self):
        raw = [None, None, None, None, "s1", "agent", 100, 200, "Page", "", "res/s1"]
        s = parse_screen(raw)
        assert s is not None
        assert s.thumbnail_url is None
        assert s.html_url is None

    @pytest.mark.unit
    def test_returns_none_for_missing_id(self):
        raw = [None, None, None, None, None]
        assert parse_screen(raw) is None

    @pytest.mark.unit
    def test_returns_none_for_none(self):
        assert parse_screen(None) is None

    @pytest.mark.unit
    def test_returns_none_for_empty_list(self):
        assert parse_screen([]) is None


class TestParseSession:
    """Tests for ``parse_session``."""

    @pytest.mark.unit
    def test_full_session(self):
        raw = [
            "projects/1/sessions/sess_42",  # [0] resource_name
            None,                           # [1]
            2,                              # [2] status = completed
            ["Build a login page"],         # [3] prompt
            None,                           # [4] results
            [1711200000, 0],                # [5] timestamp
        ]
        s = parse_session(raw)
        assert isinstance(s, Session)
        assert s.id == "sess_42"
        assert s.resource_name == "projects/1/sessions/sess_42"
        assert s.prompt == "Build a login page"
        assert s.status == 2
        assert s.timestamp == 1711200000.0

    @pytest.mark.unit
    def test_pending_session(self):
        raw = ["projects/1/sessions/sess_1", None, None, ["Hello"], None, None]
        s = parse_session(raw)
        assert s is not None
        assert s.status is None

    @pytest.mark.unit
    def test_string_prompt_info(self):
        raw = ["projects/1/sessions/s2", None, 1, "direct prompt", None, None]
        s = parse_session(raw)
        assert s is not None
        assert s.prompt == "direct prompt"

    @pytest.mark.unit
    def test_returns_none_for_none(self):
        assert parse_session(None) is None

    @pytest.mark.unit
    def test_returns_none_for_empty_list(self):
        assert parse_session([]) is None

    @pytest.mark.unit
    def test_returns_none_for_non_string_resource(self):
        assert parse_session([12345]) is None


# =====================================================================
# 4. Client Tests (mocked HTTP)
# =====================================================================


def _make_batchexecute_response(rpc_id: str, payload_json: str) -> bytes:
    """Build a realistic batchexecute HTTP response body."""
    inner = json.dumps([["wrb.fr", rpc_id, payload_json, None, None, None, "generic"]])
    footer = json.dumps([["di", 157], ["af.httprm", 157, "123", 12]])
    body = f")]}}'\n\n{len(inner)}\n{inner}\n{len(footer)}\n{footer}\n"
    return body.encode("utf-8")


def _mock_httpx_response(status_code=200, content=b"", headers=None, text=""):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.content = content
    resp.text = text or content.decode("utf-8", errors="replace")
    resp.headers = headers or {}
    return resp


class TestStitchClient:
    """Tests for ``core/client.py`` StitchClient with mocked HTTP."""

    @pytest.fixture(autouse=True)
    def _patch_auth(self):
        """Patch auth functions so no real filesystem or network is touched."""
        with patch("cli_web.stitch.core.client.load_cookies", return_value={"SID": "fake"}), \
             patch("cli_web.stitch.core.client.fetch_tokens", return_value=("csrf", "sid", "bl")), \
             patch("cli_web.stitch.core.client.get_session") as mock_sess:
            state = MagicMock()
            state.next_req_id.return_value = 200000
            mock_sess.return_value = state
            yield

    def _make_client(self):
        from cli_web.stitch.core.client import StitchClient
        return StitchClient()

    @pytest.mark.unit
    def test_list_projects_parses_response(self):
        payload = json.dumps([[["projects/100", "Design A"], ["projects/200", "Design B"]]])
        resp_body = _make_batchexecute_response("A7f2qf", payload)
        mock_resp = _mock_httpx_response(200, resp_body)

        with patch("cli_web.stitch.core.client.httpx.post", return_value=mock_resp):
            client = self._make_client()
            projects = client.list_projects()
            assert len(projects) == 2
            assert projects[0].id == "100"
            assert projects[1].title == "Design B"

    @pytest.mark.unit
    def test_list_projects_empty(self):
        payload = json.dumps([])
        resp_body = _make_batchexecute_response("A7f2qf", payload)
        mock_resp = _mock_httpx_response(200, resp_body)

        with patch("cli_web.stitch.core.client.httpx.post", return_value=mock_resp):
            client = self._make_client()
            projects = client.list_projects()
            assert projects == []

    @pytest.mark.unit
    def test_auth_error_on_401_retries_then_raises(self):
        mock_resp = _mock_httpx_response(401, b"unauthorized", text="unauthorized")
        with patch("cli_web.stitch.core.client.httpx.post", return_value=mock_resp), \
             patch("cli_web.stitch.core.client.StitchClient._refresh_tokens"):
            client = self._make_client()
            # First call with retry_on_auth=True will get 401, refresh, retry with False, get 401 again
            # The second call (retry_on_auth=False) still gets 401 but won't retry —
            # it falls through to the status check which raises AuthError via the 401 branch.
            # Actually, looking at the code: on 401/403 with retry_on_auth=True it retries.
            # On the retry (retry_on_auth=False), it gets 401 again, doesn't retry,
            # falls through to >= 400 generic handler.
            with pytest.raises(StitchError):
                client.list_projects()

    @pytest.mark.unit
    def test_auth_error_on_403(self):
        mock_resp_403 = _mock_httpx_response(403, b"forbidden", text="forbidden")
        # After retry the second call also gets 403
        with patch("cli_web.stitch.core.client.httpx.post", return_value=mock_resp_403), \
             patch("cli_web.stitch.core.client.StitchClient._refresh_tokens"):
            client = self._make_client()
            with pytest.raises(StitchError):
                client.list_projects()

    @pytest.mark.unit
    def test_rate_limit_error_on_429(self):
        mock_resp = _mock_httpx_response(429, b"too many", headers={"Retry-After": "60"}, text="too many")
        with patch("cli_web.stitch.core.client.httpx.post", return_value=mock_resp):
            client = self._make_client()
            with pytest.raises(RateLimitError) as exc_info:
                client.list_projects()
            assert exc_info.value.retry_after == 60.0

    @pytest.mark.unit
    def test_server_error_on_500(self):
        mock_resp = _mock_httpx_response(500, b"internal error", text="internal error")
        with patch("cli_web.stitch.core.client.httpx.post", return_value=mock_resp):
            client = self._make_client()
            with pytest.raises(ServerError) as exc_info:
                client.list_projects()
            assert exc_info.value.status_code == 500

    @pytest.mark.unit
    def test_server_error_on_503(self):
        mock_resp = _mock_httpx_response(503, b"unavailable", text="unavailable")
        with patch("cli_web.stitch.core.client.httpx.post", return_value=mock_resp):
            client = self._make_client()
            with pytest.raises(ServerError) as exc_info:
                client.list_projects()
            assert exc_info.value.status_code == 503

    @pytest.mark.unit
    def test_not_found_error_on_404(self):
        mock_resp = _mock_httpx_response(404, b"not found", text="not found")
        with patch("cli_web.stitch.core.client.httpx.post", return_value=mock_resp):
            client = self._make_client()
            with pytest.raises(NotFoundError):
                client.list_projects()

    @pytest.mark.unit
    def test_network_error_on_connect_failure(self):
        with patch("cli_web.stitch.core.client.httpx.post", side_effect=httpx.ConnectError("refused")):
            client = self._make_client()
            with pytest.raises(NetworkError, match="Connection failed"):
                client.list_projects()

    @pytest.mark.unit
    def test_network_error_on_timeout(self):
        with patch("cli_web.stitch.core.client.httpx.post", side_effect=httpx.TimeoutException("timed out")):
            client = self._make_client()
            with pytest.raises(NetworkError, match="timed out"):
                client.list_projects()

    @pytest.mark.unit
    def test_network_error_on_generic_request_error(self):
        with patch(
            "cli_web.stitch.core.client.httpx.post",
            side_effect=httpx.RequestError("dns failed", request=MagicMock()),
        ):
            client = self._make_client()
            with pytest.raises(NetworkError, match="Network error"):
                client.list_projects()


# =====================================================================
# 5. Helper Tests
# =====================================================================


class TestResolvePartialId:
    """Tests for ``resolve_partial_id``."""

    @dataclass
    class _Item:
        id: str
        name: str = ""

    @pytest.mark.unit
    def test_exact_match(self):
        items = [self._Item("abc123", "A"), self._Item("abc456", "B")]
        result = resolve_partial_id("abc123", items)
        assert result.id == "abc123"

    @pytest.mark.unit
    def test_unique_prefix(self):
        items = [self._Item("abc123", "A"), self._Item("xyz789", "B")]
        result = resolve_partial_id("abc", items)
        assert result.id == "abc123"

    @pytest.mark.unit
    def test_ambiguous_prefix_raises(self):
        items = [self._Item("abc123", "A"), self._Item("abc456", "B")]
        with pytest.raises(click.UsageError, match="Ambiguous"):
            resolve_partial_id("abc", items)

    @pytest.mark.unit
    def test_no_match_raises(self):
        items = [self._Item("abc123", "A")]
        with pytest.raises(click.UsageError, match="not found"):
            resolve_partial_id("zzz", items)

    @pytest.mark.unit
    def test_empty_items_raises(self):
        with pytest.raises(click.UsageError, match="not found"):
            resolve_partial_id("abc", [])

    @pytest.mark.unit
    def test_case_insensitive_prefix(self):
        items = [self._Item("ABC123", "A"), self._Item("xyz789", "B")]
        result = resolve_partial_id("abc", items)
        assert result.id == "ABC123"

    @pytest.mark.unit
    def test_long_partial_requires_exact(self):
        """IDs >= 20 chars only do exact match, not prefix."""
        items = [self._Item("a" * 25, "A")]
        with pytest.raises(click.UsageError, match="not found"):
            resolve_partial_id("a" * 20, items)


class TestSanitizeFilename:
    """Tests for ``sanitize_filename``."""

    @pytest.mark.unit
    def test_removes_invalid_chars(self):
        assert sanitize_filename('he<>:"/\\|?*llo') == "he_________llo"

    @pytest.mark.unit
    def test_empty_string(self):
        assert sanitize_filename("") == "unnamed"

    @pytest.mark.unit
    def test_only_dots(self):
        assert sanitize_filename("...") == "unnamed"

    @pytest.mark.unit
    def test_long_name_truncated(self):
        name = "a" * 300
        result = sanitize_filename(name)
        assert len(result) == 240

    @pytest.mark.unit
    def test_custom_max_length(self):
        result = sanitize_filename("abcdefghij", max_length=5)
        assert result == "abcde"

    @pytest.mark.unit
    def test_normal_filename_unchanged(self):
        assert sanitize_filename("my_design_v2") == "my_design_v2"

    @pytest.mark.unit
    def test_strips_trailing_dots_and_spaces(self):
        assert sanitize_filename("file. . .") == "file"


class TestHandleErrors:
    """Tests for ``handle_errors`` context manager."""

    @pytest.mark.unit
    def test_auth_error_exit_code_1(self):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors():
                raise AuthError("expired")
        assert exc_info.value.code == 1

    @pytest.mark.unit
    def test_generic_exception_exit_code_2(self):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors():
                raise ValueError("oops")
        assert exc_info.value.code == 2

    @pytest.mark.unit
    def test_keyboard_interrupt_exit_130(self):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors():
                raise KeyboardInterrupt()
        assert exc_info.value.code == 130

    @pytest.mark.unit
    def test_not_found_error_exit_code_1(self):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors():
                raise NotFoundError("missing")
        assert exc_info.value.code == 1

    @pytest.mark.unit
    def test_rate_limit_exit_code_1(self):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors():
                raise RateLimitError("slow")
        assert exc_info.value.code == 1

    @pytest.mark.unit
    def test_json_mode_outputs_structured_error(self, capsys):
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise AuthError("token expired")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["error"] is True
        assert data["code"] == "AUTH_ERROR"
        assert "token expired" in data["message"]

    @pytest.mark.unit
    def test_json_mode_keyboard_interrupt(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors(json_mode=True):
                raise KeyboardInterrupt()
        assert exc_info.value.code == 130
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["code"] == "INTERRUPTED"

    @pytest.mark.unit
    def test_json_mode_internal_error(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors(json_mode=True):
                raise TypeError("bad type")
        assert exc_info.value.code == 2
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["code"] == "INTERNAL_ERROR"

    @pytest.mark.unit
    def test_no_error_passes_through(self):
        with handle_errors():
            x = 1 + 1
        assert x == 2

    @pytest.mark.unit
    def test_server_error_exit_code_1(self):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors():
                raise ServerError("down", status_code=502)
        assert exc_info.value.code == 1

    @pytest.mark.unit
    def test_network_error_exit_code_1(self):
        with pytest.raises(SystemExit) as exc_info:
            with handle_errors():
                raise NetworkError("disconnected")
        assert exc_info.value.code == 1


class TestContextValueRoundTrip:
    """Tests for ``get_context_value`` / ``set_context_value``."""

    @pytest.mark.unit
    def test_round_trip(self, tmp_path):
        ctx_file = tmp_path / "context.json"
        with patch("cli_web.stitch.utils.helpers.CONFIG_DIR", tmp_path), \
             patch("cli_web.stitch.utils.helpers.CONTEXT_FILE", ctx_file):
            set_context_value("project_id", "proj_123")
            assert get_context_value("project_id") == "proj_123"

    @pytest.mark.unit
    def test_get_missing_key_returns_none(self, tmp_path):
        ctx_file = tmp_path / "context.json"
        with patch("cli_web.stitch.utils.helpers.CONFIG_DIR", tmp_path), \
             patch("cli_web.stitch.utils.helpers.CONTEXT_FILE", ctx_file):
            set_context_value("a", "1")
            assert get_context_value("b") is None

    @pytest.mark.unit
    def test_get_no_file_returns_none(self, tmp_path):
        ctx_file = tmp_path / "context.json"
        with patch("cli_web.stitch.utils.helpers.CONTEXT_FILE", ctx_file):
            assert get_context_value("anything") is None

    @pytest.mark.unit
    def test_set_overwrites_existing(self, tmp_path):
        ctx_file = tmp_path / "context.json"
        with patch("cli_web.stitch.utils.helpers.CONFIG_DIR", tmp_path), \
             patch("cli_web.stitch.utils.helpers.CONTEXT_FILE", ctx_file):
            set_context_value("k", "v1")
            set_context_value("k", "v2")
            assert get_context_value("k") == "v2"

    @pytest.mark.unit
    def test_multiple_keys(self, tmp_path):
        ctx_file = tmp_path / "context.json"
        with patch("cli_web.stitch.utils.helpers.CONFIG_DIR", tmp_path), \
             patch("cli_web.stitch.utils.helpers.CONTEXT_FILE", ctx_file):
            set_context_value("a", "1")
            set_context_value("b", "2")
            assert get_context_value("a") == "1"
            assert get_context_value("b") == "2"


# =====================================================================
# 6. Auth Module Tests (mocked filesystem)
# =====================================================================


class TestLoadCookies:
    """Tests for ``core/auth.load_cookies``."""

    @pytest.mark.unit
    def test_loads_from_file(self, tmp_path):
        auth_file = tmp_path / "auth.json"
        cookies = {"SID": "abc", "HSID": "def"}
        auth_file.write_text(json.dumps({"cookies": cookies}), encoding="utf-8")

        with patch("cli_web.stitch.core.auth.AUTH_FILE", auth_file), \
             patch.dict(os.environ, {}, clear=False):
            # Remove env var if present
            os.environ.pop("CLI_WEB_STITCH_AUTH_JSON", None)
            from cli_web.stitch.core.auth import load_cookies
            result = load_cookies()
        assert result == cookies

    @pytest.mark.unit
    def test_loads_from_env_var(self, tmp_path):
        auth_file = tmp_path / "auth.json"  # Does not exist
        env_data = json.dumps({"cookies": {"SID": "from_env"}})

        with patch("cli_web.stitch.core.auth.AUTH_FILE", auth_file), \
             patch.dict(os.environ, {"CLI_WEB_STITCH_AUTH_JSON": env_data}):
            from cli_web.stitch.core.auth import load_cookies
            result = load_cookies()
        assert result == {"SID": "from_env"}

    @pytest.mark.unit
    def test_raises_auth_error_when_no_file(self, tmp_path):
        auth_file = tmp_path / "auth.json"  # Does not exist

        with patch("cli_web.stitch.core.auth.AUTH_FILE", auth_file), \
             patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLI_WEB_STITCH_AUTH_JSON", None)
            from cli_web.stitch.core.auth import load_cookies
            with pytest.raises(AuthError, match="Not authenticated"):
                load_cookies()

    @pytest.mark.unit
    def test_handles_list_format_cookies(self, tmp_path):
        """Raw playwright state-save format: cookies is a list of objects."""
        auth_file = tmp_path / "auth.json"
        raw_cookies = [
            {"name": "SID", "value": "sid_val", "domain": ".google.com"},
            {"name": "HSID", "value": "hsid_val", "domain": ".google.com"},
            {"name": "tracking", "value": "x", "domain": ".other.com"},
        ]
        auth_file.write_text(json.dumps({"cookies": raw_cookies}), encoding="utf-8")

        with patch("cli_web.stitch.core.auth.AUTH_FILE", auth_file), \
             patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLI_WEB_STITCH_AUTH_JSON", None)
            from cli_web.stitch.core.auth import load_cookies
            result = load_cookies()
        assert "SID" in result
        assert "HSID" in result
        # Non-Google domain cookies should be filtered out
        assert "tracking" not in result


class TestExtractCookies:
    """Tests for ``core/auth._extract_cookies``."""

    @pytest.mark.unit
    def test_prioritizes_google_com_over_regional(self):
        from cli_web.stitch.core.auth import _extract_cookies
        raw = [
            {"name": "SID", "value": "regional", "domain": ".google.co.il"},
            {"name": "SID", "value": "global", "domain": ".google.com"},
        ]
        result = _extract_cookies(raw)
        assert result["SID"] == "global"

    @pytest.mark.unit
    def test_regional_cookie_accepted_when_no_global(self):
        from cli_web.stitch.core.auth import _extract_cookies
        raw = [
            {"name": "SID", "value": "regional", "domain": ".google.co.il"},
        ]
        result = _extract_cookies(raw)
        assert result["SID"] == "regional"

    @pytest.mark.unit
    def test_global_overrides_even_if_regional_comes_second(self):
        from cli_web.stitch.core.auth import _extract_cookies
        raw = [
            {"name": "SID", "value": "global", "domain": ".google.com"},
            {"name": "SID", "value": "regional", "domain": ".google.de"},
        ]
        result = _extract_cookies(raw)
        # .google.com should always win
        assert result["SID"] == "global"

    @pytest.mark.unit
    def test_filters_out_non_google_domains(self):
        from cli_web.stitch.core.auth import _extract_cookies
        raw = [
            {"name": "SID", "value": "val", "domain": ".google.com"},
            {"name": "tracking", "value": "x", "domain": ".facebook.com"},
        ]
        result = _extract_cookies(raw)
        assert "SID" in result
        assert "tracking" not in result

    @pytest.mark.unit
    def test_accepts_stitch_domain(self):
        from cli_web.stitch.core.auth import _extract_cookies
        raw = [
            {"name": "NID", "value": "nid_val", "domain": ".stitch.withgoogle.com"},
        ]
        result = _extract_cookies(raw)
        assert result["NID"] == "nid_val"

    @pytest.mark.unit
    def test_empty_list(self):
        from cli_web.stitch.core.auth import _extract_cookies
        assert _extract_cookies([]) == {}

    @pytest.mark.unit
    def test_skips_entries_without_name(self):
        from cli_web.stitch.core.auth import _extract_cookies
        raw = [
            {"name": "", "value": "val", "domain": ".google.com"},
        ]
        assert _extract_cookies(raw) == {}


class TestGetAuthStatus:
    """Tests for ``core/auth.get_auth_status``."""

    @pytest.mark.unit
    def test_not_configured(self, tmp_path):
        auth_file = tmp_path / "auth.json"  # Does not exist
        with patch("cli_web.stitch.core.auth.AUTH_FILE", auth_file):
            from cli_web.stitch.core.auth import get_auth_status
            status = get_auth_status()
        assert status["configured"] is False

    @pytest.mark.unit
    def test_configured_and_valid(self, tmp_path):
        auth_file = tmp_path / "auth.json"
        auth_file.write_text(json.dumps({"cookies": {"SID": "x"}}), encoding="utf-8")

        with patch("cli_web.stitch.core.auth.AUTH_FILE", auth_file), \
             patch("cli_web.stitch.core.auth.load_cookies", return_value={"SID": "x"}), \
             patch("cli_web.stitch.core.auth.fetch_tokens", return_value=("csrf", "1234567890", "bl")):
            from cli_web.stitch.core.auth import get_auth_status
            status = get_auth_status()
        assert status["configured"] is True
        assert status["valid"] is True
        assert status["cookie_count"] == 1

    @pytest.mark.unit
    def test_configured_but_expired(self, tmp_path):
        auth_file = tmp_path / "auth.json"
        auth_file.write_text(json.dumps({"cookies": {"SID": "x"}}), encoding="utf-8")

        with patch("cli_web.stitch.core.auth.AUTH_FILE", auth_file), \
             patch("cli_web.stitch.core.auth.load_cookies", return_value={"SID": "x"}), \
             patch("cli_web.stitch.core.auth.fetch_tokens", side_effect=AuthError("expired")):
            from cli_web.stitch.core.auth import get_auth_status
            status = get_auth_status()
        assert status["configured"] is True
        assert status["valid"] is False
        assert "expired" in status["message"]
