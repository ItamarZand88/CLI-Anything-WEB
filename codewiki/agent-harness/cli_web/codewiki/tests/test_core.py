"""Unit tests for cli-web-codewiki — no network calls."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers: build realistic batchexecute wire responses from Python objects
# ---------------------------------------------------------------------------


def _make_batchexecute(rpc_id: str, inner_obj) -> str:
    """Encode inner_obj as the double-JSON-encoded batchexecute wire format.

    The wire format is:
        )]}'
        <length hint>
        [["wrb.fr", rpc_id, "<json-encoded inner>", null, null, null, "generic"]]

    The decoder iterates chunks → entries and checks entry[0] == "wrb.fr".
    """
    inner_json_str = json.dumps(inner_obj)  # first serialisation (double-encoded)
    entry = ["wrb.fr", rpc_id, inner_json_str, None, None, None, "generic"]
    # One chunk array containing the single entry directly
    outer = json.dumps([entry])
    return ")]}'\n\n100\n" + outer


# Featured repos: [[[slug, null, null, [null, github_url], null, [desc, avatar, stars]]]]
FEATURED_RAW = _make_batchexecute(
    "nm8Fsb",
    [
        [
            [
                "test-org/test-repo",
                None,
                None,
                [None, "https://github.com/test-org/test-repo"],
                None,
                ["A test repository", "https://avatars.githubusercontent.com/u/123?v=4", 42000],
            ]
        ]
    ],
)

# Search repos: [[[slug, null, rank, [null, github_url], [ts_sec, ts_ns], [desc, avatar, stars, slug]]]]
SEARCH_RAW = _make_batchexecute(
    "vyWDAf",
    [
        [
            [
                "found-org/found-repo",
                None,
                3,
                [None, "https://github.com/found-org/found-repo"],
                [1773125120, 745316000],
                [
                    "Found repo description",
                    "https://avatars.githubusercontent.com/u/456?v=4",
                    5000,
                    "found-org/found-repo",
                ],
            ]
        ]
    ],
)

# Wiki page: [[[slug, commit], [[title, level, desc, null, content], ...], null, null, [ts_sec, ts_ns]], [[null, url], has_wiki, n]]
WIKI_RAW = _make_batchexecute(
    "VSX6ub",
    [
        [
            ["test-org/test-repo", "abc123"],
            [
                [
                    "/test-org/test-repo Overview",
                    1,
                    "Overview of test repo",
                    None,
                    "This is the overview content.",
                ],
                ["/Section A", 2, "Section A description", None, "Section A content."],
            ],
            None,
            None,
            [1773125120, 745316000],
        ],
        [[None, "https://github.com/test-org/test-repo"], True, 3],
    ],
)

# Chat response: ["answer text"]
CHAT_RAW = _make_batchexecute("EgIxfe", ["The answer is that this repo uses React for rendering."])

# Error entry (er tag) — entry[0] == "er" triggers RPCError in the decoder
ERROR_RAW = ")]}'\n\n100\n" + json.dumps(
    [["er", {"code": 403, "message": "Forbidden"}, None, None, None, "generic"]]
)

# Empty/null result
EMPTY_RAW = _make_batchexecute("nm8Fsb", None)


# ===========================================================================
# 1. RPC Encoder tests
# ===========================================================================


class TestRPCEncoder:
    def test_build_url_contains_rpcid(self):
        from cli_web.codewiki.core.rpc.encoder import build_url

        url = build_url("nm8Fsb")
        assert "rpcids=nm8Fsb" in url

    def test_build_url_contains_base(self):
        from cli_web.codewiki.core.rpc.encoder import build_url
        from cli_web.codewiki.core.rpc.types import BATCHEXECUTE_URL

        url = build_url("nm8Fsb")
        assert url.startswith(BATCHEXECUTE_URL)

    def test_encode_request_featured_empty_params(self):
        from cli_web.codewiki.core.rpc.encoder import encode_request

        body = encode_request("nm8Fsb", [])
        # Must be form-encoded and contain f.req
        assert "f.req=" in body
        # Decode the f.req value and check structure
        from urllib.parse import parse_qs

        parsed = parse_qs(body)
        freq = json.loads(parsed["f.req"][0])
        # [[["nm8Fsb", "[]", null, "generic"]]]
        assert freq[0][0][0] == "nm8Fsb"
        assert freq[0][0][3] == "generic"
        inner_params = json.loads(freq[0][0][1])
        assert inner_params == []

    def test_encode_request_search_with_query_params(self):
        from urllib.parse import parse_qs

        from cli_web.codewiki.core.rpc.encoder import encode_request

        body = encode_request("vyWDAf", ["react", 25, "react", 0])
        parsed = parse_qs(body)
        freq = json.loads(parsed["f.req"][0])
        assert freq[0][0][0] == "vyWDAf"
        inner_params = json.loads(freq[0][0][1])
        assert inner_params == ["react", 25, "react", 0]

    def test_encode_request_produces_form_encoded(self):
        from cli_web.codewiki.core.rpc.encoder import encode_request

        body = encode_request("EgIxfe", [["question"]])
        # Form-encoded: no raw brackets allowed
        assert "f.req=" in body
        assert "&" not in body.split("f.req=")[0]  # no leading param


# ===========================================================================
# 2. RPC Decoder tests
# ===========================================================================


class TestRPCDecoder:
    def test_strip_prefix_removes_xssi(self):
        from cli_web.codewiki.core.rpc.decoder import _strip_prefix

        raw = ")]}'\nhello"
        result = _strip_prefix(raw)
        assert result == "hello"

    def test_strip_prefix_handles_bytes(self):
        from cli_web.codewiki.core.rpc.decoder import _strip_prefix

        raw = b")]}'\ndata"
        result = _strip_prefix(raw)
        assert result == "data"

    def test_strip_prefix_no_prefix_unchanged(self):
        from cli_web.codewiki.core.rpc.decoder import _strip_prefix

        raw = "plain text"
        assert _strip_prefix(raw) == "plain text"

    def test_decode_featured_response(self):
        from cli_web.codewiki.core.rpc.decoder import decode_response

        result = decode_response(FEATURED_RAW, "nm8Fsb")
        assert result is not None
        # Should be a list with one inner list of repos
        assert isinstance(result, list)
        repos = result[0]
        assert isinstance(repos, list)
        assert len(repos) == 1
        assert repos[0][0] == "test-org/test-repo"

    def test_decode_returns_none_for_empty(self):
        from cli_web.codewiki.core.rpc.decoder import decode_response

        result = decode_response(EMPTY_RAW, "nm8Fsb")
        assert result is None

    def test_decode_rpc_error_raises(self):
        from cli_web.codewiki.core.exceptions import RPCError
        from cli_web.codewiki.core.rpc.decoder import decode_response

        with pytest.raises(RPCError):
            decode_response(ERROR_RAW, "nm8Fsb")

    def test_decode_search_response(self):
        from cli_web.codewiki.core.rpc.decoder import decode_response

        result = decode_response(SEARCH_RAW, "vyWDAf")
        assert result is not None
        repos = result[0]
        assert repos[0][0] == "found-org/found-repo"

    def test_decode_chat_response(self):
        from cli_web.codewiki.core.rpc.decoder import decode_response

        result = decode_response(CHAT_RAW, "EgIxfe")
        assert isinstance(result, list)
        assert result[0] == "The answer is that this repo uses React for rendering."

    def test_decode_wrong_rpc_id_returns_none(self):
        from cli_web.codewiki.core.rpc.decoder import decode_response

        # Asking for a different RPC ID than what's in the response
        result = decode_response(FEATURED_RAW, "xxxxxx")
        assert result is None


# ===========================================================================
# 3. Client tests (mocked httpx)
# ===========================================================================


def _make_mock_response(body: str, status_code: int = 200, headers: dict | None = None):
    """Build a MagicMock that mimics httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = body.encode("utf-8")
    resp.text = body
    resp.headers = headers or {}
    return resp


