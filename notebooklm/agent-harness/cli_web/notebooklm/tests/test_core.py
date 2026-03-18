"""Comprehensive unit tests for the NotebookLM CLI core modules.

Covers:
- cli_web.notebooklm.core.rpc.encoder  (encode_request, build_url)
- cli_web.notebooklm.core.rpc.decoder  (strip_prefix, parse_chunks,
                                         extract_result, decode_response)
- cli_web.notebooklm.core.models       (parse_notebook, parse_source, parse_user)
- cli_web.notebooklm.core.client       (NotebookLMClient – HTTP mocked)
"""
import json
import unittest
import urllib.parse
from unittest.mock import MagicMock, patch

from cli_web.notebooklm.core.rpc.encoder import build_url, encode_request
from cli_web.notebooklm.core.rpc.decoder import (
    decode_response,
    extract_result,
    parse_chunks,
    strip_prefix,
)
from cli_web.notebooklm.core.exceptions import (
    AuthError,
    RPCError,
    RateLimitError,
    ServerError,
    NetworkError,
    NotebookLMError,
)
from cli_web.notebooklm.core.models import (
    Notebook,
    Source,
    User,
    parse_notebook,
    parse_source,
    parse_user,
)


# ---------------------------------------------------------------------------
# Helpers shared across client tests
# ---------------------------------------------------------------------------

def _make_batchexecute_response(rpc_id: str, result: object) -> bytes:
    """Build a minimal valid batchexecute response body for *rpc_id*.

    The decoder pipeline is:
        strip_prefix  →  parse_chunks  →  extract_result
    extract_result does json.loads(entry[2]), so entry[2] must be a JSON string
    whose decoded value is *result*.
    """
    entry = ["wrb.fr", rpc_id, json.dumps(result), None, None, None, "100000"]
    # The batchexecute chunk format is [["wrb.fr", rpc_id, ...]] — entry is a
    # direct element of the outer list, so ONE level of wrapping is correct.
    payload_str = json.dumps([entry])
    body = ")]}'" + "\n\n" + str(len(payload_str)) + "\n" + payload_str + "\n"
    return body.encode("utf-8")


def _make_mock_response(status_code: int, body: bytes) -> MagicMock:
    """Return a mock httpx.Response-alike object."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.content = body
    mock_resp.text = body.decode("utf-8", errors="replace")
    return mock_resp


# ===========================================================================
# 1.  RPC Encoder tests
# ===========================================================================

class TestEncodeRequest(unittest.TestCase):

    def _decode_body(self, body: str) -> dict:
        """URL-decode the encoded body into a plain dict."""
        return dict(urllib.parse.parse_qsl(body))

    def test_encode_request_body_format(self):
        """f.req must be JSON of [[["rpc_id", json.dumps(params), None, "generic"]]]."""
        body = encode_request("TestRPC", ["arg1", 42], "csrf-token")
        parsed = self._decode_body(body)

        freq = json.loads(parsed["f.req"])
        self.assertIsInstance(freq, list)
        self.assertEqual(len(freq), 1)

        inner_list = freq[0]
        self.assertEqual(len(inner_list), 1)

        entry = inner_list[0]
        self.assertEqual(entry[0], "TestRPC")
        self.assertEqual(json.loads(entry[1]), ["arg1", 42])
        self.assertIsNone(entry[2])
        self.assertEqual(entry[3], "generic")

    def test_encode_request_with_csrf(self):
        """The `at` field must carry the CSRF token verbatim."""
        body = encode_request("SomeRPC", [], "my-csrf-123")
        parsed = self._decode_body(body)
        self.assertEqual(parsed["at"], "my-csrf-123")

    def test_encode_request_list_params(self):
        """Params list is JSON-encoded as the second element of the RPC entry."""
        params = ["hello", None, 99]
        body = encode_request("RPC1", params, "tok")
        parsed = self._decode_body(body)

        freq = json.loads(parsed["f.req"])
        entry = freq[0][0]
        self.assertEqual(json.loads(entry[1]), params)

    def test_encode_request_empty_params(self):
        """Empty params list encodes as `[]` (JSON array) in f.req."""
        body = encode_request("RPC2", [], "tok")
        parsed = self._decode_body(body)

        freq = json.loads(parsed["f.req"])
        entry = freq[0][0]
        self.assertEqual(json.loads(entry[1]), [])

    def test_build_url_contains_rpcid(self):
        """URL must contain rpcids=<rpc_id> as a query parameter."""
        url = build_url("wXbhsf", "sess-123", "build-abc")
        qs = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        self.assertEqual(qs["rpcids"], "wXbhsf")

    def test_build_url_has_session_id(self):
        """URL must contain f.sid=<session_id>."""
        url = build_url("rLM1Ne", "my-session-id", "build-xyz")
        qs = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        self.assertEqual(qs["f.sid"], "my-session-id")

    def test_build_url_has_build_label(self):
        """URL must contain bl=<build_label>."""
        url = build_url("CCqFvf", "sess", "boq_labs-tailwind-ui_20240101.01_p0")
        qs = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        self.assertEqual(qs["bl"], "boq_labs-tailwind-ui_20240101.01_p0")

    def test_build_url_default_lang(self):
        """URL must contain hl=en when no lang is supplied."""
        url = build_url("VfAZjd", "sess", "build")
        qs = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        self.assertEqual(qs["hl"], "en")


# ===========================================================================
# 2.  RPC Decoder tests
# ===========================================================================

class TestStripPrefix(unittest.TestCase):

    def test_strip_prefix_removes_xssi(self):
        """)]}' + newline must be stripped, leaving the JSON body."""
        data = ")]}'\n[[\"foo\"]]"
        result = strip_prefix(data)
        self.assertEqual(result, "[[\"foo\"]]")

    def test_strip_prefix_bytes_input(self):
        """bytes input is decoded to str and the XSSI prefix is stripped."""
        data = b")]}'\n[[\"bar\"]]"
        result = strip_prefix(data)
        self.assertIsInstance(result, str)
        self.assertEqual(result, "[[\"bar\"]]")

    def test_strip_prefix_no_prefix(self):
        """When the prefix is absent the string is returned unchanged."""
        data = "[[\"no-prefix\"]]"
        result = strip_prefix(data)
        self.assertEqual(result, data)


