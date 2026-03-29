"""E2E and CLI subprocess tests for cli-web-futbin.

Live tests make real API calls to https://www.futbin.com
CLI subprocess tests use the installed `cli-web-futbin` binary.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

# ── CLI subprocess helper ─────────────────────────────────────────────────────

def _resolve_cli(name: str) -> list[str]:
    """Resolve CLI binary, supporting CLI_WEB_FORCE_INSTALLED=1 for CI."""
    if os.environ.get("CLI_WEB_FORCE_INSTALLED"):
        found = shutil.which(name)
        if found:
            return [found]
        # Fall back to python -m
        pkg = name.replace("cli-web-", "cli_web.").replace("-", "_")
        return [sys.executable, "-m", pkg]

    # Development: use python -m
    pkg = "cli_web.futbin"
    return [sys.executable, "-m", pkg]


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    cmd = _resolve_cli("cli-web-futbin") + list(args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=check,
        timeout=30,
        encoding="utf-8",
        errors="replace",
    )


# ── CLI Subprocess Tests ──────────────────────────────────────────────────────

def test_cli_help():
    result = _run("--help")
    assert result.returncode == 0
    assert "futbin" in result.stdout.lower() or "players" in result.stdout.lower()


def test_cli_version():
    result = _run("--version")
    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_cli_players_search_json():
    result = _run("players", "search", "--name", "Mbappe", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) >= 1
    player = data[0]
    assert "id" in player
    assert "name" in player
    assert "rating" in player
    assert "Mbapp" in player["name"] or "mbappe" in player["name"].lower()


def test_cli_market_index_json():
    result = _run("market", "index", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) >= 1
    item = data[0]
    assert "name" in item
    assert "last" in item


def test_cli_sbc_list_json():
    result = _run("sbc", "list", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)


def test_cli_evolutions_list_json():
    result = _run("evolutions", "list", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)


# ── Live API Tests ────────────────────────────────────────────────────────────

def test_players_search_live():
    from cli_web.futbin.core.client import FutbinClient
    with FutbinClient() as client:
        results = client.search_players("Mbappe", year=26)
    assert len(results) >= 1
    assert any("Mbapp" in p.name for p in results)
    # Verify model fields
    p = results[0]
    assert p.id > 0
    assert p.rating > 0
    assert p.position != ""


def test_players_search_returns_player_model():
    from cli_web.futbin.core.client import FutbinClient
    from cli_web.futbin.core.models import Player
    with FutbinClient() as client:
        results = client.search_players("Salah", year=26)
    assert len(results) >= 1
    assert all(isinstance(p, Player) for p in results)


def test_market_index_live():
    from cli_web.futbin.core.client import FutbinClient
    with FutbinClient() as client:
        items = client.get_market_index()
    assert len(items) >= 1
    item = items[0]
    assert item.name != ""
    # Verify JSON serializable
    d = item.to_dict()
    assert "name" in d
    assert "last" in d
    assert "change_pct" in d


def test_sbc_list_live():
    from cli_web.futbin.core.client import FutbinClient
    with FutbinClient() as client:
        sbcs = client.list_sbcs()
    # SBCs may be empty if none active, but should not error
    assert isinstance(sbcs, list)


def test_evolutions_list_live():
    from cli_web.futbin.core.client import FutbinClient
    with FutbinClient() as client:
        evos = client.list_evolutions()
    assert isinstance(evos, list)
    assert len(evos) >= 1


def test_player_search_json_output():
    """Verify JSON output is fully serializable."""
    from cli_web.futbin.core.client import FutbinClient
    import json as _json
    with FutbinClient() as client:
        results = client.search_players("Ronaldo", year=26)
    data = [p.to_dict() for p in results]
    # Should not raise
    serialized = _json.dumps(data)
    parsed = _json.loads(serialized)
    assert isinstance(parsed, list)


# ── Filter Tests ─────────────────────────────────────────────────────────────

def test_list_players_position_filter():
    """Verify position filter is passed to FUTBIN and returns results."""
    from cli_web.futbin.core.client import FutbinClient
    with FutbinClient() as client:
        results, has_next = client.list_players(position="GK", sort="overall", order="desc")
    assert isinstance(results, list)
    assert isinstance(has_next, bool)


def test_list_players_rating_filter():
    """Verify rating range filter returns results."""
    from cli_web.futbin.core.client import FutbinClient
    with FutbinClient() as client:
        results, has_next = client.list_players(rating_min=90, rating_max=99, sort="overall", order="desc")
    assert isinstance(results, list)
    assert isinstance(has_next, bool)


def test_list_players_version_filter():
    """Verify version filter returns results."""
    from cli_web.futbin.core.client import FutbinClient
    with FutbinClient() as client:
        results, has_next = client.list_players(version="toty", sort="overall", order="desc")
    assert isinstance(results, list)
    assert isinstance(has_next, bool)


def test_list_players_cheapest():
    """Verify cheapest flag (sort=ps_price asc) returns results."""
    from cli_web.futbin.core.client import FutbinClient
    with FutbinClient() as client:
        results, has_next = client.list_players(
            position="ST", version="gold_rare", sort="ps_price", order="asc"
        )
    assert isinstance(results, list)
    assert isinstance(has_next, bool)


def test_cli_list_players_filters_json():
    """CLI: players list with position, rating filters returns valid JSON."""
    result = _run(
        "players", "list",
        "--position", "CAM",
        "--rating-min", "85",
        "--json",
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    assert "players" in data
    assert isinstance(data["players"], list)


def test_cli_list_players_cheapest():
    """CLI: players list --cheapest returns valid JSON."""
    result = _run(
        "players", "list",
        "--position", "GK",
        "--cheapest",
        "--json",
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    assert "players" in data
    assert isinstance(data["players"], list)


# ── New Market Commands ──────────────────────────────────────────────────────

def test_cli_market_popular_json():
    """CLI: market popular returns valid JSON with player data."""
    result = _run("market", "popular", "--limit", "5", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) > 0
    assert "id" in data[0]
    assert "name" in data[0]
    assert "rating" in data[0]


def test_cli_market_latest_json():
    """CLI: market latest returns valid JSON with player list."""
    result = _run("market", "latest", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    assert "players" in data
    assert isinstance(data["players"], list)
    assert len(data["players"]) > 0


def test_cli_market_cheapest_json():
    """CLI: market cheapest returns valid JSON with cheapest players."""
    result = _run("market", "cheapest", "--rating-min", "88", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    assert "players" in data
    assert len(data["players"]) > 0
    for p in data["players"]:
        assert p["rating"] >= 88


def test_cli_players_price_history_json():
    """CLI: players price-history returns valid JSON with price data."""
    result = _run("players", "price-history", "40", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "player_id" in data
    assert data["player_id"] == 40
    assert "ps_prices" in data
    assert isinstance(data["ps_prices"], list)
    assert len(data["ps_prices"]) > 0
    assert len(data["ps_prices"][0]) == 2


# ── Live API tests for new features ─────────────────────────────────────────

def test_popular_players_live():
    """Live: get_popular_players returns player models."""
    from cli_web.futbin.core.client import FutbinClient
    with FutbinClient() as client:
        players = client.get_popular_players(limit=5)
    assert isinstance(players, list)
    assert len(players) > 0
    p = players[0]
    assert p.id > 0
    assert p.name
    assert p.rating > 0


def test_latest_players_live():
    """Live: get_latest_players returns player models."""
    from cli_web.futbin.core.client import FutbinClient
    with FutbinClient() as client:
        players, has_next = client.get_latest_players()
    assert isinstance(players, list)
    assert len(players) > 0
    assert isinstance(has_next, bool)


def test_price_history_live():
    """Live: get_price_history returns PriceHistory model."""
    from cli_web.futbin.core.client import FutbinClient
    with FutbinClient() as client:
        history = client.get_price_history(40)  # Mbappé
    assert history.player_id == 40
    assert len(history.ps_prices) > 0
    d = history.to_dict()
    assert d["ps_current"] is not None
    assert d["ps_min"] is not None
    assert d["data_points"] > 0


# ── SBC Fodder + Market Movers ───────────────────────────────────────────────

def test_cli_market_fodder_json():
    """CLI: market fodder returns valid JSON with rating tiers."""
    result = _run("market", "fodder", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) > 0
    tier = data[0]
    assert "rating" in tier
    assert "cheapest_price" in tier
    assert "players" in tier
    assert len(tier["players"]) > 0


def test_cli_market_movers_json():
    """CLI: market movers returns valid JSON with risers."""
    result = _run("market", "movers", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    assert "players" in data
    assert data["direction"] == "risers"


def test_cli_market_movers_fallers_json():
    """CLI: market movers --fallers returns fallers."""
    result = _run("market", "movers", "--fallers", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["direction"] == "fallers"


def test_sbc_fodder_live():
    """Live: get_sbc_fodder returns FodderTier models."""
    from cli_web.futbin.core.client import FutbinClient
    with FutbinClient() as client:
        tiers = client.get_sbc_fodder()
    assert isinstance(tiers, list)
    assert len(tiers) > 0
    t = tiers[0]
    assert t.rating >= 81
    assert len(t.players) > 0
    assert t.players[0].name
    assert t.players[0].price


def test_market_movers_live():
    """Live: get_market_movers returns player list."""
    from cli_web.futbin.core.client import FutbinClient
    with FutbinClient() as client:
        players, has_next = client.get_market_movers(direction="risers")
    assert isinstance(players, list)
    assert len(players) > 0
    assert isinstance(has_next, bool)
