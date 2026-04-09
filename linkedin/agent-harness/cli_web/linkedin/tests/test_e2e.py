"""E2E and subprocess tests for cli-web-linkedin.

Tests FAIL (not skip) if auth is missing.
Requires: li_at cookie in ~/.config/cli-web-linkedin/auth.json
          or CLI_WEB_LINKEDIN_AUTH_JSON env var.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------


def _resolve_cli(*args):
    """Build the command list, using installed binary or module invocation."""
    if os.environ.get("CLI_WEB_FORCE_INSTALLED"):
        return ["cli-web-linkedin", *args]
    return [sys.executable, "-m", "cli_web.linkedin", *args]


def _run(*args, input_text=None):
    """Run the CLI as a subprocess, returning (returncode, stdout, stderr)."""
    result = subprocess.run(
        _resolve_cli(*args),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        input=input_text,
        timeout=60,
    )
    return result.returncode, result.stdout, result.stderr


def _parse_json(stdout: str) -> dict:
    """Parse JSON from CLI stdout, stripping any non-JSON prefix lines."""
    # Some commands may emit non-JSON lines before the payload; find the
    # first line that starts with '{' or '['.
    lines = stdout.strip().splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            return json.loads("\n".join(lines[i:]))
    # Fallback: try the whole output
    return json.loads(stdout)


# ---------------------------------------------------------------------------
# Client fixture for live API tests
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Create a LinkedinClient instance.  Fails (not skips) if auth missing."""
    from cli_web.linkedin.core.client import LinkedinClient

    c = LinkedinClient()
    yield c
    c.close()


# ═══════════════════════════════════════════════════════════════════════════
# 1. Subprocess tests — invoke the installed CLI binary
# ═══════════════════════════════════════════════════════════════════════════


class TestCLISubprocess:
    """Subprocess tests that shell out to cli-web-linkedin."""

    # -- help / version (no auth required) --------------------------------

    def test_help_loads(self):
        rc, out, err = _run("--help")
        assert rc == 0, f"--help exited {rc}: {err}"
        combined = (out + err).lower()
        assert "linkedin" in combined, f"'linkedin' not in help output: {out}"

    def test_version(self):
        rc, out, err = _run("--version")
        assert rc == 0, f"--version exited {rc}: {err}"
        combined = out + err
        assert "0.1.0" in combined, f"'0.1.0' not in version output: {combined}"

    def test_search_help(self):
        rc, out, err = _run("search", "--help")
        assert rc == 0, f"search --help exited {rc}: {err}"

    def test_profile_help(self):
        rc, out, err = _run("profile", "--help")
        assert rc == 0, f"profile --help exited {rc}: {err}"

    def test_jobs_help(self):
        rc, out, err = _run("jobs", "--help")
        assert rc == 0, f"jobs --help exited {rc}: {err}"

    def test_post_help(self):
        rc, out, err = _run("post", "--help")
        assert rc == 0, f"post --help exited {rc}: {err}"

    def test_auth_help(self):
        rc, out, err = _run("auth", "--help")
        assert rc == 0, f"auth --help exited {rc}: {err}"

    # -- authenticated commands (require li_at) ----------------------------

    def test_auth_status_json(self):
        rc, out, err = _run("auth", "status", "--json")
        assert rc == 0, f"auth status --json exited {rc}: {err}"
        data = _parse_json(out)
        assert "authenticated" in data, f"Missing 'authenticated' key: {data}"

    def test_feed_json(self):
        rc, out, err = _run("feed", "--count", "2", "--json")
        assert rc == 0, f"feed --json exited {rc}: {err}"
        data = _parse_json(out)
        assert "data" in data or "included" in data or "elements" in data, (
            f"Expected feed response keys, got: {list(data.keys())}"
        )

    def test_profile_me_json(self):
        rc, out, err = _run("profile", "me", "--json")
        assert rc == 0, f"profile me --json exited {rc}: {err}"
        data = _parse_json(out)
        # The /me endpoint returns miniProfile fields directly
        assert "miniProfile" in str(data) or "firstName" in str(data), (
            f"Expected profile data, got keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
        )

    def test_company_json(self):
        rc, out, err = _run("company", "anthropic", "--json")
        assert rc == 0, f"company --json exited {rc}: {err}"
        data = _parse_json(out)
        assert "data" in data or "included" in data or "elements" in data, (
            f"Expected company response, got keys: {list(data.keys())}"
        )

    def test_jobs_search_json(self):
        rc, out, err = _run("jobs", "search", "python", "--limit", "3", "--json")
        assert rc == 0, f"jobs search --json exited {rc}: {err}"
        data = _parse_json(out)
        assert "count" in data or "jobs" in data, (
            f"Expected 'count' or 'jobs' key, got keys: {list(data.keys())}"
        )

    def test_feed_text_mode(self):
        """Feed in text mode should print something (not crash)."""
        rc, out, err = _run("feed", "--count", "2")
        assert rc == 0, f"feed text mode exited {rc}: {err}"


