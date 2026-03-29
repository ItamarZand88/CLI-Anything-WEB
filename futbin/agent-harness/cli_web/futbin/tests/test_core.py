"""Unit tests for cli-web-futbin core — mocked HTTP, no network."""
import json
from unittest.mock import MagicMock, patch

import pytest

from cli_web.futbin.core.client import FutbinClient, _coin_str_to_int
from cli_web.futbin.core.models import Player, MarketItem


# ── Coin string parsing ───────────────────────────────────────────────────────

@pytest.mark.parametrize("value,expected", [
    ("150K", 150_000),
    ("1.2M", 1_200_000),
    ("1,234", 1_234),
    ("500", 500),
    ("", None),
    (None, None),
    ("N/A", None),
])
def test_coin_str_to_int(value, expected):
    assert _coin_str_to_int(value) == expected


# ── Player search JSON parsing ────────────────────────────────────────────────

PLAYER_SEARCH_JSON = [
    {
        "id": 40,
        "name": "Kylian Mbappé",
        "position": "ST",
        "version": "Normal",
        "location": {"type": "futbin.frontenddata.Location.LocationDontUseThisDirectly",
                     "url": "/26/player/40/kylian-mbappe"},
        "clubImage": {"fixed": {"type": "...", "name": "Real Madrid", "url": {}}},
        "nationImage": {"fixed": {"type": "...", "name": "France", "url": {}}},
        "playerImage": {"fixed": {"url": {}}},
        "ratingSquare": {"type": "...", "rating": "91", "color": "#gold"},
    }
]