class TestParseChunks(unittest.TestCase):

    def test_parse_chunks_extracts_arrays(self):
        """JSON arrays are extracted; length-hint digit lines are skipped."""
        text = "42\n[[\"wrb.fr\",\"RPC1\",\"result\"]]\n"
        chunks = parse_chunks(text)
        self.assertEqual(len(chunks), 1)
        parsed = json.loads(chunks[0])
        self.assertEqual(parsed[0][0], "wrb.fr")

    def test_parse_chunks_multiple_chunks(self):
        """Multiple JSON arrays on separate chunk lines are all returned."""
        chunk1 = json.dumps([["wrb.fr", "RPC1", "r1"]])
        chunk2 = json.dumps([["di", 157], ["af.httprm", 157, "abc", 1]])
        text = f"100\n{chunk1}\n59\n{chunk2}\n"
        chunks = parse_chunks(text)
        self.assertEqual(len(chunks), 2)

    def test_parse_chunks_skips_digit_only_lines(self):
        """Lines containing only digits (length hints) are not included as chunks."""
        text = "12345\n[[\"data\"]]\n"
        chunks = parse_chunks(text)
        # Should only find the JSON array, not try to parse "12345"
        self.assertEqual(len(chunks), 1)
        self.assertIn("data", chunks[0])


class TestExtractResult(unittest.TestCase):

    def _make_chunks(self, rpc_id: str, result: object) -> list[str]:
        """Build a minimal chunk list as produced by parse_chunks.

        parse_chunks returns strings like '[["wrb.fr", "rpc_id", "...", ...]]'
        where the outer list contains the entry as a direct element.
        """
        entry = ["wrb.fr", rpc_id, json.dumps(result), None, None, None, "100000"]
        return [json.dumps([entry])]

    def test_extract_result_found(self):
        """Finds wrb.fr entry for the given rpc_id and double-decodes it."""
        chunks = self._make_chunks("MyRPC", {"key": "value"})
        result = extract_result(chunks, "MyRPC")
        self.assertEqual(result, {"key": "value"})

    def test_extract_result_not_found(self):
        """Raises ValueError when rpc_id does not appear in any chunk."""
        chunks = self._make_chunks("SomeRPC", {})
        with self.assertRaises(ValueError):
            extract_result(chunks, "MissingRPC")

    def test_extract_result_error_code_7(self):
        """An 'er' entry with code 7 raises AuthError."""
        # Outer list contains the error entry as a direct element: [["er", 7]]
        error_chunk = json.dumps([["er", 7]])
        with self.assertRaises(AuthError):
            extract_result([error_chunk], "AnyRPC")

    def test_extract_result_error_code_9(self):
        """An 'er' entry with code 9 raises AuthError."""
        error_chunk = json.dumps([["er", 9]])
        with self.assertRaises(AuthError):
            extract_result([error_chunk], "AnyRPC")

    def test_extract_result_non_auth_error_code(self):
        """An 'er' entry with a code other than 7/9 raises RPCError (not AuthError)."""
        error_chunk = json.dumps([["er", 42]])
        with self.assertRaises(RPCError) as ctx:
            extract_result([error_chunk], "AnyRPC")
        # Must be RPCError but NOT the AuthError subclass
        self.assertNotIsInstance(ctx.exception, AuthError)

    def test_extract_result_none_payload(self):
        """entry[2] = None returns None without raising."""
        entry = ["wrb.fr", "NullRPC", None, None, None, None, "100000"]
        chunk = json.dumps([entry])
        result = extract_result([chunk], "NullRPC")
        self.assertIsNone(result)


