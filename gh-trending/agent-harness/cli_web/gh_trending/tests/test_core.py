"""Unit tests for cli-web-github core modules (mocked HTTP, no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from cli_web.gh_trending.core.client import GitHubClient
from cli_web.gh_trending.core.exceptions import (
    AppError,
    AuthError,
    NetworkError,
    ParseError,
    RateLimitError,
    ServerError,
)
from cli_web.gh_trending.core.models import _parse_int


# ─── Fixtures ────────────────────────────────────────────────────────────────

REPO_ARTICLE_HTML = """
<html><body>
<article class="Box-row">
  <div class="float-right d-flex">
    <a href="/login?return_to=%2Flangchain-ai%2Fopen-swe" aria-label="You must be signed in to star a repository">Star</a>
  </div>
  <h2 class="h3 lh-condensed">
    <a href="/langchain-ai/open-swe">langchain-ai / open-swe</a>
  </h2>
  <p>An Open-Source Asynchronous Coding Agent</p>
  <div class="f6 color-fg-muted mt-2">
    <span itemprop="programmingLanguage">Python</span>
    <a class="Link--muted d-inline-block mr-3" href="/langchain-ai/open-swe/stargazers">
      <svg></svg> 6,777
    </a>
    <a class="Link--muted d-inline-block mr-3" href="/langchain-ai/open-swe/forks">
      <svg></svg> 854
    </a>
    <span class="d-inline-block float-sm-right">
      <svg></svg> 955 stars today
    </span>
    <a class="Link--muted" href="/bracesproul"><img alt="@bracesproul" class="avatar" /></a>
    <a class="Link--muted" href="/aran-yogesh"><img alt="@aran-yogesh" class="avatar" /></a>
  </div>
</article>
</body></html>
"""

DEVELOPER_ARTICLE_HTML = """
<html><body>
<article class="Box-row d-flex" id="pa-njbrake">
  <a href="#pa-njbrake" class="Link color-fg-muted f6">1</a>
  <div class="tmp-mx-3">
    <a href="/njbrake"><img class="rounded avatar-user" src="https://avatars.githubusercontent.com/u/33383515?s=96&v=4" width="48" height="48" alt="@njbrake"></a>
  </div>
  <div class="d-sm-flex flex-auto">
    <div class="col-sm-8 d-md-flex">
      <div class="col-md-6">
        <h1 class="h3 lh-condensed">
          <a href="/njbrake">Nathan Brake</a>
        </h1>
        <p class="f4 text-normal mb-1">
          <a href="/njbrake" class="Link--secondary Link">njbrake</a>
        </p>
      </div>
      <div class="col-md-6">
        <div class="mt-2">
          <article>
            <div class="f6 color-fg-muted text-uppercase mb-1">Popular repo</div>
            <h1 class="h4 lh-condensed">
              <a href="/njbrake/agent-of-empires">agent-of-empires</a>
            </h1>
            <p>A strategy game powered by AI agents</p>
          </article>
        </div>
      </div>
    </div>
  </div>
</article>
</body></html>
"""

EMPTY_HTML = """
<html><body>
<div class="container">No trending repos.</div>
</body></html>
"""


# ─── _parse_int tests ─────────────────────────────────────────────────────────

class TestParseInt:
    def test_comma_separated(self):
        assert _parse_int("4,859") == 4859

    def test_stars_today_text(self):
        assert _parse_int("1,394 stars today") == 1394

    def test_empty(self):
        assert _parse_int("") == 0

    def test_zero(self):
        assert _parse_int("0") == 0

    def test_plain_number(self):
        assert _parse_int("100") == 100


# ─── HTML parser tests ────────────────────────────────────────────────────────

class TestParseReposHTML:
    def test_parses_repo_fields(self):
        client = GitHubClient()
        repos = client._parse_repos(REPO_ARTICLE_HTML)
        assert len(repos) >= 1
        repo = repos[0]
        assert repo.full_name == "langchain-ai/open-swe"
        assert repo.owner == "langchain-ai"
        assert repo.name == "open-swe"
        assert repo.language == "Python"
        assert repo.stars == 6777
        assert repo.forks == 854
        assert repo.stars_today == 955
        assert repo.rank == 1
        assert repo.url == "https://github.com/langchain-ai/open-swe"
        assert "bracesproul" in repo.contributors

    def test_description_parsed(self):
        client = GitHubClient()
        repos = client._parse_repos(REPO_ARTICLE_HTML)
        assert "Asynchronous Coding Agent" in repos[0].description

    def test_empty_page_raises_parse_error(self):
        client = GitHubClient()
        with pytest.raises(ParseError):
            client._parse_repos(EMPTY_HTML)


class TestParseDevelopersHTML:
    def test_parses_developer_fields(self):
        client = GitHubClient()
        devs = client._parse_developers(DEVELOPER_ARTICLE_HTML)
        assert len(devs) >= 1
        dev = devs[0]
        assert dev.login == "njbrake"
        assert dev.name == "Nathan Brake"
        assert dev.rank == 1
        assert dev.profile_url == "https://github.com/njbrake"
        assert dev.popular_repo == "njbrake/agent-of-empires"

    def test_empty_page_raises_parse_error(self):
        client = GitHubClient()
        with pytest.raises(ParseError):
            client._parse_developers(EMPTY_HTML)


# ─── HTTP client error handling tests ────────────────────────────────────────

class TestClientHTTPErrors:
    def _mock_response(self, status_code: int, headers: dict | None = None, text: str = ""):
        resp = MagicMock()
        resp.status_code = status_code
        resp.headers = headers or {}
        resp.text = text
        return resp

    def test_rate_limit_raises(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = self._mock_response(
                429, headers={"retry-after": "30"}
            )
            client = GitHubClient()
            with pytest.raises(RateLimitError) as exc_info:
                client._get("https://github.com/trending")
            assert exc_info.value.retry_after == 30

    def test_server_error_raises(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = self._mock_response(503)
            client = GitHubClient()
            with pytest.raises(ServerError):
                client._get("https://github.com/trending")

    def test_network_error_raises(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            client = GitHubClient()
            with pytest.raises(NetworkError):
                client._get("https://github.com/trending")

    def test_timeout_raises_network_error(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Timed out")
            client = GitHubClient()
            with pytest.raises(NetworkError):
                client._get("https://github.com/trending")


# ─── Exception serialization tests ───────────────────────────────────────────

class TestExceptionsToDicts:
    def test_app_error_to_dict(self):
        exc = AppError("something broke", "TEST_ERROR")
        d = exc.to_dict()
        assert d["error"] is True
        assert d["code"] == "TEST_ERROR"
        assert "something broke" in d["message"]

    def test_auth_error_to_dict(self):
        exc = AuthError()
        d = exc.to_dict()
        assert d["error"] is True
        assert d["code"] == "AUTH_ERROR"

    def test_rate_limit_error_to_dict(self):
        exc = RateLimitError(60)
        d = exc.to_dict()
        assert d["code"] == "RATE_LIMIT"

    def test_server_error_to_dict(self):
        exc = ServerError(503)
        d = exc.to_dict()
        assert d["code"] == "SERVER_ERROR"
        assert "503" in d["message"]

    def test_parse_error_to_dict(self):
        exc = ParseError("bad html")
        d = exc.to_dict()
        assert d["code"] == "PARSE_ERROR"


