"""HTTP client for cli-web-airbnb.

Airbnb uses SSR HTML with niobeClientData embedded in script tags.
Bot protection (Akamai + DataDome) bypassed with curl_cffi Chrome impersonation.
"""

from __future__ import annotations

import base64
import json
import re
from typing import Optional

from curl_cffi import requests as curl_requests

from .exceptions import (
    AirbnbError,
    AuthError,
    BotBlockedError,
    NetworkError,
    NotFoundError,
    ParseError,
    RateLimitError,
    ServerError,
)
from .models import AvailabilityDay, AvailabilityMonth, Listing, LocationSuggestion, Review

import os as _os

BASE_URL = "https://www.airbnb.com"
# Public Airbnb web API key — embedded in airbnb.com JS bundle.
# Override via CLI_WEB_AIRBNB_API_KEY if the key is ever rotated.
API_KEY = _os.environ.get("CLI_WEB_AIRBNB_API_KEY", "d306zoyjsyarp7ifhu67rjxn52tv0t20")

# sha256 hashes for v3 persisted GraphQL queries (captured from traffic).
_REVIEWS_HASH = "2ed951bfedf71b87d9d30e24a419e15517af9fbed7ac560a8d1cc7feadfa22e6"
_AVAIL_HASH = "b23335819df0dc391a338d665e2ee2f5d3bff19181d05c0b39bc6c5aac403914"