class TestDecodeResponse(unittest.TestCase):

    def test_decode_response_full_pipeline(self):
        """Full pipeline: bytes with XSSI prefix → correct decoded object."""
        rpc_id = "TestRPC"
        expected = [{"key": "value"}]
        body = _make_batchexecute_response(rpc_id, expected)
        result = decode_response(body, rpc_id)
        self.assertEqual(result, expected)

    def test_decode_response_string_input(self):
        """decode_response also accepts a plain str (not bytes)."""
        rpc_id = "StrRPC"
        expected = {"a": 1}
        body_bytes = _make_batchexecute_response(rpc_id, expected)
        body_str = body_bytes.decode("utf-8")
        result = decode_response(body_str, rpc_id)
        self.assertEqual(result, expected)

    def test_decode_response_wrong_rpcid_raises(self):
        """ValueError raised when the body does not contain the requested rpc_id."""
        body = _make_batchexecute_response("RealRPC", {})
        with self.assertRaises(ValueError):
            decode_response(body, "WrongRPC")


# ===========================================================================
# 3.  Model parsing tests
# ===========================================================================

class TestParseNotebook(unittest.TestCase):

    # --- rLM1Ne / flat style ---

    def test_parse_notebook_flat_rlm1ne(self):
        """Flat rLM1Ne format: [title, sources, nb_id, emoji, null, flags]."""
        flags = [True, None, None, None, None,
                 [1700000000, 0],  # created_at
                 None, None,
                 [1700001000, 0]]  # updated_at
        raw = ["My Notebook", [], "nb-flat-id-001", "📔", None, flags]
        nb = parse_notebook(raw)

        self.assertIsNotNone(nb)
        self.assertEqual(nb.id, "nb-flat-id-001")
        self.assertEqual(nb.title, "My Notebook")
        self.assertEqual(nb.emoji, "📔")
        self.assertTrue(nb.is_pinned)
        self.assertEqual(nb.created_at, 1700000000)
        self.assertEqual(nb.updated_at, 1700001000)

    def test_parse_notebook_flat_source_count(self):
        """source_count reflects the length of the sources list in flat format."""
        raw = ["Title", [["s1"], ["s2"], ["s3"]], "nb-id-sc", "📓", None, []]
        nb = parse_notebook(raw)
        self.assertIsNotNone(nb)
        self.assertEqual(nb.source_count, 3)

    # --- wXbhsf / nested style ---

    def test_parse_notebook_nested_wXbhsf(self):
        """Nested wXbhsf format: [[header_arr], [title, sources], ...]."""
        flags = [False, None, None, None, None,
                 [1700000000, 0],
                 None, None,
                 [1700001000, 0]]
        header = ["", None, "nb-nested-id-002", "🗒️", None, flags]
        title_block = ["Nested Notebook", [["src1"]]]
        raw = [header, title_block]
        nb = parse_notebook(raw)

        self.assertIsNotNone(nb)
        self.assertEqual(nb.id, "nb-nested-id-002")
        self.assertEqual(nb.title, "Nested Notebook")
        self.assertEqual(nb.emoji, "🗒️")
        self.assertFalse(nb.is_pinned)
        self.assertEqual(nb.source_count, 1)
        self.assertEqual(nb.created_at, 1700000000)
        self.assertEqual(nb.updated_at, 1700001000)

    def test_parse_notebook_missing_id_returns_none(self):
        """Returns None when the notebook ID field is absent/falsy."""
        raw = ["Title", [], None]  # nb_id is None
        result = parse_notebook(raw)
        self.assertIsNone(result)

    def test_parse_notebook_empty_input_returns_none(self):
        """Returns None for empty / non-list input."""
        self.assertIsNone(parse_notebook([]))
        self.assertIsNone(parse_notebook(None))  # type: ignore[arg-type]

    def test_parse_notebook_default_emoji(self):
        """Emoji defaults to 📓 when the field is missing or empty string."""
        raw = ["Title", [], "nb-no-emoji", ""]
        nb = parse_notebook(raw)
        self.assertIsNotNone(nb)
        self.assertEqual(nb.emoji, "📓")


