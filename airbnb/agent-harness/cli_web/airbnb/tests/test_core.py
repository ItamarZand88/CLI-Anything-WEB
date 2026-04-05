"""Unit tests for cli-web-airbnb core modules."""

from __future__ import annotations

import base64
import json
import sys
import pytest

from unittest.mock import patch, MagicMock

import click
from click.testing import CliRunner

from cli_web.airbnb.core.exceptions import (
    AirbnbError,
    AuthError,
    BotBlockedError,
    NetworkError,
    NotFoundError,
    ParseError,
    RateLimitError,
    ServerError,
)
from cli_web.airbnb.core.models import Listing, LocationSuggestion
from cli_web.airbnb.core.client import (
    _decode_listing_id,
    _encode_listing_id,
    _location_to_slug,
    _extract_niobe_data,
    _parse_search_listing,
)
from cli_web.airbnb.utils.helpers import (
    handle_errors,
    json_error,
    resolve_json_mode,
    print_json,
    truncate,
)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

def test_airbnb_error_is_exception():
    err = AirbnbError("test")
    assert isinstance(err, Exception)
    assert str(err) == "test"


def test_auth_error_defaults():
    err = AuthError()
    assert err.recoverable is False
    assert "Authentication" in str(err)


def test_auth_error_recoverable():
    err = AuthError("Session expired", recoverable=True)
    assert err.recoverable is True


def test_rate_limit_error():
    err = RateLimitError("Too many requests", retry_after=30.0)
    assert err.retry_after == 30.0


def test_server_error():
    err = ServerError("Internal error", status_code=503)
    assert err.status_code == 503


def test_exception_hierarchy():
    assert issubclass(AuthError, AirbnbError)
    assert issubclass(RateLimitError, AirbnbError)
    assert issubclass(NetworkError, AirbnbError)
    assert issubclass(ServerError, AirbnbError)
    assert issubclass(NotFoundError, AirbnbError)
    assert issubclass(ParseError, AirbnbError)


# ---------------------------------------------------------------------------
# Listing ID encode/decode
# ---------------------------------------------------------------------------

def test_decode_listing_id_roundtrip():
    """Decoded b64 ID matches the original integer string."""
    original = "770993223449115417"
    encoded = _encode_listing_id(original)
    assert encoded  # not empty
    decoded = _decode_listing_id(encoded)
    assert decoded == original


def test_decode_listing_id_known():
    """Known b64 -> integer mapping from captured traffic."""
    b64 = "RGVtYW5kU3RheUxpc3Rpbmc6NzcwOTkzMjIzNDQ5MTE1NDE3"
    result = _decode_listing_id(b64)
    assert result == "770993223449115417"


def test_encode_listing_id_known():
    result = _encode_listing_id("770993223449115417")
    # Verify the base64 prefix is correct
    decoded = base64.b64decode(result + "=" * (4 - len(result) % 4)).decode()
    assert decoded == "DemandStayListing:770993223449115417"


def test_decode_invalid_id_passthrough():
    """Invalid base64 should return the input unchanged."""
    result = _decode_listing_id("plain-integer-12345")
    assert result == "plain-integer-12345"


# ---------------------------------------------------------------------------
# Location slug
# ---------------------------------------------------------------------------

def test_location_to_slug_simple():
    assert _location_to_slug("London, UK") == "London--UK"


def test_location_to_slug_multi():
    assert _location_to_slug("New York, NY, United States") == "New-York--NY--United-States"


def test_location_to_slug_spaces():
    assert _location_to_slug("Paris, France") == "Paris--France"


def test_location_to_slug_no_comma():
    assert _location_to_slug("Barcelona") == "Barcelona"


# ---------------------------------------------------------------------------
# niobeClientData extraction
# ---------------------------------------------------------------------------

SAMPLE_SEARCH_HTML = """
<html>
<head></head>
<body>
<script type="application/json">{"niobeClientData": [["StaysSearch:{}", {"data": {"presentation": {"staysSearch": {"results": {"searchResults": [], "paginationInfo": {"nextPageCursor": "abc123"}}}}}}]]}</script>
</body>
</html>
"""

SAMPLE_BOOL_SCRIPT_HTML = """
<html>
<body>
<script type="application/json">true</script>
<script type='application/json'>{"niobeClientData": [["StaysSearch:{}", {"data": {"presentation": {"staysSearch": {"results": {"searchResults": [], "paginationInfo": {}}}}}}]]}</script>
</body>
</html>
"""


def test_extract_niobe_data_found():
    result = _extract_niobe_data(SAMPLE_SEARCH_HTML, "StaysSearch")
    assert result is not None
    assert "data" in result


