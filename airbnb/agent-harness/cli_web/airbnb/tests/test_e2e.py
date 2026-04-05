"""E2E and subprocess tests for cli-web-airbnb.

These tests make real HTTP requests to Airbnb. They verify the CLI works
end-to-end with live data. No auth is required (public no-auth site).

Windows note: encoding="utf-8", errors="replace" is required on all
subprocess.run() calls — Airbnb responses may contain emoji/non-ASCII that
crash the default cp1252 encoding on Windows.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys


def _resolve_cli(name: str) -> list[str]:
    """Resolve CLI command — installed binary first, then Python module fallback."""
    import shutil
    # CI override: force installed binary path resolution
    if os.environ.get("CLI_WEB_FORCE_INSTALLED"):
        binary = shutil.which(name)
        if binary:
            return [binary]
        raise RuntimeError(
            f"CLI_WEB_FORCE_INSTALLED is set but '{name}' not found on PATH. "
            "Run: pip install -e ."
        )
    binary = shutil.which(name)
    if binary:
        return [binary]
    # Fall back to running as Python module
    return [sys.executable, "-m", name.replace("-", "_")]


CLI = _resolve_cli("cli-web-airbnb")


# ---------------------------------------------------------------------------
# search stays
# ---------------------------------------------------------------------------

class TestSearchStays:
    def test_search_returns_listings(self):
        result = subprocess.run(
            CLI + ["search", "stays", "London, UK", "--json"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["count"] > 0
        assert len(data["listings"]) > 0
        listing = data["listings"][0]
        assert listing["id"]
        assert listing["name"]
        assert listing["url"].startswith("https://www.airbnb.com/rooms/")

    def test_search_with_dates_and_guests(self):
        result = subprocess.run(
            CLI + ["search", "stays", "Paris, France",
                   "--adults", "2", "--checkin", "2025-08-01", "--checkout", "2025-08-05",
                   "--json"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True

    def test_search_with_max_price(self):
        result = subprocess.run(
            CLI + ["search", "stays", "Berlin, Germany", "--max-price", "200", "--json"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True

    def test_search_pagination_cursor(self):
        # First page
        result1 = subprocess.run(
            CLI + ["search", "stays", "London, UK", "--json"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        assert result1.returncode == 0
        data1 = json.loads(result1.stdout)
        cursor = data1.get("next_cursor")
        if cursor:
            result2 = subprocess.run(
                CLI + ["search", "stays", "London, UK", "--cursor", cursor, "--json"],
                capture_output=True, text=True, timeout=60,
                encoding="utf-8", errors="replace",
            )
            assert result2.returncode == 0
            data2 = json.loads(result2.stdout)
            assert data2["success"] is True
            # Second page listings differ from first
            ids1 = {l["id"] for l in data1["listings"]}
            ids2 = {l["id"] for l in data2["listings"]}
            assert ids1 != ids2, "Page 2 should differ from page 1"

    def test_search_json_structure(self):
        result = subprocess.run(
            CLI + ["search", "stays", "New York, NY, United States", "--json"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        listing = data["listings"][0]
        # All required fields present
        for field in ["id", "id_b64", "name", "url"]:
            assert field in listing, f"Missing field: {field}"

    def test_search_listing_fields_not_empty(self):
        """Verify the listing JSON fields are real data, not empty stubs."""
        result = subprocess.run(
            CLI + ["search", "stays", "London, UK", "--json"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        listing = data["listings"][0]
        # id must be a non-trivial integer string
        assert listing["id"].isdigit(), f"id should be numeric, got: {listing['id']}"
        # name must be non-empty
        assert len(listing["name"]) > 2, f"name too short: {listing['name']}"
        # url must point to a real room page
        assert f"/rooms/{listing['id']}" in listing["url"]


# ---------------------------------------------------------------------------
# --json flag placement (both group-level and subcommand-level)
# ---------------------------------------------------------------------------

class TestJsonFlagPlacement:
    def test_json_flag_at_group_level_search(self):
        """--json before subcommand returns valid JSON."""
        result = subprocess.run(
            CLI + ["--json", "search", "stays", "London, UK"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data.get("success") is True

    def test_json_flag_at_subcommand_level_search(self):
        """--json after 'stays' subcommand must NOT raise 'No such option'."""
        result = subprocess.run(
            CLI + ["search", "stays", "London, UK", "--json"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0, (
            f"--json at end of subcommand failed.\n"
            f"stderr: {result.stderr}\n"
            "Fix: ensure @click.option('--json', 'json_mode', ...) is on the stays command."
        )
        data = json.loads(result.stdout)
        assert data.get("success") is True

    def test_json_flag_at_group_level_autocomplete(self):
        """--json at group level works for autocomplete locations."""
        result = subprocess.run(
            CLI + ["--json", "autocomplete", "locations", "Lond"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data.get("success") is True

    def test_json_flag_at_subcommand_level_autocomplete(self):
        """--json at end of autocomplete locations must work."""
        result = subprocess.run(
            CLI + ["autocomplete", "locations", "Lond", "--json"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0, (
            f"--json at end of subcommand failed.\nstderr: {result.stderr}"
        )
        data = json.loads(result.stdout)
        assert data.get("success") is True


# ---------------------------------------------------------------------------
# listings get
# ---------------------------------------------------------------------------

class TestListingsGet:
    def test_get_listing_returns_name(self):
        result = subprocess.run(
            CLI + ["listings", "get", "1603496841117193305", "--json"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["id"] == "1603496841117193305"
        assert data["name"]
        assert data["url"].startswith("https://www.airbnb.com/rooms/")

    def test_get_listing_not_found(self):
        result = subprocess.run(
            CLI + ["listings", "get", "99999999999999", "--json"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        # Either a not-found error or a parse error is acceptable
        if result.returncode != 0:
            data = json.loads(result.stdout)
            assert data["error"] is True

    def test_get_listing_search_then_get_roundtrip(self):
        """Search → grab first ID → get listing → verify ID and URL match."""
        # Step 1: search for listings
        search_result = subprocess.run(
            CLI + ["search", "stays", "London, UK", "--json"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        assert search_result.returncode == 0
        search_data = json.loads(search_result.stdout)
        assert search_data["count"] > 0

        # Step 2: get first listing by ID
        first_id = search_data["listings"][0]["id"]
        get_result = subprocess.run(
            CLI + ["listings", "get", first_id, "--json"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        assert get_result.returncode == 0, f"stderr: {get_result.stderr}"
        detail = json.loads(get_result.stdout)

        # Step 3: verify consistency
        assert detail["id"] == first_id
        assert detail["url"] == f"https://www.airbnb.com/rooms/{first_id}"
        assert detail["name"]  # detail view must have a name


# ---------------------------------------------------------------------------
# autocomplete
# ---------------------------------------------------------------------------

class TestAutocomplete:
    def test_locations_returns_suggestions(self):
        result = subprocess.run(
            CLI + ["autocomplete", "locations", "Lond", "--json"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert "suggestions" in data

    def test_locations_num_results(self):
        result = subprocess.run(
            CLI + ["autocomplete", "locations", "Paris", "--num-results", "3", "--json"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data["suggestions"]) <= 3

    def test_locations_suggestion_fields(self):
        """Each suggestion must have query and display fields."""
        result = subprocess.run(
            CLI + ["autocomplete", "locations", "Tokyo", "--json"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        if data["suggestions"]:
            s = data["suggestions"][0]
            assert "query" in s
            assert "display" in s


# ---------------------------------------------------------------------------
# CLI help and version
# ---------------------------------------------------------------------------

class TestCliHelp:
    def test_help_loads(self):
        result = subprocess.run(
            CLI + ["--help"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        assert "search" in result.stdout
        assert "listings" in result.stdout
        assert "autocomplete" in result.stdout

    def test_search_help(self):
        result = subprocess.run(
            CLI + ["search", "stays", "--help"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        assert "--checkin" in result.stdout
        assert "--checkout" in result.stdout

    def test_version(self):
        result = subprocess.run(
            CLI + ["--version"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        assert "0.1.0" in result.stdout

    def test_listings_help(self):
        result = subprocess.run(
            CLI + ["listings", "get", "--help"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        assert "--json" in result.stdout


# ---------------------------------------------------------------------------
# Installed-binary subprocess tests (HARNESS checklist 5.5)
# ---------------------------------------------------------------------------


class TestCLISubprocess:
    """Tests that exercise the installed cli-web-airbnb binary directly."""

    def test_binary_resolves(self):
        """The installed CLI binary must be on PATH and exit 0 for --help."""
        result = subprocess.run(
            CLI + ["--help"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0, f"Binary failed: {result.stderr}"
        assert "cli-web-airbnb" in result.stdout.lower() or "search" in result.stdout

    def test_reviews_help(self):
        """listings reviews subcommand must be registered and return help."""
        result = subprocess.run(
            CLI + ["listings", "reviews", "--help"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        assert "--limit" in result.stdout
        assert "--sort" in result.stdout

    def test_availability_help(self):
        """listings availability subcommand must be registered and return help."""
        result = subprocess.run(
            CLI + ["listings", "availability", "--help"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        assert "--month" in result.stdout
        assert "--count" in result.stdout

    def test_reviews_returns_data(self):
        """listings reviews must return real review data for a known listing."""
        result = subprocess.run(
            CLI + ["--json", "listings", "reviews", "1603496841117193305"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["count"] > 0
        assert len(data["reviews"]) > 0
        review = data["reviews"][0]
        assert review["id"]
        assert review["rating"] is not None

    def test_availability_returns_data(self):
        """listings availability must return calendar data for a known listing."""
        result = subprocess.run(
            CLI + ["--json", "listings", "availability", "1603496841117193305"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert len(data["months"]) > 0
        month = data["months"][0]
        assert "month" in month
        assert "year" in month
        assert len(month["days"]) > 0