class TestParseSource(unittest.TestCase):

    def _make_raw_source(
        self,
        src_id: str = "src-uuid-001",
        name: str = "My Source",
        char_count: int = 5000,
        ts_sec: int = 1700000000,
        type_id: int = 5,
        urls: list = None,
    ) -> list:
        """Return a raw source list matching the documented format."""
        if urls is None:
            urls = ["https://example.com"]
        meta = [None, char_count, [ts_sec, 0], None, type_id, None, 1, urls]
        return [[src_id], name, meta, [None, 2]]

    def test_parse_source_url_type_5(self):
        """type_id 5 maps to source_type 'url'."""
        raw = self._make_raw_source(type_id=5, urls=["https://example.com"])
        src = parse_source(raw)
        self.assertIsNotNone(src)
        self.assertEqual(src.source_type, "url")
        self.assertEqual(src.url, "https://example.com")

    def test_parse_source_url_type_11(self):
        """type_id 11 (Wikipedia URLs) also maps to 'url'."""
        raw = self._make_raw_source(type_id=11, urls=["https://en.wikipedia.org/wiki/Test"])
        src = parse_source(raw)
        self.assertIsNotNone(src)
        self.assertEqual(src.source_type, "url")

    def test_parse_source_text_type_4(self):
        """type_id 4 maps to source_type 'text'."""
        raw = self._make_raw_source(type_id=4, urls=[])
        src = parse_source(raw)
        self.assertIsNotNone(src)
        self.assertEqual(src.source_type, "text")
        self.assertIsNone(src.url)

    def test_parse_source_text_type_8(self):
        """type_id 8 also maps to source_type 'text'."""
        raw = self._make_raw_source(type_id=8, urls=[])
        src = parse_source(raw)
        self.assertIsNotNone(src)
        self.assertEqual(src.source_type, "text")

    def test_parse_source_extracts_id(self):
        """ID is extracted from the nested [[uuid]] structure."""
        raw = self._make_raw_source(src_id="my-source-uuid-9999")
        src = parse_source(raw)
        self.assertIsNotNone(src)
        self.assertEqual(src.id, "my-source-uuid-9999")

    def test_parse_source_char_count(self):
        """char_count field is correctly extracted from meta[1]."""
        raw = self._make_raw_source(char_count=12345)
        src = parse_source(raw)
        self.assertIsNotNone(src)
        self.assertEqual(src.char_count, 12345)

    def test_parse_source_created_at(self):
        """created_at timestamp (seconds) is extracted from meta[2][0]."""
        raw = self._make_raw_source(ts_sec=1699999999)
        src = parse_source(raw)
        self.assertIsNotNone(src)
        self.assertEqual(src.created_at, 1699999999)

    def test_parse_source_unknown_type(self):
        """Unmapped type_id falls back to source_type 'unknown'."""
        raw = self._make_raw_source(type_id=99)
        src = parse_source(raw)
        self.assertIsNotNone(src)
        self.assertEqual(src.source_type, "unknown")

    def test_parse_source_empty_input(self):
        """Returns None for empty or non-list input."""
        self.assertIsNone(parse_source([]))
        self.assertIsNone(parse_source(None))  # type: ignore[arg-type]


class TestParseUser(unittest.TestCase):

    def _make_raw_user(
        self,
        email: str = "user@example.com",
        display_name: str = "Jane Doe",
        avatar_url: str = "https://lh3.googleusercontent.com/avatar",
    ) -> list:
        """Build a raw user list in the documented format."""
        return [
            [[email, 1, [], [display_name, avatar_url]]],
            None,
            1000,
        ]

    def test_parse_user_extracts_fields(self):
        """email, display_name and avatar_url are all correctly extracted."""
        raw = self._make_raw_user(
            email="alice@gmail.com",
            display_name="Alice Smith",
            avatar_url="https://lh3.googleusercontent.com/alice",
        )
        user = parse_user(raw)
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "alice@gmail.com")
        self.assertEqual(user.display_name, "Alice Smith")
        self.assertEqual(user.avatar_url, "https://lh3.googleusercontent.com/alice")

    def test_parse_user_no_avatar(self):
        """avatar_url is None when the profile list has no second element."""
        raw = [
            [["bob@gmail.com", 1, [], ["Bob"]]],
            None,
            1000,
        ]
        user = parse_user(raw)
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "bob@gmail.com")
        self.assertIsNone(user.avatar_url)

    def test_parse_user_empty_input(self):
        """Returns None for empty / non-list input."""
        self.assertIsNone(parse_user([]))
        self.assertIsNone(parse_user(None))  # type: ignore[arg-type]

    def test_parse_user_empty_users_list(self):
        """Returns None when the users sub-list is empty."""
        raw = [[], None, 1000]
        self.assertIsNone(parse_user(raw))


