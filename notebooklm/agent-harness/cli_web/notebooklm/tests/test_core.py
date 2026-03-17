"""Unit tests for cli-web-notebooklm core modules."""

import json
import pytest

from cli_web.notebooklm.core.rpc.encoder import encode_request, build_query_params
from cli_web.notebooklm.core.rpc.decoder import decode_response, extract_rpc_data, parse_rpc_result
from cli_web.notebooklm.core.auth import cookies_to_header, check_required_cookies, extract_tokens_from_html
from cli_web.notebooklm.core.models import parse_notebook, parse_source, parse_artifact, parse_timestamp


# ── RPC Encoder Tests ──────────────────────────────────────────────


class TestEncoder:
    def test_encode_request_basic(self):
        body = encode_request("wXbhsf", "[null,1]", "test_token_123")
        assert "wXbhsf" in body
        assert "test_token_123" in body
        assert "f.req=" in body

    def test_encode_request_with_list(self):
        body = encode_request("rLM1Ne", [None, 1, [2]], "token")
        assert "rLM1Ne" in body
        assert "token" in body

    def test_build_query_params(self):
        params = build_query_params("wXbhsf", "/", "bl_123", "fsid_456", "en", 100000)
        assert params["rpcids"] == "wXbhsf"
        assert params["source-path"] == "/"
        assert params["bl"] == "bl_123"
        assert params["f.sid"] == "fsid_456"
        assert params["hl"] == "en"
        assert params["_reqid"] == "100000"
        assert params["rt"] == "c"


# ── RPC Decoder Tests ──────────────────────────────────────────────


class TestDecoder:
    def test_decode_simple_response(self):
        prefix = ")]}'"
        raw = prefix + '\n\n26\n[["wrb.fr","test","[1,2,3]",null,null,null,"generic"]]'
        envs = decode_response(raw)
        assert len(envs) >= 1
        assert envs[0][0][0] == "wrb.fr"
        assert envs[0][0][1] == "test"

    def test_decode_multibyte_response(self):
        """Hebrew chars cause byte/char mismatch — decoder must handle this."""
        inner = json.dumps({"title": "שלום"})
        envelope = json.dumps([["wrb.fr", "test", inner, None, None, None, "generic"]])
        byte_len = len(envelope.encode("utf-8"))
        prefix = ")]}'"
        raw = prefix + "\n\n" + str(byte_len) + "\n" + envelope
        envs = decode_response(raw)
        assert len(envs) >= 1

    def test_decode_multiple_chunks(self):
        chunk1 = json.dumps([["wrb.fr", "A", '"data1"', None]])
        chunk2 = json.dumps([["di", 67]])
        prefix = ")]}'"
        raw = prefix + "\n" + str(len(chunk1.encode('utf-8'))) + "\n" + chunk1 + "\n" + str(len(chunk2.encode('utf-8'))) + "\n" + chunk2
        envs = decode_response(raw)
        assert len(envs) == 2

    def test_extract_rpc_data(self):
        envs = [[["wrb.fr", "myRpc", '{"key":"val"}', None, None, None, "generic"]]]
        data = extract_rpc_data(envs, "myRpc")
        assert data == '{"key":"val"}'

    def test_extract_rpc_data_not_found(self):
        envs = [[["wrb.fr", "other", '{}', None]]]
        assert extract_rpc_data(envs, "missing") is None

    def test_parse_rpc_result(self):
        envs = [[["wrb.fr", "testRpc", '[[1,2],[3,4]]', None, None, None, "generic"]]]
        result = parse_rpc_result(envs, "testRpc")
        assert result == [[1, 2], [3, 4]]


# ── Auth Tests ─────────────────────────────────────────────────────


class TestAuth:
    def test_cookies_to_header_filters_domain(self):
        cookies = [
            {"name": "SID", "value": "abc", "domain": ".google.com"},
            {"name": "OTHER", "value": "xyz", "domain": "mail.google.com"},
        ]
        header = cookies_to_header(cookies, target_domain="notebooklm.google.com")
        assert "SID=abc" in header
        assert "OTHER=xyz" not in header

    def test_cookies_to_header_deduplicates(self):
        cookies = [
            {"name": "OSID", "value": "broad", "domain": ".google.com"},
            {"name": "OSID", "value": "narrow", "domain": ".notebooklm.google.com"},
        ]
        header = cookies_to_header(cookies, target_domain="notebooklm.google.com")
        assert "OSID=broad" in header
        assert "OSID=narrow" not in header

    def test_check_required_cookies_all_present(self):
        cookies = [
            {"name": "SID"}, {"name": "HSID"}, {"name": "SSID"}, {"name": "OSID"},
        ]
        ok, missing = check_required_cookies(cookies)
        assert ok is True
        assert missing == []

    def test_check_required_cookies_missing(self):
        cookies = [{"name": "SID"}]
        ok, missing = check_required_cookies(cookies)
        assert ok is False
        assert "HSID" in missing

    def test_extract_tokens_from_html(self):
        html = '''<script>window.WIZ_global_data = {"SNlM0e":"token123","cfb2h":"bl_val","FdrFJe":"fsid_val"};</script>'''
        tokens = extract_tokens_from_html(html)
        assert tokens["at"] == "token123"
        assert tokens["bl"] == "bl_val"
        assert tokens["fsid"] == "fsid_val"

    def test_extract_tokens_missing(self):
        tokens = extract_tokens_from_html("<html></html>")
        assert tokens["at"] is None


# ── Models Tests ───────────────────────────────────────────────────


class TestModels:
    def test_parse_timestamp(self):
        ts = parse_timestamp([1700000000, 0])
        assert ts is not None
        assert "2023" in ts

    def test_parse_timestamp_none(self):
        assert parse_timestamp(None) is None
        assert parse_timestamp([]) is None

    def test_parse_notebook(self):
        raw = [
            "Test Notebook",
            [
                [["src-1"], "Source 1", [None, 100, [1700000000, 0], None, 4, None, 1], [None, 2]],
            ],
            "nb-uuid-123",
            "📝",
            None,
            [1, False, True, None, None, [1700000000, 0], 1, False, [1699000000, 0]],
        ]
        nb = parse_notebook(raw)
        assert nb["id"] == "nb-uuid-123"
        assert nb["title"] == "Test Notebook"
        assert nb["emoji"] == "📝"
        assert nb["source_count"] == 1

    def test_parse_source(self):
        raw = [
            ["src-uuid-1"],
            "My Source",
            [None, 5000, [1700000000, 0], None, 5, None, 2, ["https://example.com"]],
            [None, 2],
        ]
        src = parse_source(raw)
        assert src["id"] == "src-uuid-1"
        assert src["title"] == "My Source"
        assert src["word_count"] == 5000
        assert src["type"] == "Web URL"
        assert src["url"] == "https://example.com"

    def test_parse_source_empty(self):
        src = parse_source([])
        assert src == {}

    def test_parse_artifact(self):
        raw = [
            "art-uuid-1",
            "Audio Overview",
            1,  # audio type
            [[["src-1"]]],
            3,  # status
        ]
        art = parse_artifact(raw)
        assert art["id"] == "art-uuid-1"
        assert art["title"] == "Audio Overview"
        assert art["type"] == "Audio Overview"
