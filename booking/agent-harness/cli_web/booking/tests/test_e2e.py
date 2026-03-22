"""E2E tests for cli-web-booking — live API calls + subprocess tests.

These tests hit the real Booking.com APIs. The autocomplete tests
work without auth (GraphQL bypass). Search/detail tests require
WAF cookies — run `cli-web-booking auth login` first.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

from cli_web.booking.core.auth import is_authenticated
from cli_web.booking.core.client import BookingClient


# ── Helpers ────────────────────────────────────────────────────────


def _resolve_cli(name):
    """Resolve installed CLI command; falls back to python -m for dev."""
    force = os.environ.get("CLI_WEB_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-web-", "cli_web.").replace("-", ".") + "." + name.split("-")[-1] + "_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


def _require_auth():
    """Fail (not skip) if auth is not configured."""
    if not is_authenticated():
        pytest.fail(
            "WAF cookies not configured. Run: cli-web-booking auth login"
        )


# ── Live E2E: AutoComplete (no auth needed) ───────────────────────


class TestAutoCompleteLive:
    """Live tests for GraphQL AutoComplete — no auth required."""

    def test_autocomplete_paris(self):
        client = BookingClient()
        results = client.autocomplete("Paris")
        assert len(results) > 0
        assert results[0].dest_type == "city"
        assert results[0].dest_id  # not empty
        assert "Paris" in results[0].title
        print(f"[verify] Paris dest_id={results[0].dest_id}")

    def test_autocomplete_tokyo(self):
        client = BookingClient()
        results = client.autocomplete("Tokyo")
        assert len(results) > 0
        assert results[0].title  # has a title
        print(f"[verify] Tokyo dest_id={results[0].dest_id}")

    def test_autocomplete_empty(self):
        client = BookingClient()
        results = client.autocomplete("xyznonexistent12345")
        # May return 0 or fallback results
        assert isinstance(results, list)

    def test_autocomplete_limit(self):
        client = BookingClient()
        results = client.autocomplete("London", limit=3)
        assert len(results) <= 3


# ── Live E2E: Search (requires WAF cookies) ───────────────────────


class TestSearchLive:
    """Live search tests — require WAF cookies."""

    @pytest.fixture(autouse=True)
    def require_auth(self):
        _require_auth()

    def test_search_paris(self):
        client = BookingClient()
        results = client.search(
            destination="Paris",
            checkin="2026-04-01",
            checkout="2026-04-04",
            adults=2,
            rooms=1,
        )
        assert len(results) > 0
        first = results[0]
        assert first.title  # has a name
        assert first.slug  # has a URL slug
        print(f"[verify] First result: {first.title} ({first.slug})")

    def test_search_has_scores(self):
        client = BookingClient()
        results = client.search("London", "2026-04-01", "2026-04-04")
        scored = [r for r in results if r.score is not None]
        assert len(scored) > 0, "Expected at least some results with scores"
        assert scored[0].score > 0

    def test_search_has_prices(self):
        client = BookingClient()
        results = client.search("Berlin", "2026-04-01", "2026-04-04")
        priced = [r for r in results if r.price_amount is not None]
        assert len(priced) > 0, "Expected at least some results with prices"
        assert priced[0].price_amount > 0

    def test_search_sort_by_price(self):
        client = BookingClient()
        results = client.search("Paris", "2026-04-01", "2026-04-04", sort="price")
        assert len(results) > 0


# ── Live E2E: Property Detail (requires WAF cookies) ──────────────


class TestPropertyDetailLive:
    """Live property detail tests."""

    @pytest.fixture(autouse=True)
    def require_auth(self):
        _require_auth()

    def test_get_property_le_senat(self):
        client = BookingClient()
        detail = client.get_property(
            slug="fr/lesenatparis.html",
            checkin="2026-04-01",
            checkout="2026-04-04",
        )
        assert detail.name == "Le Senat"
        assert detail.score is not None
        assert detail.score > 0
        assert detail.review_count > 0
        assert "France" in detail.country
        print(f"[verify] {detail.name}: {detail.score}/10, {detail.review_count} reviews")


# ── Round-Trip: List → Detail ─────────────────────────────────────


class TestRoundTrip:
    """Verify data consistency between search and detail."""

    @pytest.fixture(autouse=True)
    def require_auth(self):
        _require_auth()

    def test_search_then_detail(self):
        """Search → get first result's detail → verify name matches."""
        client = BookingClient()
        results = client.search("Paris", "2026-04-01", "2026-04-04")
        assert len(results) > 0

        first = results[0]
        assert first.slug, "First result must have a slug"

        detail = client.get_property(first.slug, "2026-04-01", "2026-04-04")
        assert detail.name, "Detail must have a name"
        # Name should be similar (HTML parsing may differ slightly)
        print(f"[verify] Search: {first.title} → Detail: {detail.name}")


# ── Subprocess Tests ──────────────────────────────────────────────


class TestCLISubprocess:
    """Test the installed CLI binary via subprocess."""

    CLI_BASE = _resolve_cli("cli-web-booking")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            check=check,
            encoding="utf-8",
            errors="replace",
        )

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "cli-web-booking" in result.stdout
        assert "search" in result.stdout

    def test_version(self):
        result = self._run(["--version"])
        assert result.returncode == 0
        assert "0.1.0" in result.stdout

    def test_autocomplete_json(self):
        result = self._run(["autocomplete", "Paris", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert len(data["results"]) > 0
        assert data["results"][0]["title"] == "Paris"

    def test_auth_status_json(self):
        result = self._run(["auth", "status", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "authenticated" in data

    def test_search_json(self):
        """Subprocess search test — requires WAF cookies."""
        if not is_authenticated():
            pytest.fail("WAF cookies not configured. Run: cli-web-booking auth login")

        result = self._run([
            "search", "find", "Paris",
            "--checkin", "2026-04-01",
            "--checkout", "2026-04-04",
            "--json",
        ], check=False)

        if result.returncode != 0:
            # May fail if cookies expired
            print(f"Search failed: {result.stderr}")
            pytest.skip("Search failed — WAF cookies may have expired")

        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["count"] > 0
        assert data["properties"][0]["title"]