# ===========================================================================
# 4.  Client unit tests (HTTP mocked via unittest.mock.patch)
# ===========================================================================

# Patch targets – must match what client.py imports
_HTTPX_POST = "cli_web.notebooklm.core.client.httpx.post"
_LOAD_COOKIES = "cli_web.notebooklm.core.client.load_cookies"
_FETCH_TOKENS = "cli_web.notebooklm.core.client.fetch_tokens"


def _make_client_with_mock_auth():
    """Return a NotebookLMClient whose auth loading is fully stubbed out."""
    from cli_web.notebooklm.core.client import NotebookLMClient
    client = NotebookLMClient()
    # Inject pre-loaded auth state so _ensure_auth() is a no-op
    client._cookies = {"SID": "test-sid"}
    client._csrf = "test-csrf"
    client._session_id = "test-session-id"
    client._build_label = "test-build-label"
    return client


class TestClientListNotebooks(unittest.TestCase):

    def test_list_notebooks_parses_response(self):
        """list_notebooks() returns Notebook objects parsed from the API response."""
        flags = [False, None, None, None, None,
                 [1700000000, 0], None, None, [1700001000, 0]]
        nb_raw = ["Test Notebook", [], "test-nb-id-1234", "📓", None, flags]
        # wXbhsf result shape expected by list_notebooks: [[nb_raw, ...]]
        api_result = [[nb_raw]]

        body = _make_batchexecute_response("wXbhsf", api_result)
        mock_resp = _make_mock_response(200, body)

        client = _make_client_with_mock_auth()
        with patch(_HTTPX_POST, return_value=mock_resp):
            notebooks = client.list_notebooks()

        self.assertEqual(len(notebooks), 1)
        nb = notebooks[0]
        self.assertIsInstance(nb, Notebook)
        self.assertEqual(nb.id, "test-nb-id-1234")
        self.assertEqual(nb.title, "Test Notebook")

    def test_list_notebooks_empty_result(self):
        """list_notebooks() returns [] when the API returns an empty list."""
        body = _make_batchexecute_response("wXbhsf", [[]])
        mock_resp = _make_mock_response(200, body)

        client = _make_client_with_mock_auth()
        with patch(_HTTPX_POST, return_value=mock_resp):
            notebooks = client.list_notebooks()

        self.assertEqual(notebooks, [])


class TestClientCreateNotebook(unittest.TestCase):

    def test_create_notebook_returns_notebook(self):
        """create_notebook() returns a Notebook with the correct id and title."""
        # CCqFvf response: ["", null, uuid, null, null, [flags...], ...]
        api_result = ["", None, "new-nb-uuid-5678", None, None, []]
        body = _make_batchexecute_response("CCqFvf", api_result)
        mock_resp = _make_mock_response(200, body)

        client = _make_client_with_mock_auth()
        with patch(_HTTPX_POST, return_value=mock_resp):
            nb = client.create_notebook("Brand New Notebook")

        self.assertIsInstance(nb, Notebook)
        self.assertEqual(nb.id, "new-nb-uuid-5678")
        # title is injected by the client (not from response)
        self.assertEqual(nb.title, "Brand New Notebook")

    def test_create_notebook_passes_title_in_params(self):
        """create_notebook() encodes the title inside the f.req POST body."""
        api_result = ["", None, "some-uuid", None, None, []]
        body = _make_batchexecute_response("CCqFvf", api_result)
        mock_resp = _make_mock_response(200, body)

        client = _make_client_with_mock_auth()
        with patch(_HTTPX_POST, return_value=mock_resp) as mock_post:
            client.create_notebook("Param Check")

        self.assertTrue(mock_post.called)
        # httpx.post is called as: httpx.post(url, content=..., headers=..., ...)
        # Retrieve the `content` keyword argument which holds the encoded body.
        posted_content = mock_post.call_args.kwargs.get("content", b"")
        if isinstance(posted_content, bytes):
            posted_content = posted_content.decode("utf-8", errors="replace")
        # The title must appear in the URL-decoded body.
        # urlencode encodes spaces as '+', so use unquote_plus.
        self.assertIn("Param Check", urllib.parse.unquote_plus(posted_content))