class TestCodeWikiClientFeaturedRepos:
    def test_featured_repos_parses_correctly(self):
        from cli_web.codewiki.core.client import CodeWikiClient

        client = CodeWikiClient()
        with patch.object(client._http, "post", return_value=_make_mock_response(FEATURED_RAW)):
            repos = client.featured_repos()
        assert len(repos) == 1
        repo = repos[0]
        assert repo.slug == "test-org/test-repo"
        assert repo.github_url == "https://github.com/test-org/test-repo"
        assert repo.description == "A test repository"
        assert repo.stars == 42000
        assert repo.org == "test-org"
        assert repo.name == "test-repo"
        client.close()

    def test_featured_repos_empty_returns_list(self):
        from cli_web.codewiki.core.client import CodeWikiClient

        client = CodeWikiClient()
        with patch.object(client._http, "post", return_value=_make_mock_response(EMPTY_RAW)):
            repos = client.featured_repos()
        assert repos == []
        client.close()


class TestCodeWikiClientSearchRepos:
    def test_search_repos_parses_correctly(self):
        from cli_web.codewiki.core.client import CodeWikiClient

        client = CodeWikiClient()
        with patch.object(client._http, "post", return_value=_make_mock_response(SEARCH_RAW)):
            repos = client.search_repos("found")
        assert len(repos) == 1
        repo = repos[0]
        assert repo.slug == "found-org/found-repo"
        assert repo.github_url == "https://github.com/found-org/found-repo"
        assert repo.description == "Found repo description"
        assert repo.stars == 5000
        assert repo.updated_at is not None
        client.close()

    def test_search_repos_passes_query_to_rpc(self):
        from urllib.parse import parse_qs

        from cli_web.codewiki.core.client import CodeWikiClient

        client = CodeWikiClient()
        mock_post = MagicMock(return_value=_make_mock_response(SEARCH_RAW))
        with patch.object(client._http, "post", mock_post):
            client.search_repos("react", limit=10, offset=5)
        call_kwargs = mock_post.call_args
        body_bytes = (
            call_kwargs[1]["content"]
            if "content" in call_kwargs[1]
            else call_kwargs.kwargs["content"]
        )
        body = body_bytes.decode("utf-8")
        parsed = parse_qs(body)
        freq = json.loads(parsed["f.req"][0])
        inner_params = json.loads(freq[0][0][1])
        assert inner_params[0] == "react"
        assert inner_params[1] == 10
        assert inner_params[3] == 5
        client.close()


