"""Unit tests for FUTBIN CLI core modules."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli_web.futbin.core.client import FutbinClient, _parse_price
from cli_web.futbin.core.models import Player, PriceHistory, PricePoint


# ── Price parsing tests ──────────────────────────────────────────────────────


def test_parse_price_millions():
    assert _parse_price("2.73M") == 2730000


def test_parse_price_thousands():
    assert _parse_price("690K") == 690000


def test_parse_price_plain():
    assert _parse_price("3,600") == 3600


def test_parse_price_zero():
    assert _parse_price("0") == 0


def test_parse_price_dash():
    assert _parse_price("---") is None


def test_parse_price_empty():
    assert _parse_price("") is None


# ── Auth tests ───────────────────────────────────────────────────────────────


@pytest.fixture()
def _patch_auth_paths(tmp_path):
    """Patch AUTH_FILE and CONFIG_DIR to use a temporary directory."""
    auth_file = tmp_path / "auth.json"
    with (
        patch("cli_web.futbin.core.auth.AUTH_FILE", auth_file),
        patch("cli_web.futbin.core.auth.CONFIG_DIR", tmp_path),
    ):
        yield auth_file


@pytest.mark.usefixtures("_patch_auth_paths")
class TestAuth:
    def test_save_and_load_cookies(self):
        from cli_web.futbin.core.auth import load_cookies, save_cookies

        cookies = {"session_id": "abc123", "csrf": "xyz"}
        save_cookies(cookies)
        loaded = load_cookies()
        assert loaded == cookies

    def test_load_cookies_missing(self):
        from cli_web.futbin.core.auth import load_cookies

        assert load_cookies() is None

    def test_get_auth_status_no_cookies(self):
        from cli_web.futbin.core.auth import get_auth_status

        status = get_auth_status()
        assert status["authenticated"] is False

    def test_get_auth_status_with_cookies(self):
        from cli_web.futbin.core.auth import get_auth_status, save_cookies

        save_cookies({"token": "val"})
        status = get_auth_status()
        assert status["authenticated"] is True
        assert status["cookie_count"] == 1

    def test_clear_cookies(self):
        from cli_web.futbin.core.auth import clear_cookies, load_cookies, save_cookies

        save_cookies({"token": "val"})
        clear_cookies()
        assert load_cookies() is None


# ── Model tests ──────────────────────────────────────────────────────────────


def test_player_to_dict():
    player = Player(
        id=123,
        name="Messi",
        rating=97,
        position="RW",
        price_ps=2730000,
    )
    d = player.to_dict()
    assert d["id"] == 123
    assert d["name"] == "Messi"
    assert d["price_ps"] == 2730000
    # Fields that are None or empty string should be excluded
    assert "price_pc" not in d
    assert "club" not in d
    assert "slug" not in d


def test_price_history_to_dict():
    ph = PriceHistory(
        player_id=1,
        player_name="Ronaldo",
        platform="ps",
        prices=[
            PricePoint(timestamp=1000, price=500),
            PricePoint(timestamp=2000, price=600),
        ],
    )
    d = ph.to_dict()
    assert d["player_id"] == 1
    assert d["player_name"] == "Ronaldo"
    assert d["platform"] == "ps"
    assert len(d["prices"]) == 2
    assert d["prices"][0] == {"timestamp": 1000, "price": 500}
    assert d["prices"][1] == {"timestamp": 2000, "price": 600}


# ── Client search parsing test ───────────────────────────────────────────────


def test_search_players_mocked():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "id": 42,
            "name": "Mbappé",
            "position": "ST",
            "version": "TOTY",
            "ratingSquare": {"rating": "97"},
            "location": {"url": "/26/player/42/kylian-mbappe"},
        },
    ]

    client = FutbinClient()
    with patch.object(client, "_get", return_value=mock_response):
        results = client.search_players("Mbappé")

    assert len(results) == 1
    r = results[0]
    assert r.id == 42
    assert r.name == "Mbappé"
    assert r.position == "ST"
    assert r.version == "TOTY"
    assert r.rating == "97"
    assert r.url == "/26/player/42/kylian-mbappe"
    client.close()