class TestClientGetNotebook(unittest.TestCase):

    def test_client_get_notebook_fixed_params(self):
        """get_notebook() calls the API with [notebook_id] (flat rLM1Ne format)."""
        nb_id = "get-nb-target-id"
        flags = [False, None, None, None, None,
                 [1700000000, 0], None, None, [1700001000, 0]]
        # rLM1Ne result: [[title, sources, nb_id, emoji, null, flags]]
        api_result = [["My NB", [], nb_id, "📓", None, flags]]
        body = _make_batchexecute_response("rLM1Ne", api_result)
        mock_resp = _make_mock_response(200, body)

        client = _make_client_with_mock_auth()
        with patch(_HTTPX_POST, return_value=mock_resp) as mock_post:
            nb = client.get_notebook(nb_id)

        # Verify the notebook ID was included in the POST body
        call_kwargs = mock_post.call_args
        posted_body = call_kwargs.kwargs.get("content", b"")
        if isinstance(posted_body, bytes):
            posted_body = posted_body.decode("utf-8", errors="replace")
        decoded_body = urllib.parse.unquote(posted_body)
        self.assertIn(nb_id, decoded_body)
        self.assertIsInstance(nb, Notebook)


class TestClientAddUrlSource(unittest.TestCase):

    def test_client_add_url_source_fixed_params(self):
        """add_url_source() calls VfAZjd with [nb_id, [url]] params."""
        nb_id = "nb-add-src-id"
        url = "https://example.com/article"
        # VfAZjd response: [null, "source_id"]
        api_result = [None, "new-source-id-abc"]
        body = _make_batchexecute_response("VfAZjd", api_result)
        mock_resp = _make_mock_response(200, body)

        client = _make_client_with_mock_auth()
        with patch(_HTTPX_POST, return_value=mock_resp) as mock_post, \
             patch("cli_web.notebooklm.core.client.time.sleep"):  # suppress delay
            src = client.add_url_source(nb_id, url)

        posted_body = mock_post.call_args.kwargs.get("content", b"")
        if isinstance(posted_body, bytes):
            posted_body = posted_body.decode("utf-8", errors="replace")
        decoded_body = urllib.parse.unquote(posted_body)

        # Both nb_id and the url must appear in the encoded params
        self.assertIn(nb_id, decoded_body)
        self.assertIn("example.com", decoded_body)

        self.assertIsInstance(src, Source)
        self.assertEqual(src.id, "new-source-id-abc")
        self.assertEqual(src.source_type, "url")

    def test_add_url_source_rpc_method(self):
        """add_url_source() targets the VfAZjd RPC endpoint."""
        nb_id = "nb-rpc-check"
        url = "https://test.example.org"
        api_result = [None, "src-rpc-id"]
        body = _make_batchexecute_response("VfAZjd", api_result)
        mock_resp = _make_mock_response(200, body)

        client = _make_client_with_mock_auth()
        with patch(_HTTPX_POST, return_value=mock_resp) as mock_post, \
             patch("cli_web.notebooklm.core.client.time.sleep"):
            client.add_url_source(nb_id, url)

        # The request URL must include rpcids=VfAZjd
        call_url = mock_post.call_args.args[0]
        self.assertIn("VfAZjd", call_url)


class TestClient401Retry(unittest.TestCase):

    def test_client_401_triggers_token_refresh_and_retry(self):
        """On HTTP 401, _refresh_tokens is called and the request is retried once."""
        from cli_web.notebooklm.core.client import NotebookLMClient

        flags = [False, None, None, None, None,
                 [1700000000, 0], None, None, [1700001000, 0]]
        success_result = [["Retried NB", [], "retry-nb-id", "📓", None, flags]]
        success_body = _make_batchexecute_response("rLM1Ne", success_result)

        first_resp = _make_mock_response(401, b"Unauthorized")
        second_resp = _make_mock_response(200, success_body)

        client = NotebookLMClient()
        client._cookies = {"SID": "old-sid"}
        # Pre-populate tokens so _ensure_auth does not try to load from disk
        client._csrf = "old-csrf"
        client._session_id = "old-session"
        client._build_label = "old-build"

        with patch(_HTTPX_POST, side_effect=[first_resp, second_resp]) as mock_post, \
             patch(_FETCH_TOKENS, return_value=("new-csrf", "new-sess", "new-build")) as mock_refresh:
            nb = client.get_notebook("retry-nb-id")

        # httpx.post must have been called exactly twice (initial + retry)
        self.assertEqual(mock_post.call_count, 2)
        # fetch_tokens (refresh) must have been called once
        mock_refresh.assert_called_once()
        self.assertEqual(nb.id, "retry-nb-id")

    def test_client_429_raises_rate_limit_error(self):
        """HTTP 429 raises RateLimitError with 'Rate limited' message."""
        mock_resp = _make_mock_response(429, b"Too Many Requests")
        mock_resp.headers = {}

        client = _make_client_with_mock_auth()
        with patch(_HTTPX_POST, return_value=mock_resp):
            with self.assertRaises(RateLimitError) as ctx:
                client.list_notebooks()

        self.assertIn("Rate limited", str(ctx.exception))

    def test_client_500_raises_server_error(self):
        """HTTP 500 raises ServerError with status code."""
        mock_resp = _make_mock_response(500, b"Internal Server Error")

        client = _make_client_with_mock_auth()
        with patch(_HTTPX_POST, return_value=mock_resp):
            with self.assertRaises(ServerError) as ctx:
                client.list_notebooks()

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("500", str(ctx.exception))