def test_extract_niobe_data_not_found():
    result = _extract_niobe_data(SAMPLE_SEARCH_HTML, "StaysPdpSections")
    assert result is None


def test_extract_niobe_data_bool_script():
    """bool JSON values in script tags should not crash the parser."""
    result = _extract_niobe_data(SAMPLE_BOOL_SCRIPT_HTML, "StaysSearch")
    assert result is not None


def test_extract_niobe_data_empty():
    result = _extract_niobe_data("<html></html>", "StaysSearch")
    assert result is None


# ---------------------------------------------------------------------------
# _parse_search_listing
# ---------------------------------------------------------------------------

SAMPLE_LISTING_RAW = {
    "demandStayListing": {
        "id": "RGVtYW5kU3RheUxpc3Rpbmc6NzcwOTkzMjIzNDQ5MTE1NDE3",
        "location": {
            "coordinate": {"latitude": 51.5, "longitude": -0.1}
        }
    },
    "nameLocalized": {
        "localizedStringWithTranslationPreference": "Cozy Room with View"
    },
    "avgRatingLocalized": "4.98 (42)",
    "structuredDisplayPrice": {
        "primaryLine": {"price": "$142", "qualifier": "total"}
    },
    "badges": [{"text": "Guest favorite"}],
}


def test_parse_search_listing():
    listing = _parse_search_listing(SAMPLE_LISTING_RAW)
    assert listing.id == "770993223449115417"
    assert listing.name == "Cozy Room with View"
    assert listing.rating == "4.98 (42)"
    assert listing.price == "$142"
    assert listing.price_qualifier == "total"
    assert listing.latitude == 51.5
    assert listing.longitude == -0.1
    assert "Guest favorite" in listing.badges
    assert listing.url == "https://www.airbnb.com/rooms/770993223449115417"


def test_parse_search_listing_to_dict():
    listing = _parse_search_listing(SAMPLE_LISTING_RAW)
    d = listing.to_dict()
    assert d["id"] == "770993223449115417"
    assert d["name"] == "Cozy Room with View"
    assert isinstance(d["badges"], list)


def test_parse_search_listing_fallback_name():
    """When nameLocalized is absent, falls back to 'name' key."""
    raw = {
        "demandStayListing": {"id": "RGVtYW5kU3RheUxpc3Rpbmc6MTIz"},
        "name": "Fallback Name",
        "structuredDisplayPrice": {"primaryLine": {}},
        "badges": [],
    }
    listing = _parse_search_listing(raw)
    assert listing.name == "Fallback Name"


def test_parse_search_listing_empty_badges():
    """Listings without badges parse cleanly."""
    raw = {
        "demandStayListing": {
            "id": "RGVtYW5kU3RheUxpc3Rpbmc6NzcwOTkzMjIzNDQ5MTE1NDE3",
        },
        "nameLocalized": {"localizedStringWithTranslationPreference": "Test"},
        "structuredDisplayPrice": {"primaryLine": {}},
        "badges": [],
    }
    listing = _parse_search_listing(raw)
    assert listing.badges == []


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

def test_listing_to_dict_complete():
    listing = Listing(
        id="123", id_b64="abc", name="Test", url="https://airbnb.com/rooms/123",
        rating="4.5 (10)", price="$100",
    )
    d = listing.to_dict()
    assert d["id"] == "123"
    assert d["name"] == "Test"
    assert d["price"] == "$100"


def test_listing_all_fields_in_dict():
    """to_dict() must include ALL model fields."""
    listing = Listing(
        id="1", id_b64="b64", name="N", url="u",
        rating="4.9", price="$50", price_qualifier="night",
        latitude=48.8, longitude=2.3, badges=["Superhost"],
        room_type="Private room", location="Paris", review_count=100,
        host_name="Alice", description="Nice place", amenities=["WiFi", "Kitchen"],
        bedrooms=1, bathrooms=1.0, max_guests=2,
    )
    d = listing.to_dict()
    required_keys = [
        "id", "id_b64", "name", "url", "rating", "price", "price_qualifier",
        "latitude", "longitude", "badges", "room_type", "location", "review_count",
        "host_name", "description", "amenities", "bedrooms", "bathrooms", "max_guests",
    ]
    for key in required_keys:
        assert key in d, f"Missing key in to_dict(): {key}"


def test_location_suggestion_to_dict():
    sug = LocationSuggestion(query="London", place_id="ChIJ", display="London, UK")
    d = sug.to_dict()
    assert d["query"] == "London"
    assert d["place_id"] == "ChIJ"
    assert d["display"] == "London, UK"


def test_location_suggestion_display_fallback():
    """display should fall back to query if not set."""
    sug = LocationSuggestion(query="London")
    d = sug.to_dict()
    assert d["display"] == "London"


