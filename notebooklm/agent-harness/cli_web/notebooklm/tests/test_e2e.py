"""Comprehensive E2E tests for the NotebookLM CLI.

Three test classes:
  - TestFixtureReplay  : pure parsing tests with hardcoded fixture data (no network)
  - TestLiveAPI        : real API calls (fail without auth)
  - TestCLISubprocess  : subprocess end-to-end via the installed CLI or module fallback
"""

import json
import os
import shutil
import subprocess
import sys
import time

import pytest

# ---------------------------------------------------------------------------
# CLI resolver
# ---------------------------------------------------------------------------

def _resolve_cli(name):
    force = os.environ.get("CLI_WEB_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = "cli_web.notebooklm.notebooklm_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

# rLM1Ne (get_notebook) response — flat array form
# ["title", sources_list, uuid, emoji, null, flags]
FIXTURE_RLME1NE = [
    "My Notebook",
    [
        [
            "source-id-123",
            "Source Name",
            [None, 9659, [1769878626, 803288000], ["ea6e64da", [1769878626, 523384000]], 4, None, 1],
            [None, 2],
        ]
    ],
    "nb-uuid-1234",
    "\U0001f4d3",  # 📓
    None,
    [True, None, None, None, None, [1769878626, 0], None, None, [1769878626, 0]],
]

# wXbhsf (list notebooks) entry — flat content entry form
# [title, [[sources...]], uuid, emoji, null, flags]
FIXTURE_WXBHSF_ENTRY = [
    "My Notebook",
    [["src-id"]],
    "nb-uuid-5678",
    "\U0001f4d3",  # 📓
    None,
    [True, None, None, None, None, [1700000000, 0], None, None, [1700000000, 0]],
]

# CCqFvf (create notebook) response
# ["", null, uuid, null, null, flags...]
FIXTURE_CCQFVF = ["", None, "new-nb-uuid", None, None, []]

# VfAZjd (add url source) response
# [null, "source_id"]
FIXTURE_VFAZJD = [None, "new-source-id-abc"]

# izAoDd / rLM1Ne source entry (single source from the sources list)
FIXTURE_SOURCE_ENTRY = [
    "source-id-123",
    "Source Name",
    [None, 9659, [1769878626, 803288000], ["ea6e64da", [1769878626, 523384000]], 4, None, 1],
    [None, 2],
]


# ===========================================================================
# Class 1: TestFixtureReplay — pure parsing, no network
# ===========================================================================

class TestFixtureReplay:
    """Parse real-shaped fixture data through the model parsing functions.

    No auth, no network — verifies parsing logic in isolation.
    """

    def test_rlm1ne_parse_title(self):
        """rLM1Ne flat array: title extracted correctly."""
        from cli_web.notebooklm.core.models import parse_notebook

        nb = parse_notebook(FIXTURE_RLME1NE)
        assert nb is not None, "parse_notebook returned None for rLM1Ne fixture"
        assert nb.title == "My Notebook", f"Expected 'My Notebook', got {nb.title!r}"

    def test_rlm1ne_parse_source_count(self):
        """rLM1Ne flat array: source_count matches number of sources in list."""
        from cli_web.notebooklm.core.models import parse_notebook

        nb = parse_notebook(FIXTURE_RLME1NE)
        assert nb is not None
        assert nb.source_count == 1, f"Expected source_count=1, got {nb.source_count}"

    def test_rlm1ne_parse_notebook_id(self):
        """rLM1Ne flat array: notebook id extracted at position [2]."""
        from cli_web.notebooklm.core.models import parse_notebook

        nb = parse_notebook(FIXTURE_RLME1NE)
        assert nb is not None
        assert nb.id == "nb-uuid-1234", f"Expected 'nb-uuid-1234', got {nb.id!r}"
        print(f"[verify] notebook id={nb.id}")

    def test_rlm1ne_parse_is_pinned(self):
        """rLM1Ne flat array: is_pinned flag from flags[0]."""
        from cli_web.notebooklm.core.models import parse_notebook

        nb = parse_notebook(FIXTURE_RLME1NE)
        assert nb is not None
        assert nb.is_pinned is True, f"Expected is_pinned=True, got {nb.is_pinned}"

    def test_rlm1ne_parse_created_at(self):
        """rLM1Ne flat array: created_at extracted from flags[5][0]."""
        from cli_web.notebooklm.core.models import parse_notebook

        nb = parse_notebook(FIXTURE_RLME1NE)
        assert nb is not None
        assert nb.created_at == 1769878626, f"Expected created_at=1769878626, got {nb.created_at}"

    def test_wXbhsf_parse_entry(self):
        """wXbhsf list content entry: title, id, and emoji parsed correctly."""
        from cli_web.notebooklm.core.client import _parse_notebook_content_entry

        nb = _parse_notebook_content_entry(FIXTURE_WXBHSF_ENTRY)
        assert nb is not None, "_parse_notebook_content_entry returned None"
        assert nb.title == "My Notebook", f"Expected 'My Notebook', got {nb.title!r}"
        assert nb.id == "nb-uuid-5678", f"Expected 'nb-uuid-5678', got {nb.id!r}"
        assert nb.emoji == "\U0001f4d3", f"Expected emoji 📓, got {nb.emoji!r}"
        print(f"[verify] notebook id={nb.id} title={nb.title!r}")

    def test_wXbhsf_parse_source_count(self):
        """wXbhsf list content entry: source_count equals number of source entries."""
        from cli_web.notebooklm.core.client import _parse_notebook_content_entry

        nb = _parse_notebook_content_entry(FIXTURE_WXBHSF_ENTRY)
        assert nb is not None
        assert nb.source_count == 1, f"Expected source_count=1, got {nb.source_count}"

    def test_wXbhsf_skips_empty_title_entries(self):
        """_parse_notebook_content_entry returns None for metadata/cursor entries with empty title."""
        from cli_web.notebooklm.core.client import _parse_notebook_content_entry

        cursor_entry = ["", None, "some-cursor-uuid", None, None, []]
        result = _parse_notebook_content_entry(cursor_entry)
        assert result is None, "Expected None for empty-title cursor entry"

    def test_create_response_parse(self):
        """CCqFvf create response: notebook id extracted from position [2]."""
        from cli_web.notebooklm.core.client import _parse_create_response

        nb = _parse_create_response(FIXTURE_CCQFVF)
        assert nb is not None, "_parse_create_response returned None"
        assert nb.id == "new-nb-uuid", f"Expected 'new-nb-uuid', got {nb.id!r}"
        print(f"[verify] created notebook id={nb.id}")

    def test_create_response_empty_title(self):
        """CCqFvf create response: title is empty (injected later by caller)."""
        from cli_web.notebooklm.core.client import _parse_create_response

        nb = _parse_create_response(FIXTURE_CCQFVF)
        assert nb is not None
        assert nb.title == "", f"Expected empty title in raw create response, got {nb.title!r}"

    def test_create_response_none_returns_none(self):
        """_parse_create_response returns None for empty/None input."""
        from cli_web.notebooklm.core.client import _parse_create_response

        assert _parse_create_response(None) is None
        assert _parse_create_response([]) is None
        assert _parse_create_response(["", None]) is None  # no id at [2]

    def test_add_url_source_response(self):
        """VfAZjd add-url response: source_id is at index [1]."""
        # This mirrors what client.add_url_source does: result[1]
        result = FIXTURE_VFAZJD
        assert isinstance(result, list) and len(result) > 1
        source_id = result[1]
        assert source_id == "new-source-id-abc", f"Expected 'new-source-id-abc', got {source_id!r}"
        print(f"[verify] source id={source_id}")

    def test_parse_source_from_rlm1ne(self):
        """parse_source: parses a source entry from the rLM1Ne sources list."""
        from cli_web.notebooklm.core.models import parse_source

        src = parse_source(FIXTURE_SOURCE_ENTRY)
        assert src is not None, "parse_source returned None"
        assert src.id == "source-id-123", f"Expected 'source-id-123', got {src.id!r}"
        assert src.name == "Source Name", f"Expected 'Source Name', got {src.name!r}"
        print(f"[verify] source id={src.id} name={src.name!r}")

    def test_parse_source_char_count(self):
        """parse_source: char_count extracted from meta[1]."""
        from cli_web.notebooklm.core.models import parse_source

        src = parse_source(FIXTURE_SOURCE_ENTRY)
        assert src is not None
        assert src.char_count == 9659, f"Expected char_count=9659, got {src.char_count}"

    def test_parse_source_type_text(self):
        """parse_source: type_id=4 maps to 'text'."""
        from cli_web.notebooklm.core.models import parse_source

        src = parse_source(FIXTURE_SOURCE_ENTRY)
        assert src is not None
        assert src.source_type == "text", f"Expected source_type='text', got {src.source_type!r}"

    def test_parse_source_created_at(self):
        """parse_source: created_at extracted from meta[2][0]."""
        from cli_web.notebooklm.core.models import parse_source

        src = parse_source(FIXTURE_SOURCE_ENTRY)
        assert src is not None
        assert src.created_at == 1769878626, f"Expected created_at=1769878626, got {src.created_at}"

    def test_parse_source_url_type(self):
        """parse_source: type_id=5 maps to 'url'."""
        from cli_web.notebooklm.core.models import parse_source

        url_entry = [
            "url-src-id",
            "https://example.com",
            [None, 500, [1700000000, 0], None, 5, None, 1, ["https://example.com"]],
            [None, 2],
        ]
        src = parse_source(url_entry)
        assert src is not None
        assert src.source_type == "url", f"Expected 'url', got {src.source_type!r}"
        assert src.url == "https://example.com", f"Expected URL, got {src.url!r}"

    def test_parse_source_none_returns_none(self):
        """parse_source returns None for empty/None input."""
        from cli_web.notebooklm.core.models import parse_source

        assert parse_source(None) is None
        assert parse_source([]) is None

    def test_parse_notebook_none_returns_none(self):
        """parse_notebook returns None for empty/None input."""
        from cli_web.notebooklm.core.models import parse_notebook

        assert parse_notebook(None) is None
        assert parse_notebook([]) is None

    def test_extract_sources_from_nb_result(self):
        """_extract_sources_from_nb_result: pulls sources from rLM1Ne decoded result."""
        from cli_web.notebooklm.core.client import _extract_sources_from_nb_result

        # rLM1Ne decode wraps the flat array in another list
        result = [FIXTURE_RLME1NE]
        sources = _extract_sources_from_nb_result(result)
        assert isinstance(sources, list), "Expected a list of sources"
        assert len(sources) == 1, f"Expected 1 source, got {len(sources)}"


# ===========================================================================
# Class 2: TestLiveAPI — real API calls, FAIL without auth
# ===========================================================================

def _require_auth():
    """Fail immediately if auth cookies are not configured."""
    try:
        from cli_web.notebooklm.core.auth import load_cookies
        load_cookies()
    except Exception:
        pytest.fail("Auth not configured. Run: cli-web-notebooklm auth login")


class TestLiveAPI:
    """Real API calls against NotebookLM.

    All tests fail (not skip) if auth is not configured.
    All tests that create notebooks clean up in a finally block.
    """

    def test_live_list_notebooks(self):
        """List notebooks: verify result is a list, each item has id and title."""
        _require_auth()
        from cli_web.notebooklm.core.client import NotebookLMClient

        client = NotebookLMClient()
        notebooks = client.list_notebooks()
        assert isinstance(notebooks, list), f"Expected list, got {type(notebooks)}"
        print(f"[verify] list_notebooks returned {len(notebooks)} notebooks")
        for nb in notebooks:
            assert nb.id, f"Notebook missing id: {nb!r}"
            assert isinstance(nb.title, str), f"Notebook title is not a string: {nb!r}"
            print(f"[verify] notebook id={nb.id!r} title={nb.title!r}")

    def test_live_create_get_delete_notebook(self):
        """Create → get → verify title matches → delete notebook lifecycle."""
        _require_auth()
        from cli_web.notebooklm.core.client import NotebookLMClient

        client = NotebookLMClient()
        title = f"E2E-Test-{int(time.time())}"
        nb_id = None
        try:
            nb = client.create_notebook(title)
            nb_id = nb.id
            assert nb_id, "create_notebook returned notebook with empty id"
            assert nb.title == title, f"Expected title {title!r}, got {nb.title!r}"
            print(f"[verify] created notebook id={nb_id!r} title={nb.title!r}")

            fetched = client.get_notebook(nb_id)
            assert fetched.id == nb_id, f"get_notebook id mismatch: {fetched.id!r} != {nb_id!r}"
            assert fetched.title == title, (
                f"get_notebook title mismatch: {fetched.title!r} != {title!r}"
            )
            print(f"[verify] fetched notebook id={fetched.id!r} title={fetched.title!r}")
        finally:
            if nb_id:
                client.delete_notebook(nb_id)
                print(f"[verify] deleted notebook id={nb_id!r}")

    def test_live_add_url_source(self):
        """Create notebook → add URL source → verify source_id returned → delete notebook."""
        _require_auth()
        from cli_web.notebooklm.core.client import NotebookLMClient

        client = NotebookLMClient()
        title = f"E2E-URLSource-{int(time.time())}"
        nb_id = None
        try:
            nb = client.create_notebook(title)
            nb_id = nb.id
            print(f"[verify] created notebook id={nb_id!r}")

            url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
            src = client.add_url_source(nb_id, url)
            assert src.id, f"add_url_source returned source with empty id"
            assert src.url == url, f"Expected url={url!r}, got {src.url!r}"
            print(f"[verify] added source id={src.id!r} url={src.url!r}")
        finally:
            if nb_id:
                client.delete_notebook(nb_id)
                print(f"[verify] deleted notebook id={nb_id!r}")

    def test_live_list_sources(self):
        """Find a notebook with sources and verify list_sources returns count > 0."""
        _require_auth()
        from cli_web.notebooklm.core.client import NotebookLMClient

        client = NotebookLMClient()
        notebooks = client.list_notebooks()
        nb_with_sources = next(
            (nb for nb in notebooks if nb.source_count > 0), None
        )
        if nb_with_sources is None:
            pytest.skip("No notebooks with sources found — skipping live source list test")

        print(f"[verify] using notebook id={nb_with_sources.id!r} source_count={nb_with_sources.source_count}")
        sources = client.list_sources(nb_with_sources.id)
        assert isinstance(sources, list), f"Expected list, got {type(sources)}"
        assert len(sources) > 0, (
            f"Expected >0 sources for notebook {nb_with_sources.id!r}, got 0"
        )
        for src in sources:
            assert src.id, f"Source missing id: {src!r}"
            print(f"[verify] source id={src.id!r} name={src.name!r} type={src.source_type!r}")

    def test_live_whoami(self):
        """get_user: verify email is a non-empty string."""
        _require_auth()
        from cli_web.notebooklm.core.client import NotebookLMClient

        client = NotebookLMClient()
        user = client.get_user()
        assert user.email, f"Expected non-empty email, got {user.email!r}"
        assert isinstance(user.email, str), f"email is not a string: {user.email!r}"
        print(f"[verify] whoami email={user.email!r} display_name={user.display_name!r}")

    def test_live_chat_query(self):
        """Find a notebook with sources, ask a question, verify answer is non-empty."""
        _require_auth()
        from cli_web.notebooklm.core.client import NotebookLMClient

        client = NotebookLMClient()
        notebooks = client.list_notebooks()
        nb_with_sources = next(
            (nb for nb in notebooks if nb.source_count > 0), None
        )
        if nb_with_sources is None:
            pytest.skip("No notebooks with sources found — skipping live chat test")

        nb_id = nb_with_sources.id
        print(f"[verify] asking question to notebook id={nb_id!r}")
        answer = client.chat_query(nb_id, "What is the main topic of this notebook?")
        assert isinstance(answer, str), f"Expected str answer, got {type(answer)}"
        assert len(answer) > 0, "chat_query returned empty answer"
        print(f"[verify] chat answer (first 120 chars): {answer[:120]!r}")


# ===========================================================================
# Class 3: TestCLISubprocess — subprocess end-to-end
# ===========================================================================

class TestCLISubprocess:
    """End-to-end tests using subprocess to invoke the CLI."""

    CLI_BASE = _resolve_cli("cli-web-notebooklm")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=check,
        )

    def test_help(self):
        """--help exits 0 and mentions 'notebooks' in output."""
        result = self._run(["--help"])
        assert result.returncode == 0, f"--help exited {result.returncode}\n{result.stderr}"
        combined = result.stdout + result.stderr
        assert "notebooks" in combined.lower(), (
            f"Expected 'notebooks' in help output, got:\n{combined}"
        )

    def test_notebooks_help(self):
        """notebooks --help exits 0."""
        result = self._run(["notebooks", "--help"])
        assert result.returncode == 0, (
            f"notebooks --help exited {result.returncode}\n{result.stderr}"
        )

    def test_notebooks_list_json(self):
        """notebooks list --json: exits 0, output is a valid JSON list with id/title keys."""
        result = self._run(["notebooks", "list", "--json"])
        assert result.returncode == 0, (
            f"notebooks list --json exited {result.returncode}\n{result.stderr}"
        )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"notebooks list --json output is not valid JSON: {exc}\n"
                f"stdout: {result.stdout[:500]!r}"
            )
        assert isinstance(data, list), f"Expected JSON list, got {type(data)}: {data!r}"
        print(f"[verify] notebooks list returned {len(data)} notebooks")
        for item in data:
            assert "id" in item, f"Notebook JSON entry missing 'id' key: {item!r}"
            assert "title" in item, f"Notebook JSON entry missing 'title' key: {item!r}"
            print(f"[verify] notebook id={item['id']!r} title={item['title']!r}")

    def test_auth_status_json(self):
        """auth status --json: exits 0 and output has 'configured' key."""
        result = self._run(["auth", "status", "--json"])
        assert result.returncode == 0, (
            f"auth status --json exited {result.returncode}\n{result.stderr}"
        )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"auth status --json output is not valid JSON: {exc}\n"
                f"stdout: {result.stdout[:500]!r}"
            )
        assert "configured" in data, (
            f"Expected 'configured' key in auth status output, got: {data!r}"
        )
        print(f"[verify] auth status configured={data.get('configured')} valid={data.get('valid')}")

    def test_whoami_json(self):
        """whoami --json: exits 0 and output has 'email' key."""
        result = self._run(["whoami", "--json"])
        assert result.returncode == 0, (
            f"whoami --json exited {result.returncode}\n{result.stderr}"
        )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"whoami --json output is not valid JSON: {exc}\n"
                f"stdout: {result.stdout[:500]!r}"
            )
        assert "email" in data, f"Expected 'email' key in whoami output, got: {data!r}"
        assert data["email"], f"Expected non-empty email, got {data['email']!r}"
        print(f"[verify] whoami email={data['email']!r}")

    def test_notebooks_create_and_delete(self):
        """Create notebook via CLI, verify it appears in list, then delete it."""
        title = f"SubprocessTest-{int(time.time())}"
        nb_id = None
        try:
            # Create
            result = self._run(["notebooks", "create", "--title", title, "--json"])
            assert result.returncode == 0, (
                f"notebooks create exited {result.returncode}\n{result.stderr}"
            )
            try:
                created = json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                pytest.fail(
                    f"notebooks create --json output is not valid JSON: {exc}\n"
                    f"stdout: {result.stdout[:500]!r}"
                )
            assert "id" in created, f"Create response missing 'id' key: {created!r}"
            nb_id = created["id"]
            assert nb_id, f"Create response returned empty id: {created!r}"
            print(f"[verify] created notebook id={nb_id!r} title={created.get('title')!r}")

            # Verify it appears in list
            list_result = self._run(["notebooks", "list", "--json"])
            assert list_result.returncode == 0, (
                f"notebooks list exited {list_result.returncode}\n{list_result.stderr}"
            )
            notebooks = json.loads(list_result.stdout)
            ids = [nb.get("id") for nb in notebooks]
            assert nb_id in ids, (
                f"Newly created notebook id={nb_id!r} not found in list.\n"
                f"Listed ids: {ids}"
            )
            print(f"[verify] notebook id={nb_id!r} confirmed in list")
        finally:
            if nb_id:
                del_result = self._run(
                    ["notebooks", "delete", "--id", nb_id, "--confirm"], check=False
                )
                if del_result.returncode != 0:
                    print(
                        f"[warn] delete returned {del_result.returncode}: "
                        f"{del_result.stderr[:200]}"
                    )
                else:
                    print(f"[verify] deleted notebook id={nb_id!r}")
