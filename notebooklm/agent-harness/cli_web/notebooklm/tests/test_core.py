"""Unit tests for core modules — mocked HTTP, no live calls."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# ── Session extraction tests ──────────────────────────────────────────

from cli_web.notebooklm.core.session import extract_session_params, SessionParams


FAKE_HTML = '''
<html><head><script>
window.WIZ_global_data = {
  "SNlM0e":"CSRF_TOKEN_123",
  "FdrFJe":"SESSION_ID_456",
  "cfb2h":"boq_labs-tailwind-ui_20240101.00_p0"
};
</script></head></html>
'''


def test_extract_session_params_valid():
    params = extract_session_params(FAKE_HTML)
    assert params.at == "CSRF_TOKEN_123"
    assert params.f_sid == "SESSION_ID_456"
    assert params.bl == "boq_labs-tailwind-ui_20240101.00_p0"


def test_extract_session_params_missing_at():
    html = FAKE_HTML.replace('"SNlM0e"', '"REMOVED"')
    with pytest.raises(ValueError, match="CSRF token"):
        extract_session_params(html)


def test_extract_session_params_missing_sid():
    html = FAKE_HTML.replace('"FdrFJe"', '"REMOVED"')
    with pytest.raises(ValueError, match="session ID"):
        extract_session_params(html)


def test_extract_session_params_missing_bl():
    html = FAKE_HTML.replace('"cfb2h"', '"REMOVED"')
    with pytest.raises(ValueError, match="build label"):
        extract_session_params(html)


# ── Auth tests ─────────────────────────────────────────────────────────

from cli_web.notebooklm.core.auth import (
    save_cookies,
    load_cookies,
    validate_cookies,
    build_cookie_header,
    REQUIRED_COOKIES,
    AUTH_FILE,
)


@pytest.fixture
def tmp_auth_dir(tmp_path, monkeypatch):
    """Redirect auth storage to a temp directory."""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr("cli_web.notebooklm.core.auth.AUTH_FILE", auth_file)
    monkeypatch.setattr("cli_web.notebooklm.core.auth.CONFIG_DIR", tmp_path)
    return tmp_path


def _full_cookies() -> dict[str, str]:
    return {c: f"value_{c}" for c in REQUIRED_COOKIES}


def test_save_and_load_cookies(tmp_auth_dir):
    cookies = _full_cookies()
    save_cookies(cookies)
    loaded = load_cookies()
    assert loaded == cookies


def test_load_cookies_missing_file(tmp_auth_dir):
    with pytest.raises(FileNotFoundError):
        load_cookies()


def test_validate_cookies_all_present():
    cookies = _full_cookies()
    assert validate_cookies(cookies) == []


def test_validate_cookies_missing():
    cookies = {"SID": "x", "SSID": "y"}
    missing = validate_cookies(cookies)
    assert "HSID" in missing
    assert "OSID" in missing
    assert len(missing) == len(REQUIRED_COOKIES) - 2


def test_build_cookie_header():
    header = build_cookie_header({"SID": "abc", "HSID": "def"})
    assert "SID=abc" in header
    assert "HSID=def" in header
    assert "; " in header


# ── Client parsing tests ──────────────────────────────────────────────

from cli_web.notebooklm.core.client import (
    NotebookLMClient,
    _extract_chunks,
)

# A realistic batchexecute response
_INNER_DATA = [["notebook-123", "My Notebook", "", "", 1700000000, 1700000001, 3]]
_INNER_JSON = json.dumps(_INNER_DATA)
_OUTER_ARRAY = json.dumps([
    ["wrb.fr", "wXbhsf", _INNER_JSON, None, None, None, "generic"]
])
_BATCH_PREFIX = ")]}'"
_BATCH_RESPONSE = _BATCH_PREFIX + "\n\n" + str(len(_OUTER_ARRAY)) + "\n" + _OUTER_ARRAY


def test_parse_batchexecute_simple():
    result = NotebookLMClient._parse_batchexecute(_BATCH_RESPONSE)
    assert result == _INNER_DATA


def test_parse_batchexecute_malformed():
    with pytest.raises(ValueError):
        NotebookLMClient._parse_batchexecute(")]}'\n\n5\nhello")


def test_extract_chunks_single():
    payload = '13\n["some_data"]'
    chunks = _extract_chunks(payload)
    assert len(chunks) == 1
    assert chunks[0] == '["some_data"]'


def test_extract_chunks_multi():
    c1 = '["first"]'
    c2 = '["second"]'
    payload = f"{len(c1)}\n{c1}{len(c2)}\n{c2}"
    chunks = _extract_chunks(payload)
    assert len(chunks) == 2


# ── Client RPC (mocked HTTP) ──────────────────────────────────────────

@pytest.fixture
def mock_client(tmp_auth_dir):
    """Create a client with mocked session params and HTTP."""
    cookies = _full_cookies()
    save_cookies(cookies)

    client = NotebookLMClient(cookies=cookies)
    client.session_params = SessionParams(
        at="fake_csrf", f_sid="fake_sid", bl="fake_bl"
    )
    return client


def test_rpc_list_notebooks(mock_client):
    mock_resp = mock.Mock()
    mock_resp.status_code = 200
    mock_resp.text = _BATCH_RESPONSE
    mock_resp.raise_for_status = mock.Mock()

    with mock.patch.object(mock_client._http, "post", return_value=mock_resp) as m:
        result = mock_client.rpc("wXbhsf", [None, 1, None, [2]])

    assert result == _INNER_DATA
    m.assert_called_once()
    call_kwargs = m.call_args
    assert "wXbhsf" in call_kwargs.kwargs["params"]["rpcids"]


def test_rpc_http_error(mock_client):
    mock_resp = mock.Mock()
    mock_resp.status_code = 401
    mock_resp.raise_for_status = mock.Mock(
        side_effect=Exception("401 Unauthorized")
    )

    with mock.patch.object(mock_client._http, "post", return_value=mock_resp):
        with pytest.raises(Exception, match="401"):
            mock_client.rpc("wXbhsf", [None, 1, None, [2]])


# ── Model tests ───────────────────────────────────────────────────────

from cli_web.notebooklm.core.models import Notebook, Source, ChatMessage, ChatSession


def test_notebook_to_dict():
    nb = Notebook(id="abc", title="Test", emoji="📓", source_count=5)
    d = nb.to_dict()
    assert d["id"] == "abc"
    assert d["title"] == "Test"
    assert d["emoji"] == "📓"
    assert d["source_count"] == 5


def test_source_to_dict():
    src = Source(id="s1", title="Paper", source_type="pdf", word_count=1000)
    d = src.to_dict()
    assert d["source_type"] == "pdf"
    assert d["word_count"] == 1000


def test_chat_session_to_dict():
    msg = ChatMessage(role="user", content="Hello")
    session = ChatSession(id="c1", messages=[msg], notebook_id="nb1")
    d = session.to_dict()
    assert len(d["messages"]) == 1
    assert d["messages"][0]["role"] == "user"
    assert d["messages"][0]["content"] == "Hello"


# ── Output helper tests ───────────────────────────────────────────────

from cli_web.notebooklm.utils.output import output_json, truncate


def test_output_json(capsys):
    output_json({"key": "value"})
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["key"] == "value"


def test_truncate_short():
    assert truncate("hello", 10) == "hello"


def test_truncate_long():
    result = truncate("a" * 100, 20)
    assert len(result) == 20
    assert result.endswith("...")