# ---------------------------------------------------------------------------
# helpers: json_error
# ---------------------------------------------------------------------------

def test_json_error_structure():
    out = json_error("AUTH_EXPIRED", "Token expired")
    data = json.loads(out)
    assert data["error"] is True
    assert data["code"] == "AUTH_EXPIRED"
    assert data["message"] == "Token expired"


def test_json_error_extra_fields():
    out = json_error("RATE_LIMITED", "Too fast", retry_after=60)
    data = json.loads(out)
    assert data["retry_after"] == 60


# ---------------------------------------------------------------------------
# helpers: truncate
# ---------------------------------------------------------------------------

def test_truncate_short_string():
    assert truncate("Hello", 10) == "Hello"


def test_truncate_long_string():
    result = truncate("A" * 100, 60)
    assert len(result) <= 61  # 60 chars + ellipsis character
    assert result.endswith("…")


def test_truncate_none():
    assert truncate(None) == ""


def test_truncate_empty():
    assert truncate("") == ""


# ---------------------------------------------------------------------------
# helpers: resolve_json_mode
# ---------------------------------------------------------------------------

def test_resolve_json_mode_explicit_true():
    assert resolve_json_mode(True) is True


def test_resolve_json_mode_explicit_false_no_ctx():
    assert resolve_json_mode(False) is False


def test_resolve_json_mode_from_ctx():
    """resolve_json_mode reads json flag from ctx.obj."""
    runner = CliRunner()

    @click.command()
    @click.pass_context
    def cmd(ctx):
        ctx.ensure_object(dict)
        ctx.obj["json"] = True
        result = resolve_json_mode(False, ctx)
        assert result is True, "Expected json=True from ctx.obj"

    result = runner.invoke(cmd, [])
    assert result.exit_code == 0, result.output


def test_resolve_json_mode_ctx_false():
    """resolve_json_mode returns False when ctx.obj['json'] is False."""
    runner = CliRunner()

    @click.command()
    @click.pass_context
    def cmd(ctx):
        ctx.ensure_object(dict)
        ctx.obj["json"] = False
        result = resolve_json_mode(False, ctx)
        assert result is False

    result = runner.invoke(cmd, [])
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# helpers: handle_errors exit codes
# ---------------------------------------------------------------------------

def test_handle_errors_auth_exits_1():
    with pytest.raises(SystemExit) as exc:
        with handle_errors():
            raise AuthError("expired")
    assert exc.value.code == 1


def test_handle_errors_not_found_exits_1():
    with pytest.raises(SystemExit) as exc:
        with handle_errors():
            raise NotFoundError("gone")
    assert exc.value.code == 1


def test_handle_errors_rate_limit_exits_1():
    with pytest.raises(SystemExit) as exc:
        with handle_errors():
            raise RateLimitError("slow down", retry_after=30)
    assert exc.value.code == 1


def test_handle_errors_server_error_exits_2():
    with pytest.raises(SystemExit) as exc:
        with handle_errors():
            raise ServerError("boom", status_code=500)
    assert exc.value.code == 2


def test_handle_errors_network_error_exits_2():
    with pytest.raises(SystemExit) as exc:
        with handle_errors():
            raise NetworkError("unreachable")
    assert exc.value.code == 2


def test_handle_errors_json_mode_auth():
    """In json_mode, handle_errors writes JSON error to stdout."""
    runner = CliRunner()

    @click.command()
    def cmd():
        with handle_errors(json_mode=True):
            raise AuthError("Session expired")

    result = runner.invoke(cmd, [])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["error"] is True
    assert data["code"] == "AUTH_EXPIRED"


def test_handle_errors_json_mode_parse_error():
    """ParseError in json_mode produces PARSE_ERROR code."""
    runner = CliRunner()

    @click.command()
    def cmd():
        with handle_errors(json_mode=True):
            raise ParseError("No data found")

    result = runner.invoke(cmd, [])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["code"] == "PARSE_ERROR"


def test_handle_errors_json_mode_rate_limit():
    """RateLimitError in json_mode includes retry_after."""
    runner = CliRunner()

    @click.command()
    def cmd():
        with handle_errors(json_mode=True):
            raise RateLimitError("Too fast", retry_after=60)

    result = runner.invoke(cmd, [])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["code"] == "RATE_LIMITED"
    assert data["retry_after"] == 60


def test_handle_errors_bot_blocked_exits_1():
    """BotBlockedError exits with code 1."""
    with pytest.raises(SystemExit) as exc:
        with handle_errors():
            raise BotBlockedError("403 blocked")
    assert exc.value.code == 1


