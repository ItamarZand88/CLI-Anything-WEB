"""E2E and subprocess tests for cli-web-tripadvisor.

E2E tests make real HTTP requests to TripAdvisor. They require internet access
and curl_cffi to be installed.

Subprocess tests verify the CLI entry point and --help output.

Set CLI_WEB_FORCE_INSTALLED=1 to use the installed binary instead of
the Python module runner.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_cli(*args: str) -> list[str]:
    """Return the command list to invoke the CLI."""
    if os.environ.get("CLI_WEB_FORCE_INSTALLED"):
        return ["cli-web-tripadvisor", *args]
    return [sys.executable, "-m", "cli_web.tripadvisor", *args]


def _run(*args: str, input_text: str | None = None) -> tuple[int, str, str]:
    """Run the CLI and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        _resolve_cli(*args),
        capture_output=True,
        text=True,
        input=input_text,
        timeout=60,
    )
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# Subprocess / --help tests (no network required)
# ---------------------------------------------------------------------------

class TestCLISubprocess:
    def test_help_loads(self):
        rc, out, err = _run("--help")
        assert rc == 0
        assert "tripadvisor" in out.lower()

    def test_version(self):
        rc, out, err = _run("--version")
        assert rc == 0
        assert "0.1.0" in out

    def test_locations_help(self):
        rc, out, err = _run("locations", "--help")
        assert rc == 0
        assert "search" in out.lower()

    def test_hotels_help(self):
        rc, out, err = _run("hotels", "--help")
        assert rc == 0
        assert "search" in out.lower()
        assert "get" in out.lower()

    def test_restaurants_help(self):
        rc, out, err = _run("restaurants", "--help")
        assert rc == 0
        assert "search" in out.lower()
        assert "get" in out.lower()

    def test_attractions_help(self):
        rc, out, err = _run("attractions", "--help")
        assert rc == 0
        assert "search" in out.lower()
        assert "get" in out.lower()

    def test_hotels_search_help(self):
        rc, out, err = _run("hotels", "search", "--help")
        assert rc == 0
        assert "--geo-id" in out
        assert "--page" in out
        assert "--json" in out

    def test_restaurants_search_help(self):
        rc, out, err = _run("restaurants", "search", "--help")
        assert rc == 0
        assert "--geo-id" in out
        assert "--page" in out
        assert "--json" in out

    def test_attractions_search_help(self):
        rc, out, err = _run("attractions", "search", "--help")
        assert rc == 0
        assert "--geo-id" in out
        assert "--page" in out
        assert "--json" in out


# ---------------------------------------------------------------------------
# Live E2E tests (require internet + curl_cffi)
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestLocationsSearchLive:
    def test_search_paris(self):
        rc, out, err = _run("locations", "search", "Paris", "--json")
        assert rc == 0
        data = json.loads(out)
        assert data["success"] is True
        assert data["count"] > 0
        locs = data["locations"]
        assert len(locs) > 0
        paris = next((l for l in locs if "187147" in l.get("geo_id", "")), None)
        assert paris is not None, "Expected Paris geo_id 187147 in results"

    def test_search_new_york(self):
        rc, out, err = _run("locations", "search", "New York", "--json")
        assert rc == 0
        data = json.loads(out)
        assert data["success"] is True
        # Should find NYC (60763) or New York state (28953)
        geo_ids = [l["geo_id"] for l in data["locations"]]
        assert "60763" in geo_ids or "28953" in geo_ids

    def test_search_returns_fields(self):
        rc, out, err = _run("locations", "search", "London", "--json")
        assert rc == 0
        data = json.loads(out)
        loc = data["locations"][0]
        assert "geo_id" in loc
        assert "name" in loc
        assert "url" in loc
        assert "type" in loc


@pytest.mark.e2e
class TestHotelsLive:
    GEO_ID = "187147"  # Paris

    def test_search_hotels_paris(self):
        rc, out, err = _run(
            "hotels", "search", "Paris",
            "--geo-id", self.GEO_ID,
            "--json",
        )
        assert rc == 0
        data = json.loads(out)
        assert data["success"] is True
        assert data["count"] > 0
        hotels = data["hotels"]
        assert len(hotels) > 0

    def test_hotel_fields_present(self):
        rc, out, err = _run(
            "hotels", "search", "Paris",
            "--geo-id", self.GEO_ID,
            "--json",
        )
        assert rc == 0
        data = json.loads(out)
        hotel = data["hotels"][0]
        # Must have all required fields (not missing/null for critical ones)
        assert "id" in hotel
        assert "name" in hotel
        assert hotel["name"]  # non-empty name
        assert "url" in hotel
        assert hotel["url"]   # non-empty URL
        assert "rating" in hotel
        assert "review_count" in hotel
        assert "price_range" in hotel
        assert "city" in hotel

    def test_hotel_url_format(self):
        rc, out, err = _run(
            "hotels", "search", "Paris",
            "--geo-id", self.GEO_ID,
            "--json",
        )
        assert rc == 0
        data = json.loads(out)
        for hotel in data["hotels"]:
            if hotel.get("url"):
                assert "tripadvisor.com" in hotel["url"]
                assert "Hotel_Review" in hotel["url"]


@pytest.mark.e2e
class TestRestaurantsLive:
    GEO_ID = "187147"  # Paris

    def test_search_restaurants_paris(self):
        rc, out, err = _run(
            "restaurants", "search", "Paris",
            "--geo-id", self.GEO_ID,
            "--json",
        )
        assert rc == 0
        data = json.loads(out)
        assert data["success"] is True
        assert data["count"] > 0

    def test_restaurant_fields_present(self):
        rc, out, err = _run(
            "restaurants", "search", "Paris",
            "--geo-id", self.GEO_ID,
            "--json",
        )
        assert rc == 0
        data = json.loads(out)
        rest = data["restaurants"][0]
        assert "id" in rest
        assert "name" in rest
        assert rest["name"]
        assert "url" in rest
        assert "rating" in rest
        assert "cuisines" in rest
        assert "price_range" in rest


@pytest.mark.e2e
class TestAttractionsLive:
    GEO_ID = "187147"  # Paris

    def test_search_attractions_paris(self):
        rc, out, err = _run(
            "attractions", "search", "Paris",
            "--geo-id", self.GEO_ID,
            "--json",
        )
        assert rc == 0
        data = json.loads(out)
        assert data["success"] is True
        assert data["count"] > 0

    def test_attraction_fields_present(self):
        rc, out, err = _run(
            "attractions", "search", "Paris",
            "--geo-id", self.GEO_ID,
            "--json",
        )
        assert rc == 0
        data = json.loads(out)
        attr = data["attractions"][0]
        assert "id" in attr
        assert "name" in attr
        assert attr["name"]
        assert "url" in attr
        assert "rating" in attr

    def test_eiffel_tower_in_results(self):
        """Eiffel Tower should appear somewhere in Paris attractions."""
        rc, out, err = _run(
            "attractions", "search", "Paris",
            "--geo-id", self.GEO_ID,
            "--json",
        )
        assert rc == 0
        data = json.loads(out)
        names = [a["name"].lower() for a in data["attractions"]]
        assert any("eiffel" in n for n in names), f"Eiffel Tower not found. Got: {names[:5]}"