class TestCodeWikiClientWikiPage:
    def test_wiki_page_parses_sections(self):
        from cli_web.codewiki.core.client import CodeWikiClient

        client = CodeWikiClient()
        with patch.object(client._http, "post", return_value=_make_mock_response(WIKI_RAW)):
            page = client.get_wiki("test-org/test-repo")
        assert page.repo.slug == "test-org/test-repo"
        assert page.repo.commit_hash == "abc123"
        assert len(page.sections) == 2
        # First section: level 1, title contains "Overview"
        s0 = page.sections[0]
        assert s0.level == 1
        assert "Overview" in s0.title
        assert s0.content == "This is the overview content."
        # Second section: level 2
        s1 = page.sections[1]
        assert s1.level == 2
        assert "Section A" in s1.title
        assert s1.content == "Section A content."
        assert page.has_wiki is True
        client.close()

    def test_wiki_page_not_found_raises(self):
        from cli_web.codewiki.core.client import CodeWikiClient
        from cli_web.codewiki.core.exceptions import NotFoundError

        client = CodeWikiClient()
        with patch.object(client._http, "post", return_value=_make_mock_response(EMPTY_RAW)):
            with pytest.raises(NotFoundError):
                client.get_wiki("missing/repo")
        client.close()


class TestCodeWikiClientChat:
    def test_chat_returns_answer(self):
        from cli_web.codewiki.core.client import CodeWikiClient

        client = CodeWikiClient()
        with patch.object(client._http, "post", return_value=_make_mock_response(CHAT_RAW)):
            resp = client.chat("What does this repo do?", "test-org/test-repo")
        assert isinstance(resp.answer, str)
        assert "React" in resp.answer
        assert resp.repo_slug == "test-org/test-repo"
        client.close()

    def test_chat_with_history(self):
        from urllib.parse import parse_qs

        from cli_web.codewiki.core.client import CodeWikiClient

        client = CodeWikiClient()
        mock_post = MagicMock(return_value=_make_mock_response(CHAT_RAW))
        history = [("previous question", "user"), ("previous answer", "model")]
        with patch.object(client._http, "post", mock_post):
            client.chat("follow-up", "test-org/test-repo", history=history)
        call_kwargs = mock_post.call_args
        body_bytes = (
            call_kwargs[1]["content"]
            if "content" in call_kwargs[1]
            else call_kwargs.kwargs["content"]
        )
        body = body_bytes.decode("utf-8")
        parsed = parse_qs(body)
        freq = json.loads(parsed["f.req"][0])
        inner_params = json.loads(freq[0][0][1])
        # messages list: history + current question
        messages = inner_params[0]
        assert len(messages) == 3  # 2 history + 1 current
        assert messages[-1] == ["follow-up", "user"]
        client.close()