_DEFAULT_HEADERS = {
    "accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}
_API_HEADERS = {
    "accept": "application/json",
    "x-airbnb-api-key": API_KEY,
}


def _decode_listing_id(encoded_id: str) -> str:
    """Decode base64 listing ID to integer string."""
    padded = encoded_id + "=" * (4 - len(encoded_id) % 4)
    try:
        return base64.b64decode(padded).decode("utf-8").split(":")[-1]
    except Exception:
        return encoded_id


def _encode_listing_id(int_id: str) -> str:
    """Encode integer listing ID to base64 (DemandStayListing prefix for search/detail)."""
    raw = f"DemandStayListing:{int_id}"
    return base64.b64encode(raw.encode()).decode().rstrip("=")


def _encode_stay_listing_id(int_id: str) -> str:
    """Encode integer listing ID to base64 (StayListing prefix for reviews GraphQL)."""
    raw = f"StayListing:{int_id}"
    return base64.b64encode(raw.encode()).decode().rstrip("=")


def _location_to_slug(location: str) -> str:
    """Convert 'London, UK' to 'London--UK'."""
    parts = [p.strip() for p in location.split(",")]
    return "--".join(p.replace(" ", "-") for p in parts)


def _strip_html(text: str) -> str:
    """Strip HTML tags and unescape common HTML entities from text."""
    if not text:
        return text
    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", " ", text)
    # Unescape common HTML entities
    clean = clean.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    clean = clean.replace("&nbsp;", " ").replace("&quot;", '"').replace("&#39;", "'")
    # Collapse multiple spaces/newlines
    clean = re.sub(r"[ \t]+", " ", clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()


def _extract_niobe_data(html: str, operation: str) -> Optional[dict]:
    """Extract embedded GraphQL response from Airbnb SSR page."""
    scripts = re.findall(
        r'<script[^>]*type=["\x27]application/json["\x27][^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    for raw in scripts:
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if not isinstance(data, dict) or "niobeClientData" not in data:
            continue
        for item in data["niobeClientData"]:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                key, value = item[0], item[1]
                if isinstance(key, str) and key.startswith(operation + ":"):
                    return value
    return None


def _parse_search_listing(raw: dict) -> Listing:
    """Parse a single listing from StaysSearch results."""
    stay = raw.get("demandStayListing", {})
    id_b64 = stay.get("id", "")
    listing_id = _decode_listing_id(id_b64)
    primary = raw.get("structuredDisplayPrice", {}).get("primaryLine", {})
    coord = stay.get("location", {}).get("coordinate", {})
    name_obj = raw.get("nameLocalized", {})
    name = name_obj.get("localizedStringWithTranslationPreference", "") or raw.get("name", "")
    badges = [b.get("text", "") for b in raw.get("badges", []) if b.get("text")]
    return Listing(
        id=listing_id,
        id_b64=id_b64,
        name=name,
        url=f"{BASE_URL}/rooms/{listing_id}",
        rating=raw.get("avgRatingLocalized") or raw.get("avgRating"),
        price=primary.get("price"),
        price_qualifier=primary.get("qualifier"),
        latitude=coord.get("latitude"),
        longitude=coord.get("longitude"),
        badges=badges,
    )


class AirbnbClient:
    """Fetch Airbnb data via SSR HTML extraction and /api/v2/ REST API."""

    def __init__(self, locale: str = "en", currency: str = "USD") -> None:
        self.locale = locale
        self.currency = currency
        self._session = curl_requests.Session(
            impersonate="chrome",
            headers=_DEFAULT_HEADERS,
        )

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "AirbnbClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _get_html(self, url: str, params: Optional[dict] = None) -> str:
        try:
            resp = self._session.get(url, params=params, timeout=30)
        except Exception as exc:
            raise NetworkError(f"Request failed: {exc}") from exc
        self._raise_for_status(resp, url)
        return resp.text

    def _api_v3_get(self, operation_name: str, sha256_hash: str, variables: dict) -> dict:
        """Make a v3 persisted GraphQL query request."""
        url = f"{BASE_URL}/api/v3/{operation_name}/{sha256_hash}"
        params = {
            "operationName": operation_name,
            "locale": self.locale,
            "currency": self.currency,
            "variables": json.dumps(variables, separators=(",", ":")),
            "extensions": json.dumps(
                {"persistedQuery": {"version": 1, "sha256Hash": sha256_hash}},
                separators=(",", ":"),
            ),
        }
        try:
            resp = self._session.get(url, params=params, headers=_API_HEADERS, timeout=30)
        except Exception as exc:
            raise NetworkError(f"Request failed: {exc}") from exc
        self._raise_for_status(resp, url)
        return resp.json()

    def _api_get(self, path: str, params: Optional[dict] = None) -> dict:
        all_params = {"key": API_KEY, "locale": self.locale, "currency": self.currency}
        if params:
            all_params.update(params)
        url = f"{BASE_URL}{path}"
        try:
            resp = self._session.get(url, params=all_params, headers=_API_HEADERS, timeout=30)
        except Exception as exc:
            raise NetworkError(f"Request failed: {exc}") from exc
        self._raise_for_status(resp, url)
        return resp.json()

    def _raise_for_status(self, resp, url: str) -> None:
        code = resp.status_code
        if code == 200:
            return
        if code == 401:
            raise AuthError(f"Unauthorized (HTTP 401).", recoverable=False)
        if code == 403:
            raise BotBlockedError(f"Blocked by bot protection (HTTP 403).")
        if code == 404:
            raise NotFoundError(f"Not found: {url}")
        if code == 429:
            retry = resp.headers.get("Retry-After")
            raise RateLimitError("Rate limited by Airbnb", retry_after=float(retry) if retry else 60.0)
        if code >= 500:
            raise ServerError(f"Server error HTTP {code}", status_code=code)
        raise AirbnbError(f"Unexpected HTTP {code}: {url}")

    def search_stays(
        self,
        location: str,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        pets: int = 0,
        checkin: Optional[str] = None,
        checkout: Optional[str] = None,
        price_min: Optional[int] = None,
        price_max: Optional[int] = None,
        room_types: Optional[list] = None,
        amenities: Optional[list] = None,
        cursor: Optional[str] = None,
        place_id: Optional[str] = None,
    ) -> dict:
        """Search stays in a given location."""
        location_slug = _location_to_slug(location)
        params: dict = {"adults": adults, "locale": self.locale, "currency": self.currency}
        if children:
            params["children"] = children
        if infants:
            params["infants"] = infants
        if pets:
            params["pets"] = pets
        if checkin:
            params["checkin"] = checkin
        if checkout:
            params["checkout"] = checkout
        if price_min:
            params["price_min"] = price_min
        if price_max:
            params["price_max"] = price_max
        if room_types:
            params["room_types[]"] = room_types
        if amenities:
            params["amenities[]"] = amenities
        if cursor:
            params["cursor"] = cursor
        if place_id:
            params["place_id"] = place_id

        html = self._get_html(f"{BASE_URL}/s/{location_slug}/homes", params)
        niobe = _extract_niobe_data(html, "StaysSearch")
        if niobe is None:
            raise ParseError("No StaysSearch data in page. Bot protection may have triggered.")

        try:
            results = niobe["data"]["presentation"]["staysSearch"]["results"]
            pagination = results.get("paginationInfo", {})
        except (KeyError, TypeError) as exc:
            raise ParseError(f"Unexpected niobeClientData: {exc}") from exc

        listings = []
        for raw in results.get("searchResults", []):
            try:
                listings.append(_parse_search_listing(raw))
            except Exception:
                continue

        return {
            "listings": listings,
            "next_cursor": pagination.get("nextPageCursor"),
            "total_count": pagination.get("totalCount"),
            "location_slug": location_slug,
        }

    def get_listing(
        self,
        listing_id: str,
        adults: int = 1,
        checkin: Optional[str] = None,
        checkout: Optional[str] = None,
    ) -> Listing:
        """Get detailed information about a specific listing."""
        params: dict = {"adults": adults, "locale": self.locale, "currency": self.currency}
        if checkin:
            params["check_in"] = checkin
        if checkout:
            params["check_out"] = checkout
        html = self._get_html(f"{BASE_URL}/rooms/{listing_id}", params)
        id_b64 = _encode_listing_id(listing_id)
        name = rating = host_name = description = None
        review_count = bedrooms = max_guests = None
        bathrooms = None
        amenities: list = []

        niobe = _extract_niobe_data(html, "StaysPdpSections")
        if niobe:
            try:
                pdp = niobe["data"]["presentation"]["stayProductDetailPage"]
                # Airbnb returns sections as either a nested dict {"sections": [...]}
                # or directly as a list — handle both structures defensively.
                _sec_raw = pdp.get("sections", [])
                _sec_list = _sec_raw.get("sections", []) if isinstance(_sec_raw, dict) else (_sec_raw if isinstance(_sec_raw, list) else [])
                for sg in _sec_list:
                    sec = sg.get("section") or {}
                    stype = sec.get("__typename", "")
                    if stype == "PdpTitleSection":
                        name = sec.get("title")
                    elif stype == "StayPdpReviewsSection":
                        # Airbnb renamed from PdpReviewsSection → StayPdpReviewsSection
                        rv = sec.get("overallRating")
                        if rv:
                            rc = sec.get("overallCount", 0)
                            rating = f"{rv} ({rc})"
                            review_count = rc
                    elif stype == "MeetYourHostSection":
                        # Airbnb renamed from PdpHostSection → MeetYourHostSection
                        # host name is nested in cardData
                        host_name = (sec.get("cardData") or {}).get("name")
                    elif stype == "PdpDescriptionSection":
                        raw_desc = (sec.get("htmlDescription") or {}).get("htmlText") or sec.get("description")
                        description = _strip_html(raw_desc) if raw_desc else None
                    elif stype == "AmenitiesSection":
                        # Airbnb renamed from PdpAmenitiesSection → AmenitiesSection
                        for group in sec.get("seeAllAmenitiesGroups", []):
                            for a in group.get("amenities", []):
                                if a.get("available", True):
                                    amenities.append(a.get("title", ""))
                    elif stype == "PdpOverviewSection":
                        # Legacy section type (may still appear on some pages)
                        for item in sec.get("detailItems", []):
                            label = item.get("title", "")
                            if "bedroom" in label.lower():
                                try:
                                    bedrooms = int(label.split()[0])
                                except Exception:
                                    pass
                            elif "bath" in label.lower():
                                try:
                                    bathrooms = float(label.split()[0])
                                except Exception:
                                    pass
                            elif "guest" in label.lower():
                                try:
                                    max_guests = int(label.split()[0])
                                except Exception:
                                    pass
            except (KeyError, TypeError):
                pass

        if not name:
            m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            if m:
                name = m.group(1)
        if not name:
            m = re.search(r"<title[^>]*>([^<]+)</title>", html)
            if m:
                name = m.group(1).split(" - ")[0].strip()
        if not name:
            name = f"Listing {listing_id}"

        return Listing(
            id=listing_id,
            id_b64=id_b64,
            name=name,
            url=f"{BASE_URL}/rooms/{listing_id}",
            rating=rating,
            review_count=review_count,
            host_name=host_name,
            description=description,
            amenities=amenities,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            max_guests=max_guests,
        )

    def get_reviews(
        self,
        listing_id: str,
        limit: int = 24,
        offset: int = 0,
        sort: str = "BEST_QUALITY",
    ) -> dict:
        """Get guest reviews for a listing via StaysPdpReviewsQuery."""
        # Reviews API uses StayListing: prefix (not DemandStayListing:)
        id_b64 = base64.b64encode(f"StayListing:{listing_id}".encode()).decode().rstrip("=")
        variables = {
            "id": id_b64,
            "pdpReviewsRequest": {
                "fieldSelector": "for_p3_translation_only",
                "forPreview": False,
                "limit": limit,
                "offset": str(offset),
                "showingTranslationButton": False,
                "first": limit,
                "sortingPreference": sort,
                "amenityFilters": None,
            },
        }
        data = self._api_v3_get("StaysPdpReviewsQuery", _REVIEWS_HASH, variables)
        try:
            pdp_reviews = data["data"]["presentation"]["stayProductDetailPage"]["reviews"]
            raw_list = pdp_reviews.get("reviews", [])
            metadata = pdp_reviews.get("metadata", {})
            reviews = []
            for r in raw_list:
                reviewer = (r.get("reviewer") or {})
                reviews.append(
                    Review(
                        id=r.get("id", ""),
                        rating=r.get("rating"),
                        date=r.get("localizedDate") or r.get("createdAt"),
                        reviewer=reviewer.get("firstName"),
                        reviewer_location=r.get("localizedReviewerLocation"),
                        comment=r.get("comments"),
                        host_response=r.get("response"),
                    )
                )
            return {"reviews": reviews, "total_count": metadata.get("reviewsCount")}
        except (KeyError, TypeError) as exc:
            raise ParseError(f"Unexpected reviews response: {exc}") from exc

    def get_availability(
        self,
        listing_id: str,
        month: Optional[int] = None,
        year: Optional[int] = None,
        count: int = 12,
    ) -> list:
        """Get availability calendar for a listing via PdpAvailabilityCalendar."""
        import datetime

        today = datetime.date.today()
        variables = {
            "request": {
                "count": count,
                "listingId": listing_id,
                "month": month if month is not None else today.month,
                "year": year if year is not None else today.year,
                "returnPropertyLevelCalendarIfApplicable": False,
            }
        }
        data = self._api_v3_get("PdpAvailabilityCalendar", _AVAIL_HASH, variables)
        try:
            calendar_months_raw = data["data"]["merlin"]["pdpAvailabilityCalendar"]["calendarMonths"]
            result = []
            for month_data in calendar_months_raw:
                days = []
                for day in month_data.get("days", []):
                    price_obj = day.get("price") or {}
                    days.append(
                        AvailabilityDay(
                            date=day.get("calendarDate", ""),
                            available=day.get("available", False),
                            checkin=day.get("availableForCheckin", False),
                            checkout=day.get("availableForCheckout", False),
                            bookable=day.get("bookable") or False,
                            min_nights=day.get("minNights"),
                            max_nights=day.get("maxNights"),
                            price=price_obj.get("localPriceFormatted"),
                        )
                    )
                result.append(
                    AvailabilityMonth(
                        month=month_data.get("month", 0),
                        year=month_data.get("year", 0),
                        days=days,
                    )
                )
            return result
        except (KeyError, TypeError) as exc:
            raise ParseError(f"Unexpected availability response: {exc}") from exc

    def autocomplete_locations(self, query: str, num_results: int = 5) -> list:
        """Get location suggestions for a partial query."""
        params = {"user_input": query, "num_results": num_results, "api_version": "1.2.0"}
        data = self._api_get("/api/v2/autocompletes-personalized", params)
        suggestions = []
        for item in data.get("autocomplete_terms", []):
            esp = item.get("explore_search_params", {})
            # place_id and query are top-level fields in explore_search_params (v1.2.0 API)
            place_id = esp.get("place_id") or item.get("location", {}).get("google_place_id")
            query_text = esp.get("query") or item.get("display_name", query)
            # acp_id is still inside the params array
            pl = esp.get("params", [])
            acp_id = next((p["value"] for p in pl if p.get("key") == "acp_id"), None)
            display = item.get("display_name") or query_text
            suggestions.append(
                LocationSuggestion(
                    query=query_text,
                    place_id=place_id,
                    display=display,
                    acp_id=acp_id,
                )
            )
        return suggestions