# ===========================================================================
# 5.  Exception hierarchy tests
# ===========================================================================

class TestExceptionHierarchy(unittest.TestCase):

    def test_all_exceptions_inherit_from_base(self):
        """All typed exceptions are subclasses of NotebookLMError."""
        for exc_cls in (AuthError, RateLimitError, NetworkError, ServerError, RPCError):
            self.assertTrue(issubclass(exc_cls, NotebookLMError),
                            f"{exc_cls.__name__} does not inherit from NotebookLMError")

    def test_auth_error_has_recoverable(self):
        """AuthError stores the recoverable flag."""
        e = AuthError("expired", recoverable=True)
        self.assertTrue(e.recoverable)
        e2 = AuthError("deleted", recoverable=False)
        self.assertFalse(e2.recoverable)

    def test_rate_limit_error_has_retry_after(self):
        """RateLimitError stores the retry_after value."""
        e = RateLimitError("slow down", retry_after=60.0)
        self.assertEqual(e.retry_after, 60.0)
        e2 = RateLimitError("slow down")
        self.assertIsNone(e2.retry_after)

    def test_server_error_has_status_code(self):
        """ServerError stores the HTTP status code."""
        e = ServerError("bad gateway", status_code=502)
        self.assertEqual(e.status_code, 502)

    def test_error_code_mapping(self):
        """error_code_for returns the correct code string for each exception."""
        from cli_web.notebooklm.core.exceptions import error_code_for

        self.assertEqual(error_code_for(AuthError("x")), "AUTH_EXPIRED")
        self.assertEqual(error_code_for(RateLimitError("x")), "RATE_LIMITED")
        self.assertEqual(error_code_for(ServerError("x")), "SERVER_ERROR")
        self.assertEqual(error_code_for(NetworkError("x")), "NETWORK_ERROR")
        self.assertEqual(error_code_for(RPCError("x")), "RPC_ERROR")
        self.assertEqual(error_code_for(Exception("x")), "UNKNOWN_ERROR")


class TestJsonErrorOutput(unittest.TestCase):

    def test_json_error_format(self):
        """json_error produces valid JSON with error/code/message keys."""
        import json as json_mod
        from cli_web.notebooklm.utils.output import json_error

        result = json_mod.loads(json_error("AUTH_EXPIRED", "Session expired"))
        self.assertTrue(result["error"])
        self.assertEqual(result["code"], "AUTH_EXPIRED")
        self.assertEqual(result["message"], "Session expired")

    def test_json_success_format(self):
        """json_success produces valid JSON with success/data keys."""
        import json as json_mod
        from cli_web.notebooklm.utils.output import json_success

        result = json_mod.loads(json_success({"id": "test"}))
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["id"], "test")


class TestEnvVarAuth(unittest.TestCase):

    def test_env_var_auth_loads_cookies(self):
        """CLI_WEB_NOTEBOOKLM_AUTH_JSON env var provides cookies without file."""
        import os
        from cli_web.notebooklm.core.auth import load_cookies

        env_data = '{"cookies": {"SID": "test-sid", "HSID": "test-hsid"}}'
        with patch.dict(os.environ, {"CLI_WEB_NOTEBOOKLM_AUTH_JSON": env_data}):
            cookies = load_cookies()
        self.assertEqual(cookies["SID"], "test-sid")
        self.assertEqual(cookies["HSID"], "test-hsid")


# ===========================================================================
# 6.  Helpers tests (partial ID, sanitize, persistent context, handle_errors)
# ===========================================================================

class _FakeItem:
    """Tiny object with id and title for resolve_partial_id tests."""
    def __init__(self, id: str, title: str = ""):
        self.id = id
        self.title = title


