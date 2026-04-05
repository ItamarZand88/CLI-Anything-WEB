"""Unit tests for cli-web-tripadvisor core modules.

Tests cover: exception hierarchy, client helpers (slug/JSON-LD parsing,
model builders), models, and helpers. No live HTTP calls.
"""

from __future__ import annotations

import json
import pytest

from cli_web.tripadvisor.core.exceptions import (
    AuthError,
    NetworkError,
    NotFoundError,
    ParseError,
    RateLimitError,
    ServerError,
    TripAdvisorError,
)
from cli_web.tripadvisor.core.client import (
    _extract_id_from_url,
    _extract_jsonld_blocks,
    _find_jsonld_by_type,
    _find_jsonld_items,
    _make_slug,
    _slug_from_url,
    _build_hotel,
    _build_restaurant,
    _build_attraction,
)
from cli_web.tripadvisor.core.models import Hotel, Restaurant, Attraction, Location
from cli_web.tripadvisor.utils.helpers import (
    format_rating,
    resolve_json_mode,
    truncate,
)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_base_exception(self):
        exc = TripAdvisorError("base error")
        assert str(exc) == "base error"
        assert exc.to_dict()["error"] is True
        assert exc.to_dict()["code"] == "ERROR"

    def test_auth_error(self):
        exc = AuthError("blocked", recoverable=False)
        assert exc.recoverable is False
        assert exc.to_dict()["code"] == "AUTH_EXPIRED"

    def test_rate_limit_error(self):
        exc = RateLimitError("rate limited", retry_after=30.0)
        assert exc.retry_after == 30.0
        d = exc.to_dict()
        assert d["code"] == "RATE_LIMITED"
        assert d["retry_after"] == 30.0

    def test_server_error(self):
        exc = ServerError("server error", status_code=503)
        assert exc.status_code == 503
        assert exc.to_dict()["status_code"] == 503

    def test_not_found_error(self):
        exc = NotFoundError("not found")
        assert exc.to_dict()["code"] == "NOT_FOUND"

    def test_parse_error(self):
        exc = ParseError("parse failed")
        assert exc.to_dict()["code"] == "PARSE_ERROR"

    def test_network_error(self):
        exc = NetworkError("connection refused")
        assert exc.to_dict()["code"] == "NETWORK_ERROR"

    def test_inheritance_chain(self):
        for cls in (AuthError, RateLimitError, NetworkError, ServerError, NotFoundError, ParseError):
            assert issubclass(cls, TripAdvisorError)
            assert issubclass(cls, Exception)


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

class TestSlugHelpers:
    def test_make_slug_simple(self):
        assert _make_slug("Paris") == "Paris"

    def test_make_slug_with_comma_space(self):
        assert _make_slug("Paris, Ile-de-France") == "Paris_Ile_de_France"

    def test_make_slug_with_spaces(self):
        assert _make_slug("New York City") == "New_York_City"

    def test_slug_from_hotels_url(self):
        url = "/Hotels-g187147-Paris_Ile_de_France-Hotels.html"
        assert _slug_from_url(url) == "Paris_Ile_de_France"

    def test_slug_from_restaurants_url(self):
        url = "/Restaurants-g60763-New_York_City_New_York.html"
        assert _slug_from_url(url) == "New_York_City_New_York"

    def test_slug_from_tourism_url(self):
        url = "/Tourism-g60763-New_York_City_New_York-Vacations.html"
        assert _slug_from_url(url) == "New_York_City_New_York"

    def test_slug_from_none(self):
        assert _slug_from_url("/SomeOtherPage.html") is None


# ---------------------------------------------------------------------------
# ID extraction
# ---------------------------------------------------------------------------

class TestExtractId:
    def test_extract_hotel_id(self):
        url = "https://www.tripadvisor.com/Hotel_Review-g187147-d229968-Reviews-Hotel.html"
        assert _extract_id_from_url(url) == "229968"

    def test_extract_restaurant_id(self):
        url = "https://www.tripadvisor.com/Restaurant_Review-g187147-d1035679-Reviews-Name.html"
        assert _extract_id_from_url(url) == "1035679"

    def test_extract_attraction_id(self):
        url = "https://www.tripadvisor.com/Attraction_Review-g187147-d188151-Reviews-Eiffel_Tower.html"
        assert _extract_id_from_url(url) == "188151"

    def test_extract_id_no_match(self):
        assert _extract_id_from_url("https://www.tripadvisor.com/Hotels.html") == ""


# ---------------------------------------------------------------------------
# JSON-LD extraction
# ---------------------------------------------------------------------------