def test_handle_errors_json_mode_bot_blocked():
    """BotBlockedError in json_mode produces BOT_BLOCKED code."""
    runner = CliRunner()

    @click.command()
    def cmd():
        with handle_errors(json_mode=True):
            raise BotBlockedError("403 blocked")

    result = runner.invoke(cmd, [])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["error"] is True
    assert data["code"] == "BOT_BLOCKED"


# ---------------------------------------------------------------------------
# Client: HTTP status → exception mapping (mocked)
# ---------------------------------------------------------------------------

def _make_mock_response(status_code: int, json_data=None, headers=None):
    """Create a mock curl_cffi response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.json.return_value = json_data or {}
    resp.text = json.dumps(json_data) if json_data else ""
    return resp


def test_client_raises_bot_blocked_on_403():
    from cli_web.airbnb.core.client import AirbnbClient
    client = AirbnbClient()
    mock_resp = _make_mock_response(403)
    with patch.object(client._session, "get", return_value=mock_resp):
        with pytest.raises(BotBlockedError):
            client._get_html("https://www.airbnb.com/s/London/homes")


def test_client_raises_not_found_on_404():
    from cli_web.airbnb.core.client import AirbnbClient
    client = AirbnbClient()
    mock_resp = _make_mock_response(404)
    with patch.object(client._session, "get", return_value=mock_resp):
        with pytest.raises(NotFoundError):
            client._get_html("https://www.airbnb.com/rooms/99999")


def test_client_raises_rate_limit_on_429():
    from cli_web.airbnb.core.client import AirbnbClient
    client = AirbnbClient()
    mock_resp = _make_mock_response(429, headers={"Retry-After": "30"})
    with patch.object(client._session, "get", return_value=mock_resp):
        with pytest.raises(RateLimitError) as exc_info:
            client._get_html("https://www.airbnb.com/s/London/homes")
    assert exc_info.value.retry_after == 30.0


def test_client_raises_server_error_on_503():
    from cli_web.airbnb.core.client import AirbnbClient
    client = AirbnbClient()
    mock_resp = _make_mock_response(503)
    with patch.object(client._session, "get", return_value=mock_resp):
        with pytest.raises(ServerError) as exc_info:
            client._get_html("https://www.airbnb.com/s/London/homes")
    assert exc_info.value.status_code == 503


def test_client_raises_network_error_on_exception():
    from cli_web.airbnb.core.client import AirbnbClient
    client = AirbnbClient()
    with patch.object(client._session, "get", side_effect=Exception("timeout")):
        with pytest.raises(NetworkError):
            client._get_html("https://www.airbnb.com/s/London/homes")


def test_client_raises_parse_error_when_no_niobe():
    """search_stays raises ParseError when SSR page has no niobeClientData."""
    from cli_web.airbnb.core.client import AirbnbClient
    client = AirbnbClient()
    mock_resp = _make_mock_response(200)
    mock_resp.text = "<html><body>No data here</body></html>"
    with patch.object(client._session, "get", return_value=mock_resp):
        with pytest.raises(ParseError):
            client.search_stays("London, UK")


def test_client_autocomplete_parses_response():
    """autocomplete_locations parses the v1.2.0 API response correctly.

    In api_version=1.2.0, place_id and query are top-level fields in
    explore_search_params (NOT inside the params array).
    """
    from cli_web.airbnb.core.client import AirbnbClient
    client = AirbnbClient()
    mock_resp = _make_mock_response(200, json_data={
        "autocomplete_terms": [
            {
                "display_name": "London",
                "explore_search_params": {
                    "place_id": "ChIJdd4hrwug2EcRmSrV3Vo6llI",  # top-level field
                    "query": "London",                            # top-level field
                    "params": [
                        {"key": "acp_id", "value": "4360b783-7c07-41a0-a227-a17d1c3d3895"},
                    ]
                },
                "location": {
                    "google_place_id": "ChIJdd4hrwug2EcRmSrV3Vo6llI",
                }
            }
        ]
    })
    with patch.object(client._session, "get", return_value=mock_resp):
        suggestions = client.autocomplete_locations("Lond")
    assert len(suggestions) == 1
    assert suggestions[0].query == "London"
    assert suggestions[0].place_id == "ChIJdd4hrwug2EcRmSrV3Vo6llI"
    assert suggestions[0].display == "London"
    assert suggestions[0].acp_id == "4360b783-7c07-41a0-a227-a17d1c3d3895"


def test_client_autocomplete_empty_response():
    """autocomplete_locations returns [] when API returns no terms."""
    from cli_web.airbnb.core.client import AirbnbClient
    client = AirbnbClient()
    mock_resp = _make_mock_response(200, json_data={"autocomplete_terms": []})
    with patch.object(client._session, "get", return_value=mock_resp):
        suggestions = client.autocomplete_locations("zzzzz")
    assert suggestions == []