def _mock_response(json_data=None, text="", status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


@patch("cli_web.futbin.core.client.httpx.Client")
def test_parse_player_search(mock_httpx_class):
    mock_client = MagicMock()
    mock_httpx_class.return_value.__enter__ = MagicMock(return_value=mock_client)
    mock_httpx_class.return_value.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = _mock_response(json_data=PLAYER_SEARCH_JSON)

    client = FutbinClient()
    client._client = mock_client

    results = client.search_players("Mbappe", year=26)

    assert len(results) == 1
    p = results[0]
    assert p.id == 40
    assert "Mbapp" in p.name
    assert p.position == "ST"
    assert p.version == "Normal"
    assert p.rating == 91
    assert p.club == "Real Madrid"
    assert p.nation == "France"
    assert p.year == 26
    assert "kylian-mbappe" in p.url


@patch("cli_web.futbin.core.client.httpx.Client")
def test_parse_player_search_empty(mock_httpx_class):
    mock_client = MagicMock()
    mock_httpx_class.return_value.__enter__ = MagicMock(return_value=mock_client)
    mock_httpx_class.return_value.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = _mock_response(json_data=[])

    client = FutbinClient()
    client._client = mock_client

    results = client.search_players("xyznotaplayer")
    assert results == []


# ── Market index HTML parsing ─────────────────────────────────────────────────

MARKET_INDEX_HTML = """
<table>
  <thead><tr><th>Name</th><th>Last</th><th>Change %</th></tr></thead>
  <tbody>
    <tr>
      <td><a href="/market">Gold Players</a></td>
      <td>150K</td>
      <td>+2.5%</td>
    </tr>
    <tr>
      <td><a href="/market">Silver Players</a></td>
      <td>5K</td>
      <td>-1.0%</td>
    </tr>
  </tbody>
</table>
"""


@patch("cli_web.futbin.core.client.httpx.Client")
def test_parse_market_index(mock_httpx_class):
    mock_client = MagicMock()
    mock_httpx_class.return_value.__enter__ = MagicMock(return_value=mock_client)
    mock_httpx_class.return_value.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = _mock_response(text=MARKET_INDEX_HTML)

    client = FutbinClient()
    client._client = mock_client

    items = client.get_market_index()
    assert len(items) >= 1
    first = items[0]
    assert isinstance(first, MarketItem)
    assert first.name != ""
    assert first.last != ""


# ── SBC list HTML parsing ─────────────────────────────────────────────────────

SBC_LIST_HTML = """
<html><body>
<div class="og-card-wrapper border-box s-column sbc-card-wrapper">
  <a class="s-column" href="/26/squad-building-challenge/665">
    <div class="og-card-wrapper-top flex space-between align-center">
      <div class="text-ellipsis bold xs-row">
        <div class="text-ellipsis">Kingsley Coman</div>
        <div class="sbc-badge positive">New</div>
      </div>
    </div>
  </a>
  <span class="sbc-rewards-area">Coman 88</span>
  <span>Expires 6 days Repeatable Completed 0 / 2 62.6K 67.7K</span>
</div>
<div class="og-card-wrapper border-box s-column sbc-card-wrapper">
  <a class="s-column" href="/26/squad-building-challenge/666">
    <div class="og-card-wrapper-top flex space-between align-center">
      <div class="text-ellipsis bold xs-row">
        <div class="text-ellipsis">Generic SBC</div>
      </div>
    </div>
  </a>
  <span>Expires 3 days</span>
</div>
</body></html>
"""


@patch("cli_web.futbin.core.client.httpx.Client")
def test_parse_sbc_list(mock_httpx_class):
    mock_client = MagicMock()
    mock_httpx_class.return_value.__enter__ = MagicMock(return_value=mock_client)
    mock_httpx_class.return_value.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = _mock_response(text=SBC_LIST_HTML)

    client = FutbinClient()
    client._client = mock_client

    sbcs = client.list_sbcs()
    assert len(sbcs) >= 1
    assert sbcs[0].id == 665


# ── Evolution list HTML parsing ───────────────────────────────────────────────

EVOLUTIONS_HTML = """
<html><body>
<div class="evolutions-overview-wrapper s-column m-border-radius relative border-box" data-filter-search-key="ucl specialist">
  <a class="evolutions-card-top row space-between" href="/evolutions/666/ucl-specialist">
    <div class="xs-row align-center">
      <div class="xs-font text-center">UCL Specialist</div>
    </div>
    <div class="xs-row justify-end flex-wrap">
      <div class="evolution-badge xxs-font uppercase">Evolutions</div>
      <div class="evolution-badge bold positive xxs-font uppercase">New</div>
    </div>
  </a>
  <span>EXPIRES 2 Weeks UNLOCK 1 Weeks Free Repeatable 2</span>
</div>
<div class="evolutions-overview-wrapper s-column m-border-radius relative border-box" data-filter-search-key="sprint master">
  <a class="evolutions-card-top row space-between" href="/evolutions/667/sprint-master">
    <div class="xs-row align-center">
      <div class="xs-font text-center">Sprint Master</div>
    </div>
    <div class="xs-row justify-end flex-wrap">
      <div class="evolution-badge xxs-font uppercase">Rewards</div>
    </div>
  </a>
  <span>EXPIRES 5 days</span>
</div>
</body></html>
"""


@patch("cli_web.futbin.core.client.httpx.Client")
def test_parse_evolution_list(mock_httpx_class):
    mock_client = MagicMock()
    mock_httpx_class.return_value.__enter__ = MagicMock(return_value=mock_client)
    mock_httpx_class.return_value.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = _mock_response(text=EVOLUTIONS_HTML)

    client = FutbinClient()
    client._client = mock_client

    evos = client.list_evolutions()
    assert len(evos) >= 1
    assert evos[0].id == 666
    assert "UCL" in evos[0].name or "Ucl" in evos[0].name


# ── Model serialization ───────────────────────────────────────────────────────

def test_player_to_dict():
    p = Player(
        id=40,
        name="Test Player",
        position="ST",
        version="Normal",
        rating=85,
        club="Test FC",
        nation="England",
        year=26,
        url="/26/player/40/test-player",
        ps_price=100_000,
        xbox_price=95_000,
        stats={"pac": 90, "sho": 85},
    )
    d = p.to_dict()
    assert d["id"] == 40
    assert d["ps_price"] == 100_000
    assert d["stats"]["pac"] == 90
    assert "futbin.com" in d["url"]


# ===========================================================================
# Exception hierarchy tests
# ===========================================================================

from cli_web.futbin.core.exceptions import (
    FutbinError, AuthError, NetworkError, RateLimitError,
    ParsingError, NotFoundError, ServerError, InvalidInputError,
    error_code_for,
)


def test_all_exceptions_inherit_from_base():
    for cls in (AuthError, NetworkError, RateLimitError, ParsingError,
                NotFoundError, ServerError, InvalidInputError):
        assert issubclass(cls, FutbinError), f"{cls.__name__} not subclass of FutbinError"


def test_error_code_mapping():
    assert error_code_for(AuthError("x")) == "AUTH_ERROR"
    assert error_code_for(RateLimitError("x")) == "RATE_LIMITED"
    assert error_code_for(NotFoundError("x")) == "NOT_FOUND"
    assert error_code_for(ServerError("x")) == "SERVER_ERROR"
    assert error_code_for(NetworkError("x")) == "NETWORK_ERROR"
    assert error_code_for(ParsingError("x")) == "PARSING_ERROR"
    assert error_code_for(InvalidInputError("x")) == "INVALID_INPUT"
    assert error_code_for(Exception("x")) == "UNKNOWN_ERROR"


def test_rate_limit_error_retry_after():
    e = RateLimitError("slow", retry_after=60.0)
    assert e.retry_after == 60.0
    e2 = RateLimitError("slow")
    assert e2.retry_after is None


def test_server_error_status_code():
    e = ServerError("bad", status_code=502)
    assert e.status_code == 502


# ===========================================================================
# Helpers tests
# ===========================================================================

import click
from pathlib import Path
from unittest.mock import patch as mock_patch


def test_resolve_partial_id_exact():
    from cli_web.futbin.utils.helpers import resolve_partial_id

    class Item:
        def __init__(self, id, name=""):
            self.id = id; self.name = name

    items = [Item(123, "Alice"), Item(456, "Bob"), Item(789, "Carol")]
    result = resolve_partial_id("456", items, kind="player")
    assert result.name == "Bob"


def test_resolve_partial_id_prefix():
    from cli_web.futbin.utils.helpers import resolve_partial_id

    class Item:
        def __init__(self, id, name=""):
            self.id = id; self.name = name

    items = [Item(1230, "Alice"), Item(4560, "Bob"), Item(7890, "Carol")]
    result = resolve_partial_id("78", items, kind="player")
    assert result.name == "Carol"


def test_resolve_partial_id_no_match():
    from cli_web.futbin.utils.helpers import resolve_partial_id

    class Item:
        def __init__(self, id, name=""):
            self.id = id; self.name = name

    items = [Item(123, "Alice")]
    with pytest.raises(click.BadParameter):
        resolve_partial_id("999", items, kind="player")


def test_sanitize_filename():
    from cli_web.futbin.utils.helpers import sanitize_filename
    assert sanitize_filename('test/file:name*') == "test_file_name_"
    assert sanitize_filename("") == "untitled"
    assert sanitize_filename("   ") == "untitled"
    assert len(sanitize_filename("a" * 300)) == 240


def test_handle_errors_app_error_exits_1():
    from cli_web.futbin.utils.helpers import handle_errors
    with pytest.raises(SystemExit) as exc:
        with handle_errors():
            raise NotFoundError("not found")
    assert exc.value.code == 1


def test_handle_errors_generic_exits_2():
    from cli_web.futbin.utils.helpers import handle_errors
    with pytest.raises(SystemExit) as exc:
        with handle_errors():
            raise ValueError("bug")
    assert exc.value.code == 2


def test_handle_errors_json_mode():
    from cli_web.futbin.utils.helpers import handle_errors
    import io
    captured = io.StringIO()
    with pytest.raises(SystemExit):
        with mock_patch("click.echo", side_effect=lambda msg, **kw: captured.write(str(msg))):
            with handle_errors(json_mode=True):
                raise NotFoundError("player 123 not found")
    data = json.loads(captured.getvalue())
    assert data["error"] is True
    assert data["code"] == "NOT_FOUND"


def test_persistent_config():
    from cli_web.futbin.utils.helpers import (
        get_config_value, set_config_value, clear_config,
    )
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_file = Path(tmp) / "config.json"
        with mock_patch("cli_web.futbin.utils.helpers.CONFIG_FILE", tmp_file), \
             mock_patch("cli_web.futbin.utils.helpers.CONFIG_DIR", Path(tmp)):
            set_config_value("year", 25)
            assert get_config_value("year") == 25
            set_config_value("platform", "pc")
            assert get_config_value("platform") == "pc"
            clear_config()
            assert get_config_value("year") is None


def test_require_year_default():
    from cli_web.futbin.utils.helpers import require_year
    assert require_year(25) == 25
    assert require_year(None) == 26  # default


# ===========================================================================
# Model enum tests
# ===========================================================================

from cli_web.futbin.core.models import (
    Position, Platform, SBCDetail, EvolutionDetail, PlayerComparison,
)


def test_position_enum():
    assert Position.ST.value == "ST"
    assert Position.GK.value == "GK"
    assert Position("CM") == Position.CM


def test_platform_enum():
    assert Platform.PS.value == "ps"
    assert Platform.PC.value == "pc"


def test_sbc_detail_to_dict():
    sbc = SBCDetail(id="123", name="Test SBC", requirements=[{"text": "85 rated"}])
    d = sbc.to_dict()
    assert d["id"] == "123"
    assert d["name"] == "Test SBC"
    assert len(d["requirements"]) == 1


def test_evolution_detail_to_dict():
    evo = EvolutionDetail(id="456", name="Speed Boost", upgrades=[{"text": "+5 PAC"}])
    d = evo.to_dict()
    assert d["id"] == "456"
    assert len(d["upgrades"]) == 1


def test_player_comparison_to_dict():
    p1 = Player(id=1, name="A", position="ST", version="", rating=90,
                club="", nation="", year=26, url="", stats={"pac": 95})
    p2 = Player(id=2, name="B", position="ST", version="", rating=88,
                club="", nation="", year=26, url="", stats={"pac": 85})
    comp = PlayerComparison(player1=p1, player2=p2, stat_diffs={"pac": {"player1": 95, "player2": 85, "diff": 10}})
    d = comp.to_dict()
    assert d["stat_diffs"]["pac"]["diff"] == 10
    assert d["player1"]["name"] == "A"


def test_price_history_to_dict():
    from cli_web.futbin.core.models import PriceHistory
    h = PriceHistory(
        player_id=40,
        player_name="Mbappé",
        year=26,
        ps_prices=[[1700000000000, 500000], [1700086400000, 480000], [1700172800000, 520000]],
        pc_prices=[[1700000000000, 450000], [1700086400000, 430000]],
    )
    d = h.to_dict()
    assert d["player_id"] == 40
    assert d["ps_current"] == 520000
    assert d["ps_min"] == 480000
    assert d["ps_max"] == 520000
    assert d["pc_current"] == 430000
    assert d["data_points"] == 3


def test_fodder_tier_to_dict():
    from cli_web.futbin.core.models import FodderTier, FodderPlayer
    tier = FodderTier(rating=88, players=[
        FodderPlayer(id=63, name="Lewandowski", position="ST", price="4.8K"),
        FodderPlayer(id=32, name="Saka", position="RW", price="5K"),
    ])
    d = tier.to_dict()
    assert d["rating"] == 88
    assert d["cheapest_price"] == "4.8K"
    assert len(d["players"]) == 2
    assert d["players"][0]["name"] == "Lewandowski"


def test_price_history_empty():
    from cli_web.futbin.core.models import PriceHistory
    h = PriceHistory(player_id=999, player_name="Unknown", year=26)
    d = h.to_dict()
    assert d["ps_current"] is None
    assert d["pc_current"] is None
    assert d["data_points"] == 0