class TestJsonLDExtraction:
    HOTEL_HTML = """
    <html><body>
    <script type="application/ld+json">
    {
      "@type": "Hotel",
      "name": "Test Hotel",
      "url": "https://www.tripadvisor.com/Hotel_Review-g187147-d229968-Reviews-Test.html",
      "aggregateRating": {"ratingValue": "4.5", "reviewCount": 1000},
      "priceRange": "$$$",
      "address": {"streetAddress": "1 Test St", "addressLocality": "Paris", "addressCountry": "FR"},
      "geo": {"latitude": "48.8", "longitude": "2.3"},
      "telephone": "+33 1 23 45 67 89"
    }
    </script>
    </body></html>
    """

    ITEM_LIST_HTML = """
    <html><body>
    <script type="application/ld+json">
    {
      "@type": "ItemList",
      "itemListElement": [
        {
          "@type": "Hotel",
          "name": "Hotel A",
          "url": "https://www.tripadvisor.com/Hotel_Review-g187147-d111-Reviews-HotelA.html",
          "aggregateRating": {"ratingValue": "4.0", "reviewCount": 500},
          "priceRange": "$$"
        },
        {
          "@type": "Hotel",
          "name": "Hotel B",
          "url": "https://www.tripadvisor.com/Hotel_Review-g187147-d222-Reviews-HotelB.html",
          "aggregateRating": {"ratingValue": "4.8", "reviewCount": 2000},
          "priceRange": "$$$$"
        }
      ]
    }
    </script>
    </body></html>
    """

    def test_extract_single_block(self):
        blocks = _extract_jsonld_blocks(self.HOTEL_HTML)
        assert len(blocks) == 1
        assert blocks[0]["@type"] == "Hotel"
        assert blocks[0]["name"] == "Test Hotel"

    def test_find_by_type(self):
        blocks = _extract_jsonld_blocks(self.HOTEL_HTML)
        hotel = _find_jsonld_by_type(blocks, "Hotel")
        assert hotel is not None
        assert hotel["name"] == "Test Hotel"

    def test_find_by_type_not_found(self):
        blocks = _extract_jsonld_blocks(self.HOTEL_HTML)
        result = _find_jsonld_by_type(blocks, "Restaurant")
        assert result is None

    def test_find_items_from_itemlist(self):
        blocks = _extract_jsonld_blocks(self.ITEM_LIST_HTML)
        items = _find_jsonld_items(blocks, "Hotel")
        assert len(items) == 2
        names = [i["name"] for i in items]
        assert "Hotel A" in names
        assert "Hotel B" in names

    def test_extract_empty_html(self):
        blocks = _extract_jsonld_blocks("<html><body></body></html>")
        assert blocks == []

    def test_extract_invalid_json(self):
        html = '<script type="application/ld+json">{broken json}</script>'
        blocks = _extract_jsonld_blocks(html)
        assert blocks == []

    def test_extract_multiple_blocks(self):
        html = """
        <script type="application/ld+json">{"@type": "Hotel", "name": "A"}</script>
        <script type="application/ld+json">{"@type": "BreadcrumbList", "items": []}</script>
        """
        blocks = _extract_jsonld_blocks(html)
        assert len(blocks) == 2


# ---------------------------------------------------------------------------
# Model builders
# ---------------------------------------------------------------------------

class TestBuildHotel:
    def test_basic_build(self):
        ld = {
            "@type": "Hotel",
            "name": "Grand Hotel",
            "url": "https://www.tripadvisor.com/Hotel_Review-g187147-d229968-Reviews-Grand.html",
            "aggregateRating": {"ratingValue": "4.5", "reviewCount": 1234},
            "priceRange": "$$$",
            "address": {
                "streetAddress": "1 Rue Test",
                "addressLocality": "Paris",
                "addressCountry": "FR",
            },
            "geo": {"latitude": "48.8648", "longitude": "2.3337"},
            "telephone": "+33 1 00 00 00 00",
        }
        hotel = _build_hotel(ld)
        assert hotel.id == "229968"
        assert hotel.name == "Grand Hotel"
        assert hotel.rating == "4.5"
        assert hotel.review_count == 1234
        assert hotel.price_range == "$$$"
        assert hotel.address == "1 Rue Test"
        assert hotel.city == "Paris"
        assert hotel.country == "FR"
        assert hotel.telephone == "+33 1 00 00 00 00"
        assert hotel.latitude == "48.8648"
        assert hotel.longitude == "2.3337"

    def test_missing_fields_fallback(self):
        ld = {"@type": "Hotel", "name": "Minimal", "url": ""}
        hotel = _build_hotel(ld)
        assert hotel.name == "Minimal"
        assert hotel.rating is None
        assert hotel.review_count is None
        assert hotel.price_range is None

    def test_to_dict_completeness(self):
        ld = {
            "@type": "Hotel",
            "name": "Test",
            "url": "https://www.tripadvisor.com/Hotel_Review-g1-d999-Reviews-T.html",
        }
        d = _build_hotel(ld).to_dict()
        expected_keys = {"id", "name", "url", "rating", "review_count", "price_range",
                         "address", "city", "country", "telephone", "latitude",
                         "longitude", "image", "amenities"}
        assert expected_keys == set(d.keys())


