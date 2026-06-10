"""E2E and subprocess tests for cli-web-codewiki.

All live tests hit the real codewiki.google API.
Mark: @pytest.mark.e2e for live network tests.

Usage:
    pytest cli_web/codewiki/tests/test_e2e.py -v -s -m e2e
    CLI_WEB_FORCE_INSTALLED=1 pytest cli_web/codewiki/tests/test_e2e.py -v -s
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest
from cli_web.codewiki.core.client import CodeWikiClient
from cli_web.codewiki.core.models import ChatResponse, Repository, WikiPage, WikiSection

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_cli(name: str = "cli-web-codewiki") -> str:
    """Return the CLI entry-point path, falling back to module mode via sys.executable."""
    if os.environ.get("CLI_WEB_FORCE_INSTALLED"):
        path = shutil.which(name)
        if path:
            return path
        raise FileNotFoundError(f"{name} not found in PATH")
    path = shutil.which(name)
    if path:
        return path
    return sys.executable


# ---------------------------------------------------------------------------
# TestLiveRepos
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestLiveRepos:
    """Live tests for repository listing and search."""

    def test_featured_repos_returns_data(self):
        """Live: featured repos has at least 1 result with slug and stars."""
        client = CodeWikiClient()
        try:
            repos = client.featured_repos()
        finally:
            client.close()

        assert len(repos) > 0, "Expected at least one featured repo"
        first = repos[0]
        assert isinstance(first, Repository)
        assert first.slug, "slug must be non-empty"
        assert first.stars > 0, "stars must be positive"

    def test_search_returns_results(self):
        """Live: search for 'react' returns results."""
        client = CodeWikiClient()
        try:
            repos = client.search_repos("react")
        finally:
            client.close()

        assert len(repos) > 0, "Expected at least one search result for 'react'"
        assert any("react" in r.slug.lower() for r in repos), (
            "At least one slug should contain 'react'"
        )

    def test_search_empty_query_returns_empty(self):
        """Live: search with nonsense query returns empty list."""
        client = CodeWikiClient()
        try:
            repos = client.search_repos("zzzzznonexistent99999")
        finally:
            client.close()

        assert isinstance(repos, list), "Result must be a list"

    def test_search_with_limit(self):
        """Live: search respects the limit parameter."""
        client = CodeWikiClient()
        try:
            repos = client.search_repos("python", limit=5)
        finally:
            client.close()

        assert isinstance(repos, list)
        assert len(repos) <= 5, "Result count must not exceed requested limit"

    def test_featured_repo_slugs_have_org_and_name(self):
        """Live: each featured repo slug is in org/name format."""
        client = CodeWikiClient()
        try:
            repos = client.featured_repos()
        finally:
            client.close()

        assert len(repos) > 0
        for repo in repos[:5]:
            assert "/" in repo.slug, f"slug '{repo.slug}' missing org/name separator"
            assert repo.org, f"org must be non-empty for slug '{repo.slug}'"
            assert repo.name, f"name must be non-empty for slug '{repo.slug}'"


# ---------------------------------------------------------------------------
# TestLiveWiki
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestLiveWiki:
    """Live tests for wiki page fetching."""

    def test_wiki_get_returns_sections(self):
        """Live: wiki get for facebook/react returns sections."""
        client = CodeWikiClient()
        try:
            wiki = client.get_wiki("facebook/react")
        finally:
            client.close()

        assert isinstance(wiki, WikiPage)
        assert len(wiki.sections) > 0, "Expected at least one wiki section"
        assert wiki.repo.slug == "facebook/react"
        assert wiki.repo.commit_hash, "commit_hash must be present"

    def test_wiki_sections_have_content(self):
        """Live: first section has markdown content."""
        client = CodeWikiClient()
        try:
            wiki = client.get_wiki("excalidraw/excalidraw")
        finally:
            client.close()

        overview = wiki.sections[0]
        assert isinstance(overview, WikiSection)
        assert overview.title, "section title must be non-empty"
        assert overview.level >= 1, "section level must be >= 1"
        assert len(overview.content) > 50, (
            f"Expected content > 50 chars, got {len(overview.content)}"
        )

    def test_wiki_not_found(self):
        """Live: nonexistent repo raises NotFoundError."""
        from cli_web.codewiki.core.exceptions import NotFoundError

        client = CodeWikiClient()
        try:
            with pytest.raises(NotFoundError):
                client.get_wiki("nonexistent-org-xyz/nonexistent-repo-abc")
        finally:
            client.close()

    def test_wiki_sections_structure(self):
        """Live: all wiki sections have required fields."""
        client = CodeWikiClient()
        try:
            wiki = client.get_wiki("facebook/react")
        finally:
            client.close()

        for section in wiki.sections:
            assert isinstance(section, WikiSection)
            assert isinstance(section.title, str)
            assert isinstance(section.level, int)
            assert section.level >= 1
            assert isinstance(section.content, str)
            assert isinstance(section.code_refs, list)

    def test_wiki_repo_metadata(self):
        """Live: wiki page contains repo metadata including github_url."""
        client = CodeWikiClient()
        try:
            wiki = client.get_wiki("excalidraw/excalidraw")
        finally:
            client.close()

        assert wiki.repo.github_url == "https://github.com/excalidraw/excalidraw"
        assert wiki.repo.slug == "excalidraw/excalidraw"


# ---------------------------------------------------------------------------
# TestLiveChat
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestLiveChat:
    """Live tests for the Gemini chat endpoint."""

    def test_chat_returns_answer(self):
        """Live: chat returns a markdown answer."""
        client = CodeWikiClient()
        try:
            response = client.chat("What is this project about?", "facebook/react")
        finally:
            client.close()

        assert isinstance(response, ChatResponse)
        assert len(response.answer) > 50, f"Expected answer > 50 chars, got {len(response.answer)}"
        assert response.repo_slug == "facebook/react"

    def test_chat_no_rpc_leak(self):
        """Live: chat answer must not contain raw RPC data."""
        client = CodeWikiClient()
        try:
            response = client.chat("Describe the architecture", "excalidraw/excalidraw")
        finally:
            client.close()

        assert "wrb.fr" not in response.answer, "RPC frame prefix leaked into answer"
        assert "af.httprm" not in response.answer, "RPC metadata leaked into answer"

    def test_chat_answer_is_string(self):
        """Live: chat answer field is a plain string (not nested structure)."""
        client = CodeWikiClient()
        try:
            response = client.chat("What programming language is used?", "facebook/react")
        finally:
            client.close()

        assert isinstance(response.answer, str), "answer must be a plain string"
        assert response.answer.strip(), "answer must not be blank"


# ---------------------------------------------------------------------------
# TestCLISubprocess
# ---------------------------------------------------------------------------


class TestCLISubprocess:
    """Subprocess tests — exercise the installed CLI binary end-to-end."""

    @classmethod
    def setup_class(cls):
        cls.cli = _resolve_cli()
        # If cli is sys.executable, use module mode
        cls.use_module = cls.cli == sys.executable

    def _run(self, args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
        if self.use_module:
            cmd = [self.cli, "-m", "cli_web.codewiki"] + args
        else:
            cmd = [self.cli] + args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

    def test_help_loads(self):
        """Subprocess: --help exits 0 and mentions all command groups."""
        result = self._run(["--help"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "repos" in result.stdout
        assert "wiki" in result.stdout
        assert "chat" in result.stdout

    def test_repos_help(self):
        """Subprocess: repos --help lists featured and search subcommands."""
        result = self._run(["repos", "--help"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "featured" in result.stdout
        assert "search" in result.stdout

    def test_wiki_help(self):
        """Subprocess: wiki --help lists get, sections, section subcommands."""
        result = self._run(["wiki", "--help"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "get" in result.stdout
        assert "sections" in result.stdout
        assert "section" in result.stdout

    @pytest.mark.e2e
    def test_repos_featured_json(self):
        """Subprocess/live: repos featured --json returns valid structured output."""
        result = self._run(["repos", "featured", "--json"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0
        first = data["data"][0]
        assert "slug" in first
        assert "stars" in first

    @pytest.mark.e2e
    def test_repos_search_json(self):
        """Subprocess/live: repos search returns valid JSON."""
        result = self._run(["repos", "search", "kubernetes", "--json"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert isinstance(data["data"], list)

    @pytest.mark.e2e
    def test_repos_search_limit(self):
        """Subprocess/live: repos search --limit is respected."""
        result = self._run(["repos", "search", "python", "--limit", "3", "--json"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert len(data["data"]) <= 3

    @pytest.mark.e2e
    def test_wiki_sections_json(self):
        """Subprocess/live: wiki sections returns a list with title fields."""
        result = self._run(["wiki", "sections", "facebook/react", "--json"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        sections = data["data"]
        assert isinstance(sections, list)
        assert len(sections) > 0
        assert "title" in sections[0]
        assert "level" in sections[0]

    @pytest.mark.e2e
    def test_wiki_get_json(self):
        """Subprocess/live: wiki get returns full page structure."""
        result = self._run(["wiki", "get", "excalidraw/excalidraw", "--json"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        wiki = data["data"]
        assert "repo" in wiki
        assert "sections" in wiki
        assert wiki["repo"]["slug"] == "excalidraw/excalidraw"
        assert len(wiki["sections"]) > 0

    @pytest.mark.e2e
    def test_chat_ask_json(self):
        """Subprocess/live: chat ask returns answer without RPC leaks."""
        result = self._run(
            ["chat", "ask", "What is this?", "--repo", "facebook/react", "--json"],
            timeout=90,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        answer = data["data"]["answer"]
        assert len(answer) > 20, f"Expected longer answer, got: {answer!r}"
        assert "wrb.fr" not in answer, "RPC frame prefix leaked into CLI output"

    @pytest.mark.e2e
    def test_wiki_not_found_returns_error_json(self):
        """Subprocess/live: wiki get for nonexistent repo exits non-zero with error JSON."""
        result = self._run(["wiki", "get", "nonexistent-org-xyz/nonexistent-repo-abc", "--json"])
        assert result.returncode != 0
        data = json.loads(result.stdout)
        assert data.get("error") is True
        assert data.get("code") == "NOT_FOUND"

    @pytest.mark.e2e
    def test_repos_featured_no_json_exits_zero(self):
        """Subprocess/live: repos featured (no --json) prints table and exits 0."""
        result = self._run(["repos", "featured"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        # Should contain at least one org/repo slug pattern
        assert "/" in result.stdout


# ---------------------------------------------------------------------------
# TestReadOnlyRoundTrip
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestReadOnlyRoundTrip:
    """Round-trip consistency tests across API calls."""

    def test_list_detail_consistency(self):
        """Round-trip: search result slug matches wiki page repo info."""
        client = CodeWikiClient()
        try:
            results = client.search_repos("excalidraw")
            assert len(results) > 0, "Expected at least one search result"
            slug = results[0].slug
            wiki = client.get_wiki(slug)
        finally:
            client.close()

        assert wiki.repo.slug == slug, f"wiki.repo.slug '{wiki.repo.slug}' != search slug '{slug}'"
        assert len(wiki.sections) > 0, "Expected at least one section in wiki page"

    def test_featured_to_wiki_round_trip(self):
        """Round-trip: first featured repo can have its wiki fetched."""
        client = CodeWikiClient()
        try:
            repos = client.featured_repos()
            assert len(repos) > 0
            slug = repos[0].slug
            wiki = client.get_wiki(slug)
        finally:
            client.close()

        assert wiki.repo.slug == slug
        # The wiki page must belong to the same org/repo
        assert wiki.repo.org == repos[0].org
        assert wiki.repo.name == repos[0].name
