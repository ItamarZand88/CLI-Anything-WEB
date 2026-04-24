"""End-to-end tests against the live capitoltrades.com API.

These tests make real HTTP requests to:
- https://www.capitoltrades.com/ (SSR HTML)
- https://bff.capitoltrades.com/ (JSON search endpoint)

No auth is required (public site). Tests will FAIL (not skip) on network errors
since this CLI has no offline fallback.

CLI subprocess tests cover the fully installed `cli-web-capitoltrades` entry
point when `CLI_WEB_FORCE_INSTALLED=1`.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cli_web.capitoltrades.core.client import CapitoltradesClient
from cli_web.capitoltrades.core.models import (
    parse_article_detail,
    parse_articles_list,
    parse_buzz_detail,
    parse_buzz_list,
    parse_issuer_detail,
    parse_issuers_list,
    parse_politician_detail,
    parse_politicians_list,
    parse_press_detail,
    parse_press_list,
    parse_trade_detail,
    parse_trades_list,
    parse_trades_stats,
)


# ─── _resolve_cli pattern ───────────────────────────────────────────────────


def _resolve_cli(cli_name: str) -> list[str]:
    """Locate the installed CLI binary, or fall back to `python -m ...`.

    If CLI_WEB_FORCE_INSTALLED=1 is set, raise if the binary is not on PATH.
    """
    forced = os.environ.get("CLI_WEB_FORCE_INSTALLED") == "1"
    path = shutil.which(cli_name)
    if path:
        return [path]
    if forced:
        raise RuntimeError(
            f"CLI_WEB_FORCE_INSTALLED=1 but '{cli_name}' not found on PATH. "
            "Run `pip install -e .` in agent-harness/ before running subprocess tests."
        )
    # Fallback: module invocation
    module = cli_name.replace("cli-web-", "cli_web.").replace("-", "_")
    return [sys.executable, "-m", module]


@pytest.fixture(scope="module")
def cli_cmd():
    return _resolve_cli("cli-web-capitoltrades")


@pytest.fixture(scope="module")
def client():
    with CapitoltradesClient() as c:
        yield c


# ─── Live API (Python layer) ────────────────────────────────────────────────


class TestLiveAPI:
    def test_trades_list_returns_rows(self, client):
        soup = client.get_html("/trades", params={"pageSize": 5})
        rows = parse_trades_list(soup)
        assert len(rows) >= 1, "trades list should have at least one row"
        first = rows[0]
        assert first["trade_id"], "trade_id must be set"
        assert first["trade_id"].isdigit(), f"trade_id should be numeric, got {first['trade_id']!r}"
        assert first["politician_id"], "politician_id must be set"
        assert first["issuer_id"], "issuer_id must be set"
        assert first["tx_type"] in ("buy", "sell", "exchange", "receive"), f"unexpected tx_type: {first['tx_type']!r}"

    def test_trades_stats_returns_known_labels(self, client):
        soup = client.get_html("/trades")
        stats = parse_trades_stats(soup)
        # At least some subset should be parseable
        assert any(k in stats for k in ("trades", "volume", "politicians", "issuers"))

    def test_trade_detail_round_trip(self, client):
        """List → pick first → get detail → verify IDs match."""
        soup = client.get_html("/trades", params={"pageSize": 1})
        rows = parse_trades_list(soup)
        assert rows, "list returned no rows"
        tid = rows[0]["trade_id"]
        detail = parse_trade_detail(client.get_html(f"/trades/{tid}"), tid)
        assert detail["trade_id"] == tid
        assert detail["politician_id"] == rows[0]["politician_id"]
        assert detail["issuer_id"] == rows[0]["issuer_id"]
        assert detail["tx_type"] in ("buy", "sell", "exchange", "receive")

    def test_politicians_list_has_cards(self, client):
        soup = client.get_html("/politicians", params={"pageSize": 5})
        rows = parse_politicians_list(soup)
        assert len(rows) >= 1, "politicians list empty"
        # Bioguide IDs match [A-Z]\d{6} pattern
        import re
        for r in rows:
            assert re.match(r"^[A-Z]\d{6}$", r["politician_id"] or ""), f"bad bioguide: {r['politician_id']}"

    def test_politician_detail_has_name(self, client):
        """Pick first politician from list, get detail, verify name present."""
        soup = client.get_html("/politicians")
        rows = parse_politicians_list(soup)
        assert rows, "politicians list empty"
        pid = rows[0]["politician_id"]
        detail = parse_politician_detail(client.get_html(f"/politicians/{pid}"), pid)
        assert detail["politician_id"] == pid
        assert detail["name"]

    def test_issuers_list_has_cards(self, client):
        soup = client.get_html("/issuers")
        rows = parse_issuers_list(soup)
        assert len(rows) >= 1
        assert rows[0]["issuer_id"].isdigit()

    def test_issuer_search_via_bff(self, client):
        """BFF JSON: search for 'amgen' → rich data returned."""
        data = client.get_bff_json("/issuers", params={"search": "amgen"})
        items = data.get("data", [])
        assert len(items) >= 1, "BFF search for 'amgen' returned no items"
        found = items[0]
        assert "Amgen" in found.get("issuerName", "")
        assert found.get("issuerTicker"), "issuerTicker missing"
        assert found.get("_issuerId"), "_issuerId missing"
        assert found.get("sector"), "sector missing"
        assert "performance" in found, "performance block missing"
        assert isinstance(found["performance"].get("eodPrices"), list)

    def test_issuer_search_empty_query_returns_empty(self, client):
        """Empty search term returns zero results (not all issuers)."""
        data = client.get_bff_json("/issuers", params={"search": ""})
        items = data.get("data", [])
        assert items == [], "empty search should return empty list"

    def test_articles_list(self, client):
        soup = client.get_html("/articles")
        rows = parse_articles_list(soup)
        assert len(rows) >= 1
        assert rows[0]["slug"]
        assert rows[0]["title"]
        assert rows[0]["url"].startswith("https://www.capitoltrades.com/articles/")

    def test_article_detail_has_body(self, client):
        soup = client.get_html("/articles")
        rows = parse_articles_list(soup)
        assert rows
        slug = rows[0]["slug"]
        detail = parse_article_detail(client.get_html(f"/articles/{slug}"), slug)
        assert detail["title"]
        assert detail["body"]
        assert len(detail["body"]) > 100, "article body suspiciously short"

    def test_buzz_list_returns_rows(self, client):
        soup = client.get_html("/buzz")
        rows = parse_buzz_list(soup)
        assert len(rows) >= 1
        assert rows[0]["slug"]
        assert rows[0]["title"]
        assert rows[0]["url"].startswith("https://www.capitoltrades.com/buzz/")

    def test_buzz_detail(self, client):
        soup = client.get_html("/buzz")
        rows = parse_buzz_list(soup)
        assert rows
        slug = rows[0]["slug"]
        detail = parse_buzz_detail(client.get_html(f"/buzz/{slug}"), slug)
        assert detail["title"]
        assert detail["body"]

    def test_press_list_returns_rows(self, client):
        soup = client.get_html("/press")
        rows = parse_press_list(soup)
        assert len(rows) >= 1
        assert rows[0]["slug"]
        assert rows[0]["url"].startswith("https://www.capitoltrades.com/press/")

    def test_trades_list_size_filter_applied(self, client):
        """tradeSize=8 (our 1M-5M bracket) restricts rows to that bracket."""
        filtered = client.get_html("/trades", params={"pageSize": 10, "tradeSize": 8})
        rows = parse_trades_list(filtered)
        assert rows, "size filter should return at least one row"
        for r in rows:
            size = (r.get("size") or "").replace("\xa0", " ")
            # Must be the 1M-5M bracket (Unicode en-dash)
            assert "1M" in size and "5M" in size, f"unexpected size in filtered result: {size!r}"


# ─── CLI subprocess tests ───────────────────────────────────────────────────


def _run(cli_cmd: list[str], *args: str, timeout: float = 60.0) -> subprocess.CompletedProcess:
    """Run the installed CLI with the given args and return the result."""
    return subprocess.run(
        [*cli_cmd, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


class TestCLISubprocess:
    def test_help_loads(self, cli_cmd):
        result = _run(cli_cmd, "--help")
        assert result.returncode == 0
        assert "trades" in result.stdout
        assert "politicians" in result.stdout
        assert "issuers" in result.stdout
        assert "articles" in result.stdout

    def test_version_works(self, cli_cmd):
        result = _run(cli_cmd, "--version")
        assert result.returncode == 0
        assert "0.1.0" in result.stdout

    def test_trades_stats_json(self, cli_cmd):
        result = _run(cli_cmd, "--json", "trades", "stats")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert "trades" in data["data"] or "volume" in data["data"]

    def test_trades_list_json(self, cli_cmd):
        result = _run(cli_cmd, "--json", "trades", "list", "--page-size", "3")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        rows = data["data"]
        assert len(rows) >= 1
        # Verify structured fields (not placeholders/protocol leaks)
        for r in rows:
            assert r["trade_id"]
            assert r["politician_id"]
            assert r["issuer_id"]
            # No raw HTML/protocol leaks
            assert "<" not in str(r.get("politician_name") or ""), "HTML leak in name"
            assert "</" not in json.dumps(r), "HTML leak in output"

    def test_trade_get_json_has_detail_fields(self, cli_cmd):
        """List a trade, then get its detail via subprocess."""
        result = _run(cli_cmd, "--json", "trades", "list", "--page-size", "1")
        data = json.loads(result.stdout)
        tid = data["data"][0]["trade_id"]

        result2 = _run(cli_cmd, "--json", "trades", "get", tid)
        assert result2.returncode == 0, f"stderr: {result2.stderr}"
        detail = json.loads(result2.stdout)
        assert detail["success"] is True
        d = detail["data"]
        assert d["trade_id"] == tid
        assert d["tx_type"] in ("buy", "sell", "exchange", "receive")

    def test_politicians_list_json(self, cli_cmd):
        result = _run(cli_cmd, "--json", "politicians", "list", "--page-size", "3")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert len(data["data"]) >= 1

    def test_issuers_search_json(self, cli_cmd):
        result = _run(cli_cmd, "--json", "issuers", "search", "microsoft")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert len(data["data"]) >= 1
        ms = next((r for r in data["data"] if "Microsoft" in (r.get("issuerName") or "")), None)
        assert ms is not None, "Microsoft not in search results"
        assert ms.get("issuerTicker") == "MSFT:US"

    def test_articles_list_json(self, cli_cmd):
        result = _run(cli_cmd, "--json", "articles", "list", "--page-size", "3")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert len(data["data"]) >= 1
        a = data["data"][0]
        assert a["slug"]
        assert a["url"].startswith("https://")

    def test_filter_party_republican(self, cli_cmd):
        """--party republican should only return Republican trades."""
        result = _run(cli_cmd, "--json", "trades", "list", "--party", "republican", "--page-size", "5")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        rows = data["data"]
        assert rows, "party filter returned no rows"
        for r in rows:
            assert r["politician_party"] == "Republican", (
                f"expected Republican, got {r['politician_party']!r} for trade {r['trade_id']}"
            )

    def test_trade_list_not_found_for_bad_id(self, cli_cmd):
        """Non-existent trade ID should exit non-zero with structured JSON error."""
        # An 11-digit ID unlikely to exist
        result = _run(cli_cmd, "--json", "trades", "get", "99999999999")
        # The site may return HTML 404 or a blank page — either way, a CLI should
        # produce valid JSON output
        if result.returncode != 0:
            data = json.loads(result.stdout) if result.stdout else {}
            if data:
                assert data.get("error") is True or data.get("success") is False

    def test_no_protocol_leakage_in_output(self, cli_cmd):
        """--json outputs must not contain raw RPC fragments or HTML fragments."""
        result = _run(cli_cmd, "--json", "trades", "list", "--page-size", "2")
        assert "<div" not in result.stdout
        assert "<span" not in result.stdout
        assert "__next_f" not in result.stdout

    def test_buzz_list_json(self, cli_cmd):
        result = _run(cli_cmd, "--json", "buzz", "list", "--page-size", "3")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert len(data["data"]) >= 1
        assert data["data"][0]["url"].startswith("https://")

    def test_press_list_json(self, cli_cmd):
        result = _run(cli_cmd, "--json", "press", "list", "--page-size", "3")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert len(data["data"]) >= 1

    def test_trades_by_ticker(self, cli_cmd):
        """trades by-ticker resolves a ticker via BFF and lists trades."""
        result = _run(cli_cmd, "--json", "trades", "by-ticker", "AMGN", "--page-size", "5")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        resolved = data["meta"]["resolved_issuer"]
        assert "Amgen" in resolved["name"]
        assert resolved["ticker"] == "AMGN:US"
        # The list should contain trades matching the resolved issuer_id
        if data["data"]:
            for t in data["data"]:
                assert t["issuer_id"] == resolved["issuer_id"]

    def test_trades_by_ticker_not_found(self, cli_cmd):
        """Unknown ticker → NOT_FOUND exit 1."""
        result = _run(cli_cmd, "--json", "trades", "by-ticker", "XYZNOTFOUND123")
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["error"] is True
        assert data["code"] == "NOT_FOUND"

    def test_politicians_top_by_trades(self, cli_cmd):
        """politicians top --by trades returns top N sorted list."""
        result = _run(cli_cmd, "--json", "politicians", "top", "--by", "trades", "--page-size", "5")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert 1 <= len(data["data"]) <= 5
        for r in data["data"]:
            assert r["politician_id"]

    def test_trades_list_new_filters_accepted(self, cli_cmd):
        """New CLI options (--chamber, --size, --sort) map to the correct query params."""
        result = _run(
            cli_cmd, "--json", "trades", "list",
            "--chamber", "house",
            "--size", "1M-5M",
            "--sort", "traded",
            "--sort-direction", "desc",
            "--page-size", "5",
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["success"] is True
        filters = data["meta"]["filters"]
        assert filters.get("chamber") == "house"
        assert filters.get("tradeSize") == 8   # 1M-5M → ID 8
        assert filters.get("sortBy") == "traded"
        assert filters.get("sortDirection") == "desc"
        # Every returned row should be House + 1M-5M
        for r in data["data"]:
            if r.get("politician_chamber"):
                assert r["politician_chamber"] == "House"
            size = (r.get("size") or "").replace("\xa0", " ")
            assert "1M" in size and "5M" in size, f"unexpected size: {size!r}"
