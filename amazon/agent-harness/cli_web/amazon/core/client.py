"""HTTP client for cli-web-amazon.

Protocol: SSR HTML + REST JSON hybrid.
Library: httpx (no Cloudflare/WAF protection detected).
"""
import re
import json as _json
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

from .exceptions import (
    AmazonError, NetworkError, NotFoundError,
    ParsingError, RateLimitError, ServerError,
)
from .models import SearchResult, Product, BestSeller, Suggestion

BASE_URL = "https://www.amazon.com"
COMPLETION_URL = "https://completion.amazon.com"
MERCHANT_ID = "ATVPDKIKX0DER"

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}

_JSON_HEADERS = {
    **_DEFAULT_HEADERS,
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",
}


class AmazonClient:
    """Amazon web client with HTML scraping and JSON API support."""

    def __init__(self):
        """Initialize the client."""
        self._client: httpx.Client | None = None

    def __enter__(self):
        self._client = httpx.Client(
            headers=_DEFAULT_HEADERS,
            follow_redirects=True,
            timeout=30.0,
        )
        return self

    def __exit__(self, *args):
        if self._client:
            self._client.close()
            self._client = None

    # ── Internal helpers ────────────────────────────────────────────────

    def _get(self, url: str, params: dict | None = None,
             headers: dict | None = None) -> httpx.Response:
        """Make a GET request with error mapping."""
        try:
            resp = self._client.get(url, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {url}") from exc
        except httpx.ConnectError as exc:
            raise NetworkError(f"Connection failed: {url}") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Request error: {exc}") from exc
        return self._check_status(resp, url)

    def _post(self, url: str, data: dict | None = None,
              json: dict | None = None) -> httpx.Response:
        """Make a POST request with error mapping."""
        try:
            resp = self._client.post(url, data=data, json=json)
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {url}") from exc
        except httpx.ConnectError as exc:
            raise NetworkError(f"Connection failed: {url}") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Request error: {exc}") from exc
        return self._check_status(resp, url)

    def _check_status(self, resp: httpx.Response, url: str) -> httpx.Response:
        """Map HTTP status codes to typed exceptions."""
        if resp.status_code == 200:
            return resp
        if resp.status_code in (401, 403):
            raise ServerError(
                f"Access denied (HTTP {resp.status_code}) — unexpected on a public endpoint.",
                status_code=resp.status_code,
            )
        if resp.status_code == 404:
            raise NotFoundError(f"Resource not found: {url}")
        if resp.status_code == 429:
            retry_after = None
            if "retry-after" in resp.headers:
                try:
                    retry_after = float(resp.headers["retry-after"])
                except ValueError:
                    pass
            raise RateLimitError("Rate limited by Amazon", retry_after=retry_after)
        if resp.status_code >= 500:
            raise ServerError(
                f"Amazon server error: {resp.status_code}", status_code=resp.status_code
            )
        return resp

    def _soup(self, resp: httpx.Response) -> BeautifulSoup:
        """Parse HTML response as BeautifulSoup."""
        return BeautifulSoup(resp.text, "html.parser")

    # ── Autocomplete Suggestions ────────────────────────────────────────

    def get_suggestions(self, query: str, limit: int = 11) -> list[Suggestion]:
        """Get autocomplete suggestions for a query.

        Uses the /suggestions JSON endpoint.
        """
        params = {
            "limit": str(limit),
            "prefix": query,
            "suggestion-type": ["WIDGET", "KEYWORD"],
            "mid": MERCHANT_ID,
            "alias": "aps",
        }
        resp = self._get(
            f"{BASE_URL}/suggestions",
            params=params,
            headers=_JSON_HEADERS,
        )
        try:
            data = resp.json()
        except Exception as exc:
            raise ParsingError(f"Could not parse suggestions response: {exc}") from exc

        results = []
        for item in data.get("suggestions", []):
            value = item.get("value", "")
            stype = item.get("type", "KEYWORD")
            if value:
                results.append(Suggestion(value=value, type=stype))
        return results

    # ── Search ──────────────────────────────────────────────────────────

    def search(self, query: str, page: int = 1,
               department: str | None = None) -> list[SearchResult]:
        """Search Amazon products.

        Args:
            query: Search keywords.
            page: Page number (default: 1).
            department: Optional department/node filter.

        Returns:
            List of SearchResult objects.
        """
        params: dict[str, Any] = {"k": query}
        if page > 1:
            params["page"] = str(page)
        if department:
            params["i"] = department

        resp = self._get(f"{BASE_URL}/s", params=params)
        soup = self._soup(resp)

        cards = soup.find_all("div", attrs={"data-component-type": "s-search-result"})
        if not cards:
            return []

        results = []
        for card in cards:
            asin = card.get("data-asin", "")
            if not asin:
                continue

            # Title from h2
            title_elem = card.find("h2")
            title = title_elem.get_text(strip=True) if title_elem else ""

            # Price — try a-offscreen first (most reliable), then structured price
            price = ""
            offscreen = card.find("span", class_="a-offscreen")
            if offscreen:
                price = offscreen.get_text(strip=True)
            else:
                whole = card.find("span", class_="a-price-whole")
                frac = card.find("span", class_="a-price-fraction")
                if whole:
                    price = whole.get_text(strip=True)
                    if frac:
                        price += frac.get_text(strip=True)

            # Rating from a-icon-alt
            rating = ""
            rating_elem = card.find("span", class_="a-icon-alt")
            if rating_elem:
                rating = rating_elem.get_text(strip=True)

            # Review count — aria-label near rating
            review_count = ""
            review_elem = card.find("span", attrs={"aria-label": re.compile(r"\d")})
            if review_elem:
                review_count = review_elem.get("aria-label", "")

            # URL — first product link
            link_elem = card.find("a", class_="a-link-normal", href=True)
            url = ""
            if link_elem:
                href = link_elem.get("href", "")
                if href.startswith("http"):
                    url = href
                elif href:
                    url = f"{BASE_URL}{href}"

            results.append(SearchResult(
                asin=asin,
                title=title,
                price=price,
                rating=rating,
                review_count=review_count,
                url=url,
            ))
        return results

    # ── Product Detail ──────────────────────────────────────────────────

    def get_product(self, asin: str) -> Product:
        """Get product details by ASIN.

        Args:
            asin: Amazon Standard Identification Number.

        Returns:
            Product object with full details.

        Raises:
            NotFoundError: If ASIN does not exist.
        """
        resp = self._get(f"{BASE_URL}/dp/{asin}")
        soup = self._soup(resp)
        html_text = resp.text

        # Title
        title_elem = soup.find("span", attrs={"id": "productTitle"})
        title = title_elem.get_text(strip=True) if title_elem else ""
        if not title:
            # Fallback: check if page actually has a product
            if "dp/" not in str(resp.url):
                raise NotFoundError(f"Product not found: {asin}")
            raise ParsingError(f"Could not parse product title for ASIN: {asin}")

        # Detect geo-restriction — Amazon replaces buybox with a "cannot ship" message
        geo_restricted = (
            "cannot be shipped to your selected delivery location" in html_text
            or "item can't be shipped to your selected location" in html_text.lower()
        )

        # Price — try a-offscreen (available in SSR when product ships to this region),
        # then a-price-whole, then embedded JSON blobs in script tags.
        # Note: price is empty when the product is geo-restricted or JS-rendered.
        price = ""
        price_elem = soup.find("span", class_="a-offscreen")
        if price_elem:
            price = price_elem.get_text(strip=True)
        if not price:
            whole = soup.find("span", class_="a-price-whole")
            frac = soup.find("span", class_="a-price-fraction")
            if whole:
                price = whole.get_text(strip=True)
                if frac:
                    price += frac.get_text(strip=True)
        if not price:
            # Fallback: scan embedded script tags for priceAmount / displayPrice JSON fields
            for m in re.finditer(r'"(?:priceAmount|displayPrice)"\s*:\s*"?([^",}]+)"?', html_text):
                candidate = m.group(1).strip()
                if candidate and candidate not in ("", "0"):
                    price = candidate
                    break

        # Build price_note when price is unavailable
        price_note = ""
        if not price:
            if geo_restricted:
                price_note = "Product not available in your region — price not shown"
            else:
                price_note = "Price JS-rendered, not available in SSR HTML"

        # Rating
        rating = ""
        rating_elem = soup.find("span", attrs={"id": "acrPopover"})
        if rating_elem:
            rating = (
                rating_elem.get("title", "")
                or rating_elem.get_text(strip=True)
            )

        # Review count
        review_count = ""
        review_elem = soup.find("span", attrs={"id": "acrCustomerReviewText"})
        if review_elem:
            review_count = review_elem.get_text(strip=True)

        # Brand
        brand = ""
        brand_elem = soup.find(attrs={"id": "bylineInfo"})
        if brand_elem:
            brand = brand_elem.get_text(strip=True)

        # Image
        image_url = ""
        img_elem = soup.find("img", attrs={"id": "landingImage"})
        if img_elem:
            image_url = img_elem.get("src", "") or img_elem.get("data-old-hires", "")

        return Product(
            asin=asin,
            title=title,
            price=price,
            price_note=price_note,
            geo_restricted=geo_restricted,
            rating=rating,
            review_count=review_count,
            brand=brand,
            image_url=image_url,
            url=f"{BASE_URL}/dp/{asin}",
        )

    # ── Product Variants ────────────────────────────────────────────────


    # ── Best Sellers ────────────────────────────────────────────────────

    def get_bestsellers(self, category: str = "electronics",
                        page: int = 1) -> list[BestSeller]:
        """Get Amazon Best Sellers for a category.

        Args:
            category: Category slug (e.g., "electronics", "books", "toys").
            page: Page number.

        Returns:
            List of BestSeller objects.
        """
        url = f"{BASE_URL}/Best-Sellers/zgbs/{category}"
        params = {}
        if page > 1:
            params["pg"] = str(page)

        resp = self._get(url, params=params if params else None)
        soup = self._soup(resp)

        results = []
        # Best seller grid items — each has id="gridItemRoot"
        containers = soup.find_all("div", attrs={"id": "gridItemRoot"})

        for container in containers:
            # ASIN from inner div
            asin_div = container.find("div", attrs={"data-asin": True})
            asin = asin_div.get("data-asin", "") if asin_div else ""
            if not asin:
                continue

            # Rank
            rank = 0
            rank_elem = container.find("span", class_="zg-bdg-text")
            if rank_elem:
                rank_text = rank_elem.get_text(strip=True).lstrip("#")
                try:
                    rank = int(rank_text)
                except ValueError:
                    pass

            # Title — from image alt or link text
            title = ""
            img = container.find("img")
            if img:
                title = img.get("alt", "")
            if not title:
                link = container.find("a", class_="a-link-normal")
                if link:
                    title = link.get_text(strip=True)

            # Price
            price = ""
            price_elem = container.find("span", class_="p13n-sc-price")
            if price_elem:
                price = price_elem.get_text(strip=True)

            # URL
            url_path = ""
            link_elem = container.find("a", class_="a-link-normal", href=True)
            if link_elem:
                href = link_elem.get("href", "")
                if href.startswith("http"):
                    url_path = href
                elif href:
                    url_path = f"{BASE_URL}{href}"

            results.append(BestSeller(
                rank=rank,
                asin=asin,
                title=title,
                price=price,
                url=url_path,
            ))

        return results