class TestResolvePartialId(unittest.TestCase):

    def _items(self):
        return [
            _FakeItem("abc123-long-uuid-0001", "First"),
            _FakeItem("abc456-long-uuid-0002", "Second"),
            _FakeItem("xyz789-long-uuid-0003", "Third"),
        ]

    def test_exact_full_id_match(self):
        """Full ID (>=20 chars) matches exactly without prefix search."""
        from cli_web.notebooklm.utils.helpers import resolve_partial_id
        items = self._items()
        result = resolve_partial_id("abc123-long-uuid-0001", items)
        self.assertEqual(result.title, "First")

    def test_unique_prefix_resolves(self):
        """Short unique prefix resolves to single match."""
        from cli_web.notebooklm.utils.helpers import resolve_partial_id
        items = self._items()
        result = resolve_partial_id("xyz", items)
        self.assertEqual(result.title, "Third")

    def test_ambiguous_prefix_raises(self):
        """Ambiguous prefix raises BadParameter."""
        import click
        from cli_web.notebooklm.utils.helpers import resolve_partial_id
        items = self._items()
        with self.assertRaises(click.BadParameter) as ctx:
            resolve_partial_id("abc", items)
        self.assertIn("Ambiguous", str(ctx.exception))

    def test_no_match_raises(self):
        """No matching prefix raises BadParameter."""
        import click
        from cli_web.notebooklm.utils.helpers import resolve_partial_id
        items = self._items()
        with self.assertRaises(click.BadParameter):
            resolve_partial_id("zzz", items)


class TestSanitizeFilename(unittest.TestCase):

    def test_removes_invalid_chars(self):
        from cli_web.notebooklm.utils.helpers import sanitize_filename
        self.assertEqual(sanitize_filename('test/file:name*'), "test_file_name_")

    def test_empty_returns_untitled(self):
        from cli_web.notebooklm.utils.helpers import sanitize_filename
        self.assertEqual(sanitize_filename(""), "untitled")
        self.assertEqual(sanitize_filename("   "), "untitled")

    def test_truncates_long_names(self):
        from cli_web.notebooklm.utils.helpers import sanitize_filename
        long = "a" * 300
        result = sanitize_filename(long)
        self.assertEqual(len(result), 240)


class TestPersistentContext(unittest.TestCase):

    def test_set_and_get_context(self):
        """set_context_value persists and get_context_value retrieves."""
        from cli_web.notebooklm.utils.helpers import (
            get_context_value, set_context_value, clear_context, CONTEXT_FILE,
        )
        import tempfile
        import os

        # Use a temp dir for the test
        with tempfile.TemporaryDirectory() as tmp:
            tmp_file = Path(tmp) / "context.json"
            with patch("cli_web.notebooklm.utils.helpers.CONTEXT_FILE", tmp_file), \
                 patch("cli_web.notebooklm.utils.helpers.AUTH_DIR", Path(tmp)):
                set_context_value("notebook_id", "test-nb-123")
                set_context_value("notebook_title", "My Test Notebook")

                self.assertEqual(get_context_value("notebook_id"), "test-nb-123")
                self.assertEqual(get_context_value("notebook_title"), "My Test Notebook")
                self.assertIsNone(get_context_value("nonexistent"))

                clear_context()
                self.assertIsNone(get_context_value("notebook_id"))


class TestHandleErrors(unittest.TestCase):

    def test_auth_error_exits_1(self):
        """handle_errors catches AuthError and exits with code 1."""
        from cli_web.notebooklm.utils.helpers import handle_errors

        with self.assertRaises(SystemExit) as ctx:
            with handle_errors():
                raise AuthError("session expired")
        self.assertEqual(ctx.exception.code, 1)

    def test_generic_error_exits_2(self):
        """handle_errors catches unknown exceptions and exits with code 2."""
        from cli_web.notebooklm.utils.helpers import handle_errors

        with self.assertRaises(SystemExit) as ctx:
            with handle_errors():
                raise ValueError("unexpected bug")
        self.assertEqual(ctx.exception.code, 2)

    def test_json_mode_outputs_json(self):
        """handle_errors in json_mode outputs structured JSON error."""
        from cli_web.notebooklm.utils.helpers import handle_errors
        import io

        captured = io.StringIO()
        with self.assertRaises(SystemExit):
            import click
            with patch("click.echo", side_effect=lambda msg, **kw: captured.write(msg)):
                with handle_errors(json_mode=True):
                    raise AuthError("expired")

        output = captured.getvalue()
        data = json.loads(output)
        self.assertTrue(data["error"])
        self.assertEqual(data["code"], "AUTH_EXPIRED")


from pathlib import Path

if __name__ == "__main__":
    unittest.main()
