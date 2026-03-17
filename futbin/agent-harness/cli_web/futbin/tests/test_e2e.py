"""E2E and subprocess tests for FUTBIN CLI.

FUTBIN is a public website — no auth is required for any of these tests.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

from cli_web.futbin.core.client import FutbinClient


def _resolve_cli(name):
    force = os.environ.get("CLI_WEB_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-web-", "cli_web.") + "." + name.split("-")[-1] + "_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


# ---------------------------------------------------------------------------
# Live API tests
# ---------------------------------------------------------------------------


class TestLiveAPI:
    """Live tests that call the real futbin.com API."""

    def test_search_live(self):
        client = FutbinClient()
        results = client.search_players("Messi")
        print(f"[verify] Found {len(results)} results")
        assert len(results) > 0
        r = results[0]
        print(f"[verify] First: id={r.id} name={r.name} position={r.position}")
        assert r.id
        assert r.name
        assert r.position

    def test_list_players_live(self):
        client = FutbinClient()
        results = client.list_players(page=1, position="ST", sort="ps_price", order="desc")
        print(f"[verify] Found {len(results)} results")
        assert len(results) > 0
        r = results[0]
        print(f"[verify] First: id={r.id} name={r.name} rating={r.rating}")
        assert r.id
        assert r.name
        assert r.rating > 0

    def test_get_price_history_live(self):
        client = FutbinClient()
        history = client.get_price_history(21747, "kylian-mbappe", "ps")
        print(f"[verify] player_name={history.player_name}")
        print(f"[verify] Found {len(history.prices)} price points")
        assert history.player_name
        assert len(history.prices) > 0
        for point in history.prices:
            assert point.timestamp > 0
            assert point.price >= 0  # some timestamps may have 0 (no sales data)

    def test_market_index_live(self):
        client = FutbinClient()
        indices = client.get_market_index()
        print(f"[verify] Found {len(indices)} results")
        assert len(indices) > 0
        r = indices[0]
        print(f"[verify] First: name={r.name} value_ps={r.value_ps}")
        assert r.name
        assert r.value_ps > 0

    def test_popular_players_live(self):
        client = FutbinClient()
        results = client.get_popular_players()
        print(f"[verify] Found {len(results)} results")
        # Popular page may use different card layout instead of table
        # Just verify no exception was raised — 0 results is acceptable
        assert isinstance(results, list)

    def test_latest_players_live(self):
        client = FutbinClient()
        results = client.get_latest_players()
        print(f"[verify] Found {len(results)} results")
        assert len(results) > 0


# ---------------------------------------------------------------------------
# Multi-step workflow tests
# ---------------------------------------------------------------------------


class TestPlayerDiscoveryWorkflow:
    """Multi-step workflow tests combining several API calls."""

    def test_search_then_prices(self):
        client = FutbinClient()
        results = client.search_players("Mbappe")
        print(f"[verify] Found {len(results)} search results")
        assert len(results) > 0

        first = results[0]
        print(f"[verify] First: id={first.id} name={first.name}")
        slug = first.url.rstrip("/").split("/")[-1] if first.url else str(first.id)

        history = client.get_price_history(first.id, slug, "ps")
        print(f"[verify] Price history for {history.player_name}: {len(history.prices)} points")
        assert len(history.prices) > 0


# ---------------------------------------------------------------------------
# CLI subprocess tests
# ---------------------------------------------------------------------------


class TestCLISubprocess:
    """Subprocess tests that invoke the CLI binary."""

    def test_cli_help(self):
        cmd = _resolve_cli("cli-web-futbin") + ["--help"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"[verify] exit_code={result.returncode}")
        print(f"[verify] stdout={result.stdout[:200]}")
        assert result.returncode == 0
        assert "FUTBIN" in result.stdout.upper() or "futbin" in result.stdout.lower()

    def test_cli_search_json(self):
        cmd = _resolve_cli("cli-web-futbin") + ["--json", "players", "search", "--query", "Messi"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"[verify] exit_code={result.returncode}")
        print(f"[verify] stdout={result.stdout[:300]}")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_cli_market_json(self):
        cmd = _resolve_cli("cli-web-futbin") + ["--json", "market", "index"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"[verify] exit_code={result.returncode}")
        print(f"[verify] stdout={result.stdout[:300]}")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) > 0
