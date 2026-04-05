"""HTTP client for cli-web-tripadvisor.

TripAdvisor uses SSR HTML pages with embedded JSON-LD structured data
(schema.org). Bot protection (DataDome) is bypassed with curl_cffi
Chrome impersonation.

No auth required — all search/listing/detail operations are public.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from curl_cffi import requests as curl_requests

from .exceptions import (
    AuthError,
    NetworkError,
    NotFoundError,
    ParseError,
    RateLimitError,
    ServerError,
    TripAdvisorError,
)
from .models import Attraction, Hotel, Location, Restaurant

BASE_URL = "https://www.tripadvisor.com"
PAGE_SIZE = 30  # hotels/restaurants/attractions per listing page

# TripAdvisor blocks Chrome-family TLS fingerprints via DataDome.
# Safari iOS 17.2 impersonation bypasses the protection.
# Override via CLI_WEB_TRIPADVISOR_IMPERSONATE env var if this rotates.
import os as _os
_IMPERSONATE = _os.environ.get("CLI_WEB_TRIPADVISOR_IMPERSONATE", "safari17_2_ios")

_DEFAULT_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
}
_JSON_HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "en-US,en;q=0.9",
    "x-requested-with": "XMLHttpRequest",
}


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

def _slug_from_url(url: str) -> Optional[str]:
    """Extract the location slug from a TripAdvisor URL path.

    Examples:
      /Tourism-g60763-New_York_City_New_York-Vacations.html → New_York_City_New_York
      /Hotels-g187147-Paris_Ile_de_France-Hotels.html      → Paris_Ile_de_France
    """
    # Pattern 1: /<Type>-g<ID>-<Slug>-<Suffix>.html  (e.g. /Hotels-g187147-Paris-Hotels.html)
    m = re.search(r"-g\d+-([\w]+)-(?:Hotels|Restaurants|Attractions|Vacations|Activities)", url)
    if m:
        return m.group(1)
    # Pattern 2: /<Type>-g<ID>-<Slug>.html  (e.g. /Restaurants-g60763-New_York_City.html)
    m = re.search(r"-g\d+-([\w]+)\.html", url)
    if m:
        return m.group(1)
    return None


def _make_slug(name: str) -> str:
    """Convert a location name to a TripAdvisor URL slug.

    'Paris, Ile-de-France' → 'Paris_Ile_de_France'
    'New York City, New York' → 'New_York_City_New_York'
    """
    slug = name.replace(", ", "_").replace(" ", "_").replace("-", "_")
    # Remove non-ASCII chars that don't appear in TA slugs
    slug = re.sub(r"[^\w_]", "", slug)
    return slug


def _extract_id_from_url(url: str) -> str:
    """Extract numeric d-ID from a TripAdvisor detail URL."""
    m = re.search(r"-d(\d+)-", url)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# JSON-LD extraction
# ---------------------------------------------------------------------------

def _extract_jsonld_blocks(html: str) -> list[dict]:
    """Extract all JSON-LD script blocks from the page HTML.

    Handles both dict and list top-level JSON-LD structures — some sites
    embed an array of LD objects in a single script tag.
    """
    blocks: list[dict] = []
    for raw in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    ):
        try:
            obj = json.loads(raw.strip())
        except Exception:
            continue
        if isinstance(obj, list):
            blocks.extend(item for item in obj if isinstance(item, dict))
        elif isinstance(obj, dict):
            blocks.append(obj)
    return blocks


def _find_jsonld_by_type(blocks: list[dict], *types: str) -> Optional[dict]:
    """Find the first JSON-LD block matching one of the given @type values."""
    for block in blocks:
        t = block.get("@type", "")
        if isinstance(t, list):
            if any(x in types for x in t):
                return block
        elif t in types:
            return block
    return None


def _find_jsonld_items(blocks: list[dict], *item_types: str) -> list[dict]:
    """Extract all items matching item_types from ItemList or CollectionPage blocks.

    Handles two TripAdvisor listing patterns:
    1. ListItem > item (hotel/restaurant listings): itemListElement has
       @type=ListItem with nested `item` dict containing the entity.
    2. Direct items: itemListElement contains the entity directly.
    """
    items: list[dict] = []
    for block in blocks:
        btype = block.get("@type", "")
        list_elements = []

        if btype == "ItemList":
            list_elements = block.get("itemListElement", [])
        elif btype == "CollectionPage":
            me = block.get("mainEntity", {})
            if isinstance(me, dict) and me.get("@type") == "ItemList":
                list_elements = me.get("itemListElement", [])

        for elem in list_elements:
            if elem.get("@type") in item_types:
                items.append(elem)
            elif elem.get("@type") == "ListItem":
                # Pattern: ListItem > item (TripAdvisor hotels/restaurants)
                inner = elem.get("item") or {}
                if inner.get("@type") in item_types:
                    items.append(inner)

    return items


# ---------------------------------------------------------------------------
# Model builders
# ---------------------------------------------------------------------------

def _build_hotel(ld: dict) -> Hotel:
    """Build a Hotel model from a JSON-LD block."""
    url = ld.get("url", "").replace("HotelHighlight", "Hotel_Review")
    hotel_id = _extract_id_from_url(url)
    addr = ld.get("address") or {}
    street = addr.get("streetAddress", "")
    locality = addr.get("addressLocality", "")
    address_str = f"{street}, {locality}".strip(", ") if street or locality else None
    rating_obj = ld.get("aggregateRating") or {}
    return Hotel(
        id=hotel_id,
        name=ld.get("name", ""),
        url=url,
        rating=str(rating_obj.get("ratingValue", "")) or None,
        review_count=_safe_int(rating_obj.get("reviewCount")),
        price_range=ld.get("priceRange"),
        address=street or None,
        city=locality or None,
        country=(addr.get("addressCountry") or None),
        telephone=ld.get("telephone"),
        latitude=str((ld.get("geo") or {}).get("latitude", "")) or None,
        longitude=str((ld.get("geo") or {}).get("longitude", "")) or None,
        image=ld.get("image") if isinstance(ld.get("image"), str) else None,
        amenities=_extract_amenities(ld),
    )


def _build_restaurant(ld: dict) -> Restaurant:
    """Build a Restaurant model from a JSON-LD block."""
    url = ld.get("url", "")
    rest_id = _extract_id_from_url(url)
    addr = ld.get("address") or {}
    street = addr.get("streetAddress", "")
    locality = addr.get("addressLocality", "")
    rating_obj = ld.get("aggregateRating") or {}
    cuisines = ld.get("servesCuisine") or []
    if isinstance(cuisines, str):
        cuisines = [cuisines]
    hours = ld.get("openingHoursSpecification") or []
    hours_strs = _parse_opening_hours(hours)
    return Restaurant(
        id=rest_id,
        name=ld.get("name", ""),
        url=url,
        rating=str(rating_obj.get("ratingValue", "")) or None,
        review_count=_safe_int(rating_obj.get("reviewCount")),
        price_range=ld.get("priceRange"),
        cuisines=list(cuisines),
        address=street or None,
        city=locality or None,
        telephone=ld.get("telephone"),
        latitude=str((ld.get("geo") or {}).get("latitude", "")) or None,
        longitude=str((ld.get("geo") or {}).get("longitude", "")) or None,
        image=ld.get("image") if isinstance(ld.get("image"), str) else None,
        opening_hours=hours_strs,
    )


def _build_attraction(ld: dict) -> Attraction:
    """Build an Attraction model from a JSON-LD block."""
    url = ld.get("url", "")
    attr_id = _extract_id_from_url(url)
    addr = ld.get("address") or {}
    street = addr.get("streetAddress", "")
    locality = addr.get("addressLocality", "")
    rating_obj = ld.get("aggregateRating") or {}
    hours = ld.get("openingHoursSpecification") or ld.get("openingHours") or []
    if isinstance(hours, list) and hours and isinstance(hours[0], str):
        hours_strs = hours
    else:
        hours_strs = _parse_opening_hours(hours if isinstance(hours, list) else [])
    return Attraction(
        id=attr_id,
        name=ld.get("name", ""),
        url=url,
        rating=str(rating_obj.get("ratingValue", "")) or None,
        review_count=_safe_int(rating_obj.get("reviewCount")),
        address=street or None,
        city=locality or None,
        telephone=ld.get("telephone"),
        latitude=str((ld.get("geo") or {}).get("latitude", "")) or None,
        longitude=str((ld.get("geo") or {}).get("longitude", "")) or None,
        image=ld.get("image") if isinstance(ld.get("image"), str) else None,
        opening_hours=hours_strs,
        description=ld.get("description"),
    )


def _extract_amenities(ld: dict) -> list[str]:
    """Extract amenity names from amenityFeatures JSON-LD field."""
    features = ld.get("amenityFeatures") or []
    return [
        f.get("name", "")
        for f in features
        if isinstance(f, dict) and f.get("value") is not False and f.get("name")
    ]


def _parse_opening_hours(spec: list) -> list[str]:
    """Convert openingHoursSpecification objects to readable strings."""
    result = []
    for item in spec:
        if not isinstance(item, dict):
            result.append(str(item))
            continue
        days = item.get("dayOfWeek", [])
        if isinstance(days, str):
            days = [days]
        opens = item.get("opens", "")
        closes = item.get("closes", "")
        day_names = [d.split("/")[-1] for d in days]  # strip schema.org prefix
        if day_names and (opens or closes):
            result.append(f"{', '.join(day_names)}: {opens}–{closes}")
    return result


def _safe_int(val) -> Optional[int]:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _parse_attractions_from_html(html: str) -> list[Attraction]:
    """Fallback HTML parser for TripAdvisor attraction listing pages.

    TripAdvisor attractions listing pages embed only name + geo in JSON-LD;
    the URL, rating, and review count must be extracted from the DOM.
    Parses cards in the QueryAppListWebResponse container.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(attrs={"data-automation": "QueryAppListWebResponse"})
    if not container:
        return []

    seen_ids: dict[str, Attraction] = {}

    for a in container.find_all("a", href=re.compile(r"Attraction_Review-g\d+-d\d+-Reviews-[^#]+")):
        href = a.get("href", "")
        # Skip anchor links like #R (review) and #S (booking)
        if "#" in href:
            continue
        m_id = re.search(r"-d(\d+)-", href)
        if not m_id:
            continue
        d_id = m_id.group(1)
        if d_id in seen_ids:
            continue  # already processed this attraction

        name_raw = a.get_text(strip=True)
        # Skip empty or non-name links (e.g. image-only links)
        if not name_raw:
            continue
        # Remove leading rank number "1. "
        name = re.sub(r"^\d+\.\s*", "", name_raw).strip()
        if not name:
            continue
        # Skip "Review of:" links (user review entries, not attraction listings)
        if name.startswith("Review of:") or name.startswith("Review of "):
            continue
        # Skip garbled "nearby attraction" cards where the link text contains the
        # full card content (rating + distance + categories merged into one string)
        if "of 5 bubbles" in name or "mi away" in name or len(name) > 100:
            continue

        full_url = BASE_URL + href if href.startswith("/") else href

        # Walk up to the card container to extract rating / review count
        card = a
        for _ in range(8):
            if card.parent:
                card = card.parent
            card_text = card.get_text(" ", strip=True)
            # Stop at a container that has rating-like content
            if re.search(r"\d\.\d", card_text) and "of 5" in card_text:
                break

        card_text = card.get_text(" ", strip=True)

        rating: Optional[str] = None
        review_count: Optional[int] = None

        # Rating: pick only single-digit.single-digit pattern before "of 5"
        rating_m = re.search(r"\b(\d\.\d)\s+of 5", card_text)
        if rating_m:
            rating = rating_m.group(1)

        # Review count: first parenthesised number in the card
        # TA separates digits with spaces e.g. "( 69,598 )"
        review_m = re.search(r"\(\s*([\d,\s]+)\s*\)", card_text)
        if review_m:
            review_count = _safe_int(review_m.group(1).replace(",", "").replace(" ", ""))

        seen_ids[d_id] = Attraction(
            id=d_id,
            name=name,
            url=full_url,
            rating=rating,
            review_count=review_count,
        )

    return list(seen_ids.values())


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class TripAdvisorClient:
    """Fetch TripAdvisor data via SSR HTML JSON-LD extraction and TypeAheadJson REST.

    No authentication required. DataDome bot protection bypassed with
    curl_cffi Chrome impersonation.
    """

    def __init__(self) -> None:
        # Do NOT pass session-level headers — they override curl_cffi's built-in
        # impersonation header set, which breaks the TLS/HTTP fingerprint that
        # bypasses DataDome. Let the impersonation profile manage its own headers.
        self._session = curl_requests.Session(impersonate=_IMPERSONATE)

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "TripAdvisorClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _get_html(self, url: str, params: Optional[dict] = None) -> str:
        try:
            resp = self._session.get(url, params=params, timeout=30)
        except Exception as exc:
            raise NetworkError(f"Request failed: {exc}") from exc
        self._raise_for_status(resp, url)
        return resp.text

    def _get_json(self, url: str, params: Optional[dict] = None) -> dict:
        # Do NOT add XHR headers — they can trigger DataDome's bot detection.
        # The session's default headers (impersonating Safari iOS) are sufficient.
        try:
            resp = self._session.get(url, params=params, timeout=30)
        except Exception as exc:
            raise NetworkError(f"Request failed: {exc}") from exc
        self._raise_for_status(resp, url)
        try:
            return resp.json()
        except Exception as exc:
            raise ParseError(f"Response is not valid JSON: {exc}") from exc

    def _raise_for_status(self, resp, url: str) -> None:
        code = resp.status_code
        if code == 200:
            return
        if code in (401, 403):
            raise AuthError(
                f"Blocked (HTTP {code}). DataDome bot protection may have triggered.",
                recoverable=False,
            )
        if code == 404:
            raise NotFoundError(f"Page not found: {url}")
        if code == 429:
            retry = resp.headers.get("retry-after") or resp.headers.get("Retry-After")
            raise RateLimitError(
                "Rate limited by TripAdvisor",
                retry_after=float(retry) if retry else 60.0,
            )
        if code >= 500:
            raise ServerError(f"Server error HTTP {code}", status_code=code)
        raise TripAdvisorError(f"Unexpected HTTP {code}: {url}")

    def _resolve_location(self, location: str) -> tuple[str, str]:
        """Given a location string, return (geo_id, slug).

        First tries TypeAheadJson to get geo_id and canonical URL/slug.
        Raises ParseError if location cannot be resolved.
        """
        results = self.search_locations(location, max_results=1)
        if not results:
            raise ParseError(
                f"Could not resolve location '{location}'. "
                "Try a more specific name or pass --geo-id directly."
            )
        loc = results[0]
        slug = _slug_from_url(loc.url)
        if not slug:
            slug = _make_slug(loc.name)
        return loc.geo_id, slug

    # -----------------------------------------------------------------------
    # Location search (TypeAheadJson)
    # -----------------------------------------------------------------------

    def search_locations(self, query: str, max_results: int = 6) -> list[Location]:
        """Search for locations via TripAdvisor TypeAheadJson REST API."""
        params = {
            "query": query,
            "max": max_results,
            "types": "geo,hotel,airline,attraction,eatery",
            "action": "API",
            "startTime": "0",
            "uiOrigin": "MASTHEAD_SEARCH",
            "source": "MASTHEAD_SEARCH_BOX",
            "userId": "",
            "interleaved": "true",
            "strictAnd": "false",
            "details": "true",
        }
        data = self._get_json(f"{BASE_URL}/TypeAheadJson", params)
        locations = []
        for item in data.get("results", []):
            details = item.get("details") or {}
            locations.append(
                Location(
                    geo_id=str(item.get("value") or item.get("document_id", "")),
                    name=item.get("name", ""),
                    url=item.get("url", ""),
                    type=item.get("type", "GEO"),
                    coords=item.get("coords"),
                    parent_name=details.get("parent_name"),
                    geo_name=details.get("geo_name"),
                )
            )
        return locations

    # -----------------------------------------------------------------------
    # Hotels
    # -----------------------------------------------------------------------

    def search_hotels(
        self,
        location: str,
        geo_id: Optional[str] = None,
        page: int = 1,
    ) -> dict:
        """Search hotels in a location. Returns list of Hotel objects."""
        if geo_id:
            slug = _make_slug(location) if location else None
            resolved_geo_id = geo_id
        else:
            resolved_geo_id, slug = self._resolve_location(location)

        offset = (page - 1) * PAGE_SIZE
        if offset > 0:
            path = f"/Hotels-g{resolved_geo_id}-oa{offset}-{slug}-Hotels.html"
        else:
            path = f"/Hotels-g{resolved_geo_id}-{slug}-Hotels.html"

        html = self._get_html(f"{BASE_URL}{path}")
        blocks = _extract_jsonld_blocks(html)

        # Hotel listing pages embed Hotel type items inside an ItemList
        items = _find_jsonld_items(blocks, "Hotel", "LodgingBusiness")

        if not items:
            # Fallback: look for top-level Hotel/LodgingBusiness blocks
            for b in blocks:
                if b.get("@type") in ("Hotel", "LodgingBusiness") and b.get("url"):
                    items.append(b)

        hotels = []
        for item in items:
            try:
                hotels.append(_build_hotel(item))
            except Exception:
                continue

        return {
            "hotels": hotels,
            "geo_id": resolved_geo_id,
            "location": location,
            "page": page,
            "offset": offset,
        }

    def get_hotel(self, url: str) -> Hotel:
        """Get detailed hotel information from its full TripAdvisor URL."""
        if not url.startswith("http"):
            url = BASE_URL + url
        html = self._get_html(url)
        blocks = _extract_jsonld_blocks(html)

        # Detail page: LodgingBusiness or Hotel
        ld = _find_jsonld_by_type(blocks, "LodgingBusiness", "Hotel")
        if ld is None:
            raise ParseError(
                f"No hotel JSON-LD found at {url}. "
                "Bot protection may have triggered or page layout changed."
            )

        hotel = _build_hotel(ld)
        if not hotel.url:
            hotel.url = url
        if not hotel.id:
            hotel.id = _extract_id_from_url(url)
        return hotel

    # -----------------------------------------------------------------------
    # Restaurants
    # -----------------------------------------------------------------------

    def search_restaurants(
        self,
        location: str,
        geo_id: Optional[str] = None,
        page: int = 1,
    ) -> dict:
        """Search restaurants in a location. Returns list of Restaurant objects."""
        if geo_id:
            slug = _make_slug(location) if location else None
            resolved_geo_id = geo_id
        else:
            resolved_geo_id, slug = self._resolve_location(location)

        offset = (page - 1) * PAGE_SIZE
        if offset > 0:
            path = f"/Restaurants-g{resolved_geo_id}-oa{offset}-{slug}.html"
        else:
            path = f"/Restaurants-g{resolved_geo_id}-{slug}.html"

        html = self._get_html(f"{BASE_URL}{path}")
        blocks = _extract_jsonld_blocks(html)

        items = _find_jsonld_items(
            blocks, "Restaurant", "FoodEstablishment", "CafeOrCoffeeShop", "BarOrPub"
        )
        if not items:
            for b in blocks:
                if b.get("@type") in (
                    "Restaurant", "FoodEstablishment", "CafeOrCoffeeShop"
                ) and b.get("url"):
                    items.append(b)

        restaurants = []
        for item in items:
            try:
                restaurants.append(_build_restaurant(item))
            except Exception:
                continue

        return {
            "restaurants": restaurants,
            "geo_id": resolved_geo_id,
            "location": location,
            "page": page,
            "offset": offset,
        }

    def get_restaurant(self, url: str) -> Restaurant:
        """Get detailed restaurant information from its full TripAdvisor URL."""
        if not url.startswith("http"):
            url = BASE_URL + url
        html = self._get_html(url)
        blocks = _extract_jsonld_blocks(html)

        ld = _find_jsonld_by_type(
            blocks, "Restaurant", "FoodEstablishment", "CafeOrCoffeeShop"
        )
        if ld is None:
            raise ParseError(
                f"No restaurant JSON-LD found at {url}. "
                "Bot protection may have triggered or page layout changed."
            )

        rest = _build_restaurant(ld)
        if not rest.url:
            rest.url = url
        if not rest.id:
            rest.id = _extract_id_from_url(url)
        return rest

    # -----------------------------------------------------------------------
    # Attractions
    # -----------------------------------------------------------------------

    def search_attractions(
        self,
        location: str,
        geo_id: Optional[str] = None,
        page: int = 1,
    ) -> dict:
        """Search attractions in a location. Returns list of Attraction objects."""
        if geo_id:
            slug = _make_slug(location) if location else None
            resolved_geo_id = geo_id
        else:
            resolved_geo_id, slug = self._resolve_location(location)

        offset = (page - 1) * PAGE_SIZE
        if offset > 0:
            path = f"/Attractions-g{resolved_geo_id}-oa{offset}-Activities-{slug}.html"
        else:
            path = f"/Attractions-g{resolved_geo_id}-Activities-{slug}.html"

        html = self._get_html(f"{BASE_URL}{path}")
        blocks = _extract_jsonld_blocks(html)

        items = _find_jsonld_items(
            blocks, "TouristAttraction", "LocalBusiness", "TouristDestination"
        )
        if not items:
            for b in blocks:
                if b.get("@type") in (
                    "TouristAttraction", "LocalBusiness", "TouristDestination"
                ) and b.get("url"):
                    items.append(b)

        # TripAdvisor attraction listing JSON-LD only contains name + geo — no URL or
        # rating. Fall back to HTML parsing for the real data.
        json_ld_has_urls = any(item.get("url") for item in items)
        if not json_ld_has_urls:
            return {
                "attractions": _parse_attractions_from_html(html),
                "geo_id": resolved_geo_id,
                "location": location,
                "page": page,
                "offset": offset,
            }

        attractions = []
        for item in items:
            try:
                attractions.append(_build_attraction(item))
            except Exception:
                continue

        return {
            "attractions": attractions,
            "geo_id": resolved_geo_id,
            "location": location,
            "page": page,
            "offset": offset,
        }

    def get_attraction(self, url: str) -> Attraction:
        """Get detailed attraction information from its full TripAdvisor URL."""
        if not url.startswith("http"):
            url = BASE_URL + url
        html = self._get_html(url)
        blocks = _extract_jsonld_blocks(html)

        ld = _find_jsonld_by_type(
            blocks, "TouristAttraction", "LocalBusiness", "TouristDestination"
        )
        if ld is None:
            raise ParseError(
                f"No attraction JSON-LD found at {url}. "
                "Bot protection may have triggered or page layout changed."
            )

        attr = _build_attraction(ld)
        if not attr.url:
            attr.url = url
        if not attr.id:
            attr.id = _extract_id_from_url(url)
        return attr
