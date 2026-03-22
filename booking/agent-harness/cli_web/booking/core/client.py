"""HTTP client for Booking.com — hybrid GraphQL + SSR HTML scraping.

Uses curl_cffi for TLS fingerprint impersonation to bypass AWS WAF.
GraphQL endpoint works without cookies; SSR pages need WAF cookies.
"""

from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

from .auth import load_cookies
from .exceptions import (
    AuthError,
    BookingError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    WAFChallengeError,
)
from .models import Destination, Property, PropertyDetail

BASE_URL = "https://www.booking.com"
GRAPHQL_URL = f"{BASE_URL}/dml/graphql"
SEARCH_URL = f"{BASE_URL}/searchresults.html"
DEFAULT_LANG = "en-us"

AUTOCOMPLETE_QUERY = """\
query AutoComplete($input: AutoCompleteRequestInput!) {
  autoCompleteSuggestions(input: $input) {
    results {
      metaData { autocompleteResultId autocompleteResultSource }
      displayInfo { title label }
    }
  }
}"""


class BookingClient:
    """Client for Booking.com API and HTML scraping."""

    def __init__(self, lang: str = DEFAULT_LANG, currency: str | None = None):
        self.lang = lang
        self.currency = currency
        self._cookies: dict[str, str] | None = None

    def _get_cookies(self) -> dict[str, str]:
        """Load WAF cookies, caching for the session."""
        if self._cookies is None:
            self._cookies = load_cookies()
        return self._cookies

    def _check_waf(self, resp: Any) -> None:
        """Check if response is a WAF challenge page."""
        if resp.status_code == 202 and len(resp.text) < 10000:
            if "challenge.js" in resp.text or "aws-waf" in resp.text:
                self._cookies = None  # Invalidate cached cookies
                raise WAFChallengeError()

    def _check_status(self, resp: Any, url: str = "") -> None:
        """Map HTTP status codes to domain exceptions."""
        if resp.status_code == 200:
            return
        if resp.status_code in (401, 403):
            raise AuthError(f"Access denied ({resp.status_code})")
        if resp.status_code == 404:
            raise NotFoundError(f"Not found: {url}")
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            raise RateLimitError(
                "Rate limited by Booking.com",
                retry_after=float(retry_after) if retry_after else None,
            )
        if resp.status_code >= 500:
            raise ServerError(
                f"Server error ({resp.status_code})",
                status_code=resp.status_code,
            )

    def _graphql(self, operation: str, query: str,
                 variables: dict | None = None) -> dict:
        """Execute a GraphQL query (no WAF cookies needed)."""
        try:
            resp = curl_requests.post(
                GRAPHQL_URL,
                params={"lang": self.lang},
                json={
                    "operationName": operation,
                    "variables": variables or {},
                    "query": query,
                },
                impersonate="chrome",
                timeout=15,
            )
        except Exception as e:
            raise NetworkError(f"GraphQL request failed: {e}")

        self._check_status(resp, GRAPHQL_URL)

        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError):
            raise ServerError("Invalid JSON response from GraphQL endpoint")

        if "errors" in data and not data.get("data"):
            errors = data["errors"]
            msg = errors[0].get("message", "Unknown GraphQL error") if errors else "Unknown"
            raise ServerError(f"GraphQL error: {msg}")

        return data.get("data", {})

    def _fetch_html(self, url: str, params: dict | None = None) -> BeautifulSoup:
        """Fetch an SSR HTML page with WAF cookies.

        Uses only the aws-waf-token cookie — the bkng cookie contains
        affiliate data that triggers redirects on hotel detail pages.
        """
        all_cookies = self._get_cookies()
        # Only use WAF-essential cookies to avoid affiliate redirects
        waf_cookies = {}
        for key in ("aws-waf-token",):
            if key in all_cookies:
                waf_cookies[key] = all_cookies[key]
        if not waf_cookies:
            waf_cookies = all_cookies  # Fallback to all cookies

        all_params = {"lang": self.lang}
        if self.currency:
            all_params["selected_currency"] = self.currency
        if params:
            all_params.update(params)

        try:
            resp = curl_requests.get(
                url,
                params=all_params,
                cookies=waf_cookies,
                impersonate="chrome",
                timeout=20,
            )
        except Exception as e:
            raise NetworkError(f"HTTP request failed: {e}")

        self._check_waf(resp)
        self._check_status(resp, url)

        return BeautifulSoup(resp.text, "html.parser")

    # ── AutoComplete (GraphQL) ──────────────────────────────────────

    def autocomplete(self, query: str, limit: int = 5) -> list[Destination]:
        """Resolve a destination query to structured results."""
        variables = {
            "input": {
                "prefixQuery": query,
                "nbSuggestions": limit,
                "fallbackConfig": {
                    "mergeResults": True,
                    "nbMaxMergedResults": 6,
                    "nbMaxThirdPartyResults": 3,
                    "sources": ["GOOGLE", "HERE"],
                },
                "requestConfig": {
                    "enableRequestContextBoost": True,
                },
            }
        }
        data = self._graphql("AutoComplete", AUTOCOMPLETE_QUERY, variables)
        results = (
            data.get("autoCompleteSuggestions", {}).get("results", [])
        )
        return [Destination.from_graphql(r) for r in results]

    # ── Search (SSR HTML) ───────────────────────────────────────────

    def search(
        self,
        destination: str,
        checkin: str,
        checkout: str,
        adults: int = 2,
        rooms: int = 1,
        children: int = 0,
        sort: str | None = None,
        offset: int = 0,
        dest_id: str | None = None,
        dest_type: str | None = None,
    ) -> list[Property]:
        """Search for properties.

        If dest_id/dest_type are not provided, autocomplete is used
        to resolve the destination name first.
        """
        if not dest_id:
            destinations = self.autocomplete(destination, limit=1)
            if not destinations:
                raise NotFoundError(f"Destination not found: {destination}")
            dest = destinations[0]
            dest_id = dest.dest_id
            dest_type = dest.dest_type

        params = {
            "ss": destination,
            "dest_id": dest_id,
            "dest_type": dest_type or "city",
            "checkin": checkin,
            "checkout": checkout,
            "group_adults": str(adults),
            "no_rooms": str(rooms),
            "group_children": str(children),
        }
        if sort:
            params["sr_order"] = sort
        if offset:
            params["offset"] = str(offset)

        soup = self._fetch_html(SEARCH_URL, params)
        return self._parse_search_results(soup)

    def _parse_search_results(self, soup: BeautifulSoup) -> list[Property]:
        """Parse property cards from search results HTML."""
        cards = soup.find_all(attrs={"data-testid": "property-card"})
        properties = []

        for card in cards:
            try:
                prop = self._parse_property_card(card)
                if prop:
                    properties.append(prop)
            except Exception:
                continue  # Skip malformed cards

        return properties

    def _parse_property_card(self, card: Any) -> Property | None:
        """Parse a single property card element."""
        title_el = card.find(attrs={"data-testid": "title"})
        if not title_el:
            return None

        title = title_el.text.strip()

        # Extract slug from title link
        slug = ""
        link = card.find("a", attrs={"data-testid": "title-link"})
        if link:
            href = link.get("href", "")
            slug_match = re.search(r"/hotel/([^?]+)", href)
            if slug_match:
                slug = slug_match.group(1)

        # Score
        score = None
        score_label = ""
        review_count = 0
        score_el = card.find(attrs={"data-testid": "review-score"})
        if score_el:
            score_text = score_el.get_text(separator=" ").strip()
            score, score_label, review_count = Property.parse_score_text(score_text)

        # Price
        price = ""
        price_amount = None
        price_el = card.find(attrs={"data-testid": "price-and-discounted-price"})
        if price_el:
            price, price_amount = Property.parse_price_text(price_el.text)

        # Address
        address = ""
        addr_el = card.find(attrs={"data-testid": "address"})
        if addr_el:
            address = addr_el.text.strip()

        # Distance
        distance = ""
        dist_el = card.find(attrs={"data-testid": "distance"})
        if dist_el:
            distance = dist_el.text.strip()

        return Property(
            title=title,
            slug=slug,
            score=score,
            score_label=score_label,
            review_count=review_count,
            price=price,
            price_amount=price_amount,
            address=address,
            distance=distance,
        )

    # ── Property Detail (SSR HTML + JSON-LD) ────────────────────────

    def get_property(
        self,
        slug: str,
        checkin: str | None = None,
        checkout: str | None = None,
        adults: int = 2,
        rooms: int = 1,
    ) -> PropertyDetail:
        """Get detailed property information from hotel page.

        Note: Date/occupancy params are omitted from the request because
        Booking.com redirects hotel detail pages with booking params to
        search results. The detail page shows general property info
        regardless of dates.
        """
        url = f"{BASE_URL}/hotel/{slug}"
        # Don't pass date/occupancy params — they trigger a redirect
        # to search results on Booking.com's hotel detail pages
        soup = self._fetch_html(url)

        # Extract JSON-LD structured data
        ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in ld_scripts:
            try:
                data = json.loads(script.string)
                if data.get("@type") in ("Hotel", "LodgingBusiness",
                                          "Apartment", "Hostel",
                                          "BedAndBreakfast", "Resort"):
                    return PropertyDetail.from_json_ld(data, slug)
            except (json.JSONDecodeError, TypeError):
                continue

        # Fallback: try to extract basic info from HTML
        name_el = soup.find("h2", class_="pp-header__title")
        if not name_el:
            name_el = soup.find("h2", attrs={"data-testid": True})
        name = name_el.text.strip() if name_el else slug

        return PropertyDetail(name=name, slug=slug)