class TestBuildRestaurant:
    def test_basic_build(self):
        ld = {
            "@type": "Restaurant",
            "name": "Café de Flore",
            "url": "https://www.tripadvisor.com/Restaurant_Review-g187147-d1035679-Reviews-Cafe.html",
            "aggregateRating": {"ratingValue": "4.2", "reviewCount": 2000},
            "priceRange": "$$",
            "servesCuisine": ["French", "Café"],
            "telephone": "+33 1 45 48 55 26",
            "address": {"streetAddress": "172 Boulevard Saint-Germain", "addressLocality": "Paris"},
        }
        rest = _build_restaurant(ld)
        assert rest.id == "1035679"
        assert rest.name == "Café de Flore"
        assert rest.rating == "4.2"
        assert rest.review_count == 2000
        assert rest.price_range == "$$"
        assert "French" in rest.cuisines
        assert rest.telephone == "+33 1 45 48 55 26"

    def test_single_cuisine_string(self):
        ld = {
            "@type": "Restaurant",
            "name": "Test",
            "url": "https://www.tripadvisor.com/Restaurant_Review-g1-d1-Reviews-T.html",
            "servesCuisine": "Italian",
        }
        rest = _build_restaurant(ld)
        assert rest.cuisines == ["Italian"]

    def test_to_dict_completeness(self):
        ld = {
            "@type": "Restaurant",
            "name": "Test",
            "url": "https://www.tripadvisor.com/Restaurant_Review-g1-d1-Reviews-T.html",
        }
        d = _build_restaurant(ld).to_dict()
        expected_keys = {"id", "name", "url", "rating", "review_count", "price_range",
                         "cuisines", "address", "city", "telephone", "latitude",
                         "longitude", "image", "opening_hours"}
        assert expected_keys == set(d.keys())


class TestBuildAttraction:
    def test_basic_build(self):
        ld = {
            "@type": "TouristAttraction",
            "name": "Eiffel Tower",
            "url": "https://www.tripadvisor.com/Attraction_Review-g187147-d188151-Reviews-Eiffel.html",
            "aggregateRating": {"ratingValue": "4.7", "reviewCount": 85000},
            "geo": {"latitude": "48.8584", "longitude": "2.2945"},
            "openingHours": ["Mo-Su 09:00-23:45"],
        }
        attr = _build_attraction(ld)
        assert attr.id == "188151"
        assert attr.name == "Eiffel Tower"
        assert attr.rating == "4.7"
        assert attr.review_count == 85000
        assert attr.latitude == "48.8584"
        assert attr.opening_hours == ["Mo-Su 09:00-23:45"]

    def test_to_dict_completeness(self):
        ld = {
            "@type": "TouristAttraction",
            "name": "Test",
            "url": "https://www.tripadvisor.com/Attraction_Review-g1-d1-Reviews-T.html",
        }
        d = _build_attraction(ld).to_dict()
        expected_keys = {"id", "name", "url", "rating", "review_count", "address",
                         "city", "telephone", "latitude", "longitude", "image",
                         "opening_hours", "description"}
        assert expected_keys == set(d.keys())


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class TestModels:
    def test_location_to_dict(self):
        loc = Location(
            geo_id="187147",
            name="Paris, France",
            url="/Tourism-g187147-Paris-Vacations.html",
            type="GEO",
            coords="48.856,2.352",
            parent_name="Ile-de-France",
            geo_name="France",
        )
        d = loc.to_dict()
        assert d["geo_id"] == "187147"
        assert d["name"] == "Paris, France"
        assert d["coords"] == "48.856,2.352"

    def test_hotel_to_dict_all_fields(self):
        h = Hotel(
            id="229968",
            name="Test Hotel",
            url="https://www.tripadvisor.com/Hotel_Review-g187147-d229968-...",
            rating="4.5",
            review_count=1000,
            price_range="$$$",
            address="1 Test St",
            city="Paris",
            country="FR",
            telephone="+33 1 00 00 00 00",
            latitude="48.8",
            longitude="2.3",
            image="https://cdn.tripadvisor.com/photo.jpg",
            amenities=["WiFi", "Pool"],
        )
        d = h.to_dict()
        assert d["id"] == "229968"
        assert d["amenities"] == ["WiFi", "Pool"]
        assert d["rating"] == "4.5"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_truncate_short(self):
        assert truncate("hello", 60) == "hello"

    def test_truncate_long(self):
        result = truncate("a" * 70, 60)
        assert result.endswith("…")
        assert len(result) == 61

    def test_truncate_none(self):
        assert truncate(None) == ""

    def test_format_rating_with_count(self):
        assert format_rating("4.5", 1234) == "4.5 (1,234)"

    def test_format_rating_without_count(self):
        assert format_rating("4.5", None) == "4.5"

    def test_format_rating_none(self):
        assert format_rating(None, 100) == "—"

    def test_resolve_json_mode_flag(self):
        assert resolve_json_mode(True) is True

    def test_resolve_json_mode_false(self):
        assert resolve_json_mode(False) is False