# ═══════════════════════════════════════════════════════════════════════════
# 2. Feed E2E — live API via LinkedinClient
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestFeedE2E:
    """Live feed API tests."""

    def test_feed_returns_data(self, client):
        data = client.get_feed(count=3)
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        # Feed responses contain 'data' or 'included' with elements
        assert "data" in data or "included" in data or "elements" in data, (
            f"Feed response missing expected keys: {list(data.keys())}"
        )

    def test_feed_count_parameter(self, client):
        data = client.get_feed(count=2)
        assert isinstance(data, dict)
        # Verify we got a valid response (LinkedIn may return more than
        # requested, but the response should be non-empty)
        total_keys = len(data)
        assert total_keys > 0, "Feed returned empty dict"


# ═══════════════════════════════════════════════════════════════════════════
# 3. Profile E2E — live API via LinkedinClient
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestProfileE2E:
    """Live profile API tests."""

    def test_profile_me(self, client):
        data = client._rest_get("me")
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        # /me returns miniProfile-level fields
        assert "miniProfile" in str(data) or "firstName" in data, (
            f"Profile /me missing expected fields: {list(data.keys())}"
        )
        if "firstName" in data:
            assert data["firstName"], "firstName should not be empty"

    def test_profile_get_williamhgates(self, client):
        data = client.get_profile("williamhgates")
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        # Should have profile elements or direct fields
        has_data = (
            "elements" in data
            or "firstName" in data
            or "miniProfile" in str(data)
        )
        assert has_data, (
            f"Profile get response missing expected fields: {list(data.keys())}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 4. Company E2E — live API via LinkedinClient
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestCompanyE2E:
    """Live company search API tests."""

    def test_company_search_anthropic(self, client):
        data = client.search_companies("anthropic", count=1)
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        assert "data" in data or "included" in data, (
            f"Company search response missing expected keys: {list(data.keys())}"
        )

    def test_company_search_has_results(self, client):
        data = client.search_companies("anthropic", count=1)
        included = data.get("included", [])
        has_entity = any("EntityResult" in i.get("$type", "") for i in included)
        assert has_entity, "Company search returned no EntityResult items"


# ═══════════════════════════════════════════════════════════════════════════
# 5. Jobs E2E — live API via LinkedinClient
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestJobsE2E:
    """Live jobs search API tests."""

    def test_jobs_search_returns_elements(self, client):
        data = client.search_jobs("python", count=3)
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        elements = data.get("elements", [])
        assert len(elements) > 0, "Job search returned no elements"
        # Each element should have a jobCardUnion
        first = elements[0]
        assert "jobCardUnion" in first, (
            f"First element missing 'jobCardUnion': {list(first.keys())}"
        )

    def test_job_cards_have_title(self, client):
        data = client.search_jobs("software engineer", count=3)
        elements = data.get("elements", [])
        assert len(elements) > 0, "Job search returned no elements"
        card = elements[0].get("jobCardUnion", {}).get("jobPostingCard", {})
        assert card, "First element has no jobPostingCard"
        assert "jobPostingTitle" in card, (
            f"Job card missing 'jobPostingTitle': {list(card.keys())}"
        )