# ===========================================================================
# 4. HTTP error → exception mapping
# ===========================================================================


class TestClientHTTPErrors:
    def test_client_404_raises_not_found(self):
        from cli_web.codewiki.core.client import CodeWikiClient
        from cli_web.codewiki.core.exceptions import NotFoundError

        client = CodeWikiClient()
        with patch.object(
            client._http, "post", return_value=_make_mock_response("", status_code=404)
        ):
            with pytest.raises(NotFoundError):
                client.featured_repos()
        client.close()

    def test_client_429_raises_rate_limit(self):
        from cli_web.codewiki.core.client import CodeWikiClient
        from cli_web.codewiki.core.exceptions import RateLimitError

        client = CodeWikiClient()
        resp = _make_mock_response("", status_code=429, headers={"Retry-After": "30"})
        with patch.object(client._http, "post", return_value=resp):
            with pytest.raises(RateLimitError) as exc_info:
                client.featured_repos()
        assert exc_info.value.retry_after == 30.0
        client.close()

    def test_client_429_no_retry_after_header(self):
        from cli_web.codewiki.core.client import CodeWikiClient
        from cli_web.codewiki.core.exceptions import RateLimitError

        client = CodeWikiClient()
        with patch.object(
            client._http, "post", return_value=_make_mock_response("", status_code=429)
        ):
            with pytest.raises(RateLimitError) as exc_info:
                client.featured_repos()
        assert exc_info.value.retry_after is None
        client.close()

    def test_client_500_raises_server_error(self):
        from cli_web.codewiki.core.client import CodeWikiClient
        from cli_web.codewiki.core.exceptions import ServerError

        client = CodeWikiClient()
        with patch.object(
            client._http, "post", return_value=_make_mock_response("oops", status_code=500)
        ):
            with pytest.raises(ServerError) as exc_info:
                client.featured_repos()
        assert exc_info.value.status_code == 500
        client.close()

    def test_client_503_raises_server_error(self):
        from cli_web.codewiki.core.client import CodeWikiClient
        from cli_web.codewiki.core.exceptions import ServerError

        client = CodeWikiClient()
        with patch.object(
            client._http, "post", return_value=_make_mock_response("", status_code=503)
        ):
            with pytest.raises(ServerError) as exc_info:
                client.search_repos("anything")
        assert exc_info.value.status_code == 503
        client.close()

    def test_client_network_error_connect(self):
        import httpx
        from cli_web.codewiki.core.client import CodeWikiClient
        from cli_web.codewiki.core.exceptions import NetworkError

        client = CodeWikiClient()
        with patch.object(client._http, "post", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(NetworkError):
                client.featured_repos()
        client.close()

    def test_client_network_error_timeout(self):
        import httpx
        from cli_web.codewiki.core.client import CodeWikiClient
        from cli_web.codewiki.core.exceptions import NetworkError

        client = CodeWikiClient()
        with patch.object(client._http, "post", side_effect=httpx.TimeoutException("timed out")):
            with pytest.raises(NetworkError):
                client.featured_repos()
        client.close()


# ===========================================================================
# 5. Exception hierarchy tests
# ===========================================================================


class TestExceptionHierarchy:
    def test_all_errors_are_codewiki_errors(self):
        from cli_web.codewiki.core.exceptions import (
            AuthError,
            CodeWikiError,
            NetworkError,
            NotFoundError,
            RateLimitError,
            RPCError,
            ServerError,
        )

        for cls in [AuthError, RateLimitError, NetworkError, ServerError, NotFoundError, RPCError]:
            exc = cls("test message") if cls not in (ServerError,) else cls("test", 500)
            assert isinstance(exc, CodeWikiError)

    def test_error_code_mapping_auth(self):
        from cli_web.codewiki.core.exceptions import AuthError, error_code_for

        assert error_code_for(AuthError("expired")) == "AUTH_EXPIRED"

    def test_error_code_mapping_rate_limit(self):
        from cli_web.codewiki.core.exceptions import RateLimitError, error_code_for

        assert error_code_for(RateLimitError("slow down")) == "RATE_LIMITED"

    def test_error_code_mapping_not_found(self):
        from cli_web.codewiki.core.exceptions import NotFoundError, error_code_for

        assert error_code_for(NotFoundError("missing")) == "NOT_FOUND"

    def test_error_code_mapping_server_error(self):
        from cli_web.codewiki.core.exceptions import ServerError, error_code_for

        assert error_code_for(ServerError("oops", 500)) == "SERVER_ERROR"

    def test_error_code_mapping_network(self):
        from cli_web.codewiki.core.exceptions import NetworkError, error_code_for

        assert error_code_for(NetworkError("down")) == "NETWORK_ERROR"

    def test_error_code_mapping_rpc(self):
        from cli_web.codewiki.core.exceptions import RPCError, error_code_for

        assert error_code_for(RPCError("bad rpc")) == "RPC_ERROR"

    def test_error_code_mapping_unknown(self):
        from cli_web.codewiki.core.exceptions import error_code_for

        assert error_code_for(ValueError("unexpected")) == "INTERNAL_ERROR"

    def test_auth_error_recoverable_default_true(self):
        from cli_web.codewiki.core.exceptions import AuthError

        exc = AuthError("session expired")
        assert exc.recoverable is True

    def test_auth_error_recoverable_can_be_false(self):
        from cli_web.codewiki.core.exceptions import AuthError

        exc = AuthError("hard fail", recoverable=False)
        assert exc.recoverable is False

    def test_rate_limit_error_stores_retry_after(self):
        from cli_web.codewiki.core.exceptions import RateLimitError

        exc = RateLimitError("slow down", retry_after=60.0)
        assert exc.retry_after == 60.0

    def test_server_error_stores_status_code(self):
        from cli_web.codewiki.core.exceptions import ServerError

        exc = ServerError("boom", status_code=503)
        assert exc.status_code == 503

    def test_rpc_error_stores_code(self):
        from cli_web.codewiki.core.exceptions import RPCError

        exc = RPCError("protocol err", code=403)
        assert exc.code == 403


# ===========================================================================
# 6. handle_errors context manager tests
# ===========================================================================


class TestHandleErrors:
    def test_handle_errors_codewiki_error_exits_1(self):
        from cli_web.codewiki.core.exceptions import NotFoundError
        from cli_web.codewiki.utils.helpers import handle_errors

        with pytest.raises(SystemExit) as exc_info:
            with handle_errors(json_mode=False):
                raise NotFoundError("not found")
        assert exc_info.value.code == 1

    def test_handle_errors_codewiki_error_json_output(self, capsys):
        from cli_web.codewiki.core.exceptions import RateLimitError
        from cli_web.codewiki.utils.helpers import handle_errors

        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise RateLimitError("too many requests")
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["error"] is True
        assert data["code"] == "RATE_LIMITED"
        assert "too many requests" in data["message"]

    def test_handle_errors_unexpected_exits_2(self):
        from cli_web.codewiki.utils.helpers import handle_errors

        with pytest.raises(SystemExit) as exc_info:
            with handle_errors(json_mode=False):
                raise RuntimeError("something unexpected")
        assert exc_info.value.code == 2

    def test_handle_errors_unexpected_json_output(self, capsys):
        from cli_web.codewiki.utils.helpers import handle_errors

        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise RuntimeError("boom")
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["error"] is True
        assert data["code"] == "INTERNAL_ERROR"

    def test_handle_errors_keyboard_interrupt_exits_130(self):
        from cli_web.codewiki.utils.helpers import handle_errors

        with pytest.raises(SystemExit) as exc_info:
            with handle_errors(json_mode=False):
                raise KeyboardInterrupt
        assert exc_info.value.code == 130

    def test_handle_errors_no_error_yields(self):
        from cli_web.codewiki.utils.helpers import handle_errors

        result = []
        with handle_errors(json_mode=False):
            result.append(42)
        assert result == [42]

    def test_handle_errors_usage_error_propagates(self):
        import click
        from cli_web.codewiki.utils.helpers import handle_errors

        with pytest.raises(click.UsageError):
            with handle_errors(json_mode=False):
                raise click.UsageError("bad args")


# ===========================================================================
# 7. Models tests
# ===========================================================================


class TestModels:
    def test_repository_org_and_name_properties(self):
        from cli_web.codewiki.core.models import Repository

        repo = Repository(slug="my-org/my-repo", github_url="https://github.com/my-org/my-repo")
        assert repo.org == "my-org"
        assert repo.name == "my-repo"

    def test_repository_to_dict_keys(self):
        from cli_web.codewiki.core.models import Repository

        repo = Repository(
            slug="a/b",
            github_url="https://github.com/a/b",
            description="desc",
            stars=100,
        )
        d = repo.to_dict()
        assert set(d.keys()) == {
            "slug",
            "github_url",
            "description",
            "avatar_url",
            "stars",
            "commit_hash",
            "updated_at",
        }
        assert d["stars"] == 100

    def test_wiki_section_to_dict(self):
        from cli_web.codewiki.core.models import WikiSection

        sec = WikiSection(title="Overview", level=1, content="some text")
        d = sec.to_dict()
        assert d["title"] == "Overview"
        assert d["level"] == 1
        assert d["content"] == "some text"

    def test_wiki_page_to_dict_includes_section_count(self):
        from cli_web.codewiki.core.models import Repository, WikiPage, WikiSection

        repo = Repository(slug="a/b", github_url="https://github.com/a/b")
        sections = [WikiSection(title=f"S{i}", level=1) for i in range(3)]
        page = WikiPage(repo=repo, sections=sections, has_wiki=True)
        d = page.to_dict()
        assert d["section_count"] == 3
        assert d["has_wiki"] is True

    def test_chat_response_to_dict(self):
        from cli_web.codewiki.core.models import ChatResponse

        resp = ChatResponse(answer="42", repo_slug="a/b")
        d = resp.to_dict()
        assert d["answer"] == "42"
        assert d["repo"] == "a/b"


# ===========================================================================
# 8. RPC types constants
# ===========================================================================


class TestRPCTypes:
    def test_rpc_method_ids(self):
        from cli_web.codewiki.core.rpc.types import RPCMethod

        assert RPCMethod.FEATURED_REPOS == "nm8Fsb"
        assert RPCMethod.WIKI_PAGE == "VSX6ub"
        assert RPCMethod.SEARCH_REPOS == "vyWDAf"
        assert RPCMethod.CHAT == "EgIxfe"

    def test_batchexecute_url_is_https(self):
        from cli_web.codewiki.core.rpc.types import BATCHEXECUTE_URL

        assert BATCHEXECUTE_URL.startswith("https://")
        assert "batchexecute" in BATCHEXECUTE_URL
