"""Unit tests for cli-web-booking core modules.

Tests client, auth, models, exceptions, and helpers with mocked HTTP.
No network required — fast and deterministic.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest

from cli_web.booking.core.exceptions import (
    AuthError,
    BookingError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    WAFChallengeError,
)
from cli_web.booking.core.models import Destination, Property, PropertyDetail
from cli_web.booking.utils.helpers import handle_errors, json_error, print_json


# ── Exception Tests ────────────────────────────────────────────────


class TestExceptions:
    """Verify exception hierarchy and attributes."""

    def test_booking_error_is_base(self):
        assert issubclass(AuthError, BookingError)
        assert issubclass(RateLimitError, BookingError)
        assert issubclass(NetworkError, BookingError)
        assert issubclass(ServerError, BookingError)
        assert issubclass(NotFoundError, BookingError)

    def test_auth_error_recoverable(self):
        e = AuthError("expired", recoverable=True)
        assert e.recoverable is True
        assert str(e) == "expired"

    def test_auth_error_not_recoverable(self):
        e = AuthError("invalid", recoverable=False)
        assert e.recoverable is False

    def test_rate_limit_error_retry_after(self):
        e = RateLimitError("slow down", retry_after=60.0)
        assert e.retry_after == 60.0

    def test_server_error_status_code(self):
        e = ServerError("bad gateway", status_code=502)
        assert e.status_code == 502

    def test_waf_challenge_error(self):
        e = WAFChallengeError()
        assert "auth login" in str(e).lower()
        assert e.recoverable is True


# ── Model Tests ────────────────────────────────────────────────────


class TestDestination:
    """Test Destination model and GraphQL parsing."""

    def test_from_graphql_city(self):
        data = {
            "metaData": {"autocompleteResultId": "city/-1456928", "autocompleteResultSource": "BRICK"},
            "displayInfo": {"title": "Paris", "label": "Paris, Ile de France, France"},
        }
        d = Destination.from_graphql(data)
        assert d.dest_id == "-1456928"
        assert d.dest_type == "city"
        assert d.title == "Paris"
        assert d.label == "Paris, Ile de France, France"

    def test_from_graphql_airport(self):
        data = {
            "metaData": {"autocompleteResultId": "airport/8"},
            "displayInfo": {"title": "CDG", "label": "CDG, France"},
        }
        d = Destination.from_graphql(data)
        assert d.dest_id == "8"
        assert d.dest_type == "airport"

    def test_to_dict(self):
        d = Destination(dest_id="-123", dest_type="city", title="Test", label="Test, Country")
        result = d.to_dict()
        assert result["dest_id"] == "-123"
        assert result["dest_type"] == "city"
        assert result["title"] == "Test"


class TestProperty:
    """Test Property model and HTML parsing helpers."""

    def test_parse_score_text_full(self):
        score, label, count = Property.parse_score_text(
            "Scored 8.6  8.6 Excellent   677 reviews"
        )
        assert score == 8.6
        assert label == "Excellent"
        assert count == 677

    def test_parse_score_text_wonderful(self):
        score, label, count = Property.parse_score_text(
            "Scored 9.1  9.1 Wonderful   993 reviews"
        )
        assert score == 9.1
        assert label == "Wonderful"
        assert count == 993

    def test_parse_score_text_no_reviews(self):
        score, label, count = Property.parse_score_text("Scored 7.0 7.0 Good")
        assert score == 7.0
        assert label == "Good"
        assert count == 0

    def test_parse_price_text_shekel(self):
        price, amount = Property.parse_price_text("₪ 2,945")
        assert amount == 2945.0
        assert "2,945" in price

    def test_parse_price_text_usd(self):
        price, amount = Property.parse_price_text("US$150")
        assert amount == 150.0

    def test_parse_price_text_empty(self):
        price, amount = Property.parse_price_text("")
        assert amount is None

    def test_to_dict(self):
        p = Property(title="Hotel Test", slug="fr/test.html", score=8.5,
                     score_label="Very Good", review_count=100, price="$200",
                     price_amount=200.0, address="Paris")
        d = p.to_dict()
        assert d["title"] == "Hotel Test"
        assert d["slug"] == "fr/test.html"
        assert d["score"] == 8.5
        assert d["price_amount"] == 200.0


class TestPropertyDetail:
    """Test PropertyDetail JSON-LD parsing."""

    SAMPLE_LD = {
        "@type": "Hotel",
        "name": "Le Senat",
        "description": "A nice hotel.",
        "image": "https://example.com/img.jpg",
        "url": "https://www.booking.com/hotel/fr/lesenatparis.html",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "10 rue de Vaugirard, Paris",
            "postalCode": "75006",
            "addressCountry": "France",
        },
        "aggregateRating": {
            "ratingValue": 8.6,
            "reviewCount": 676,
            "bestRating": 10,
        },
    }

    def test_from_json_ld(self):
        detail = PropertyDetail.from_json_ld(self.SAMPLE_LD, "fr/lesenatparis.html")
        assert detail.name == "Le Senat"
        assert detail.score == 8.6
        assert detail.review_count == 676
        assert detail.full_address == "10 rue de Vaugirard, Paris"
        assert detail.country == "France"
        assert detail.property_type == "Hotel"

    def test_to_dict(self):
        detail = PropertyDetail.from_json_ld(self.SAMPLE_LD, "fr/test.html")
        d = detail.to_dict()
        assert d["name"] == "Le Senat"
        assert d["score"] == 8.6
        assert d["slug"] == "fr/test.html"
        assert "country" in d


# ── Auth Tests ─────────────────────────────────────────────────────


class TestAuth:
    """Test auth module with mocked filesystem."""

    def test_load_cookies_from_env(self):
        with patch.dict("os.environ", {"CLI_WEB_BOOKING_AUTH_JSON": '{"cookies": {"bkng": "val"}}'}):
            from cli_web.booking.core.auth import load_cookies
            cookies = load_cookies()
            assert cookies["bkng"] == "val"

    def test_load_cookies_missing_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("cli_web.booking.core.auth.AUTH_FILE") as mock_file:
                mock_file.exists.return_value = False
                from cli_web.booking.core.auth import load_cookies
                with pytest.raises(AuthError):
                    load_cookies()

    def test_extract_cookies_list_format(self):
        from cli_web.booking.core.auth import _extract_cookies
        cookies = [
            {"name": "bkng", "value": "abc", "domain": ".booking.com"},
            {"name": "test", "value": "xyz", "domain": "other.com"},
        ]
        result = _extract_cookies(cookies)
        assert result["bkng"] == "abc"
        assert result["test"] == "xyz"

    def test_extract_cookies_domain_priority(self):
        from cli_web.booking.core.auth import _extract_cookies
        cookies = [
            {"name": "sid", "value": "regional", "domain": ".booking.co.uk"},
            {"name": "sid", "value": "primary", "domain": ".booking.com"},
        ]
        result = _extract_cookies(cookies)
        assert result["sid"] == "primary"

    def test_save_and_load(self, tmp_path):
        auth_file = tmp_path / "auth.json"
        with patch("cli_web.booking.core.auth.AUTH_FILE", auth_file), \
             patch("cli_web.booking.core.auth.CONFIG_DIR", tmp_path), \
             patch.dict("os.environ", {}, clear=True):
            from cli_web.booking.core.auth import save_cookies, load_cookies
            save_cookies({"bkng": "test123"})
            cookies = load_cookies()
            assert cookies["bkng"] == "test123"


# ── Client Tests (mocked HTTP) ────────────────────────────────────


class TestClient:
    """Test BookingClient with mocked curl_cffi responses."""

    def _mock_response(self, status_code=200, json_data=None, text=""):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = text or json.dumps(json_data or {})
        resp.json.return_value = json_data or {}
        resp.headers = {}
        return resp

    @patch("cli_web.booking.core.client.curl_requests.post")
    def test_autocomplete_success(self, mock_post):
        mock_post.return_value = self._mock_response(json_data={
            "data": {
                "autoCompleteSuggestions": {
                    "results": [
                        {
                            "metaData": {"autocompleteResultId": "city/-1456928"},
                            "displayInfo": {"title": "Paris", "label": "Paris, France"},
                        }
                    ]
                }
            }
        })
        from cli_web.booking.core.client import BookingClient
        client = BookingClient()
        results = client.autocomplete("Paris")
        assert len(results) == 1
        assert results[0].title == "Paris"
        assert results[0].dest_id == "-1456928"

    @patch("cli_web.booking.core.client.curl_requests.post")
    def test_graphql_server_error(self, mock_post):
        mock_post.return_value = self._mock_response(
            json_data={"errors": [{"message": "Internal error"}]}
        )
        from cli_web.booking.core.client import BookingClient
        client = BookingClient()
        with pytest.raises(ServerError):
            client.autocomplete("test")

    @patch("cli_web.booking.core.client.curl_requests.post")
    def test_graphql_network_error(self, mock_post):
        mock_post.side_effect = Exception("Connection refused")
        from cli_web.booking.core.client import BookingClient
        client = BookingClient()
        with pytest.raises(NetworkError):
            client.autocomplete("test")

    @patch("cli_web.booking.core.client.curl_requests.get")
    @patch("cli_web.booking.core.client.load_cookies")
    @patch("cli_web.booking.core.client.curl_requests.post")
    def test_search_waf_challenge(self, mock_post, mock_load, mock_get):
        mock_load.return_value = {"bkng": "old"}
        mock_post.return_value = self._mock_response(json_data={
            "data": {
                "autoCompleteSuggestions": {
                    "results": [
                        {
                            "metaData": {"autocompleteResultId": "city/-123"},
                            "displayInfo": {"title": "Test", "label": "Test"},
                        }
                    ]
                }
            }
        })
        # WAF challenge response
        mock_get.return_value = self._mock_response(
            status_code=202,
            text='<script src="challenge.js"></script>'
        )
        from cli_web.booking.core.client import BookingClient
        client = BookingClient()
        with pytest.raises(WAFChallengeError):
            client.search("Test", "2026-04-01", "2026-04-04")

    @patch("cli_web.booking.core.client.curl_requests.get")
    @patch("cli_web.booking.core.client.load_cookies")
    def test_fetch_html_404(self, mock_load, mock_get):
        mock_load.return_value = {"bkng": "test"}
        mock_get.return_value = self._mock_response(status_code=404)
        from cli_web.booking.core.client import BookingClient
        client = BookingClient()
        with pytest.raises(NotFoundError):
            client.get_property("fr/nonexistent.html")

    @patch("cli_web.booking.core.client.curl_requests.get")
    @patch("cli_web.booking.core.client.load_cookies")
    def test_fetch_html_429(self, mock_load, mock_get):
        mock_load.return_value = {"bkng": "test"}
        resp = self._mock_response(status_code=429)
        resp.headers = {"Retry-After": "30"}
        mock_get.return_value = resp
        from cli_web.booking.core.client import BookingClient
        client = BookingClient()
        with pytest.raises(RateLimitError) as exc_info:
            client.get_property("fr/test.html")
        assert exc_info.value.retry_after == 30.0


# ── Helpers Tests ──────────────────────────────────────────────────


class TestHelpers:
    """Test shared CLI helpers."""

    def test_json_error_format(self):
        result = json.loads(json_error("AUTH_EXPIRED", "Token expired"))
        assert result["error"] is True
        assert result["code"] == "AUTH_EXPIRED"
        assert result["message"] == "Token expired"

    def test_json_error_with_extra(self):
        result = json.loads(json_error("RATE_LIMITED", "Slow down", retry_after=60))
        assert result["retry_after"] == 60

    def test_handle_errors_auth_exits_1(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise AuthError("expired")
        assert exc.value.code == 1

    def test_handle_errors_server_exits_2(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise ServerError("bad gateway")
        assert exc.value.code == 2

    def test_handle_errors_json_mode(self, capsys):
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise NotFoundError("Hotel not found")
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["error"] is True
        assert data["code"] == "NOT_FOUND"

    def test_handle_errors_keyboard_interrupt(self):
        with pytest.raises(SystemExit) as exc:
            with handle_errors():
                raise KeyboardInterrupt()
        assert exc.value.code == 130


# ── Search HTML Parsing Tests ──────────────────────────────────────


class TestSearchParsing:
    """Test HTML parsing of search results with realistic fixtures."""

    FIXTURE_CARD = """
    <div data-testid="property-card">
      <a data-testid="title-link" href="/hotel/fr/lesenatparis.html?aid=304142&checkin=2026-03-25">
        <div data-testid="title">Le Senat</div>
      </a>
      <div data-testid="review-score">
        <div>Scored 8.6</div>
        <div>8.6</div>
        <div>
          <div>Excellent</div>
          <div>677 reviews</div>
        </div>
      </div>
      <div data-testid="price-and-discounted-price">₪ 2,945</div>
      <div data-testid="address">6th arr., Paris</div>
      <div data-testid="distance">1.2 km from downtown</div>
    </div>
    """

    def test_parse_property_card(self):
        from bs4 import BeautifulSoup
        from cli_web.booking.core.client import BookingClient

        client = BookingClient()
        soup = BeautifulSoup(self.FIXTURE_CARD, "html.parser")
        card = soup.find(attrs={"data-testid": "property-card"})
        prop = client._parse_property_card(card)

        assert prop is not None
        assert prop.title == "Le Senat"
        assert prop.slug == "fr/lesenatparis.html"
        assert prop.score == 8.6
        assert prop.score_label == "Excellent"
        assert prop.review_count == 677
        assert prop.price_amount == 2945.0
        assert prop.address == "6th arr., Paris"

    def test_parse_search_results_multiple(self):
        from bs4 import BeautifulSoup
        from cli_web.booking.core.client import BookingClient

        html = f"""
        <div>
            {self.FIXTURE_CARD}
            <div data-testid="property-card">
                <a data-testid="title-link" href="/hotel/fr/other.html?aid=123">
                    <div data-testid="title">Other Hotel</div>
                </a>
            </div>
        </div>
        """
        client = BookingClient()
        soup = BeautifulSoup(html, "html.parser")
        results = client._parse_search_results(soup)
        assert len(results) == 2
        assert results[0].title == "Le Senat"
        assert results[1].title == "Other Hotel"
