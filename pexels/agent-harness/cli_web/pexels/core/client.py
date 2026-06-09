"""HTTP client for Pexels — fetches SSR pages and parses __NEXT_DATA__.

Uses curl_cffi to bypass Cloudflare protection on pexels.com.
"""

import json
import re
from typing import Any

from curl_cffi import requests as curl_requests
from curl_cffi.requests.exceptions import RequestException

from .exceptions import (
    NetworkError,
    NotFoundError,
    ParseError,
    AppError,
    RateLimitError,
    ServerError,
)
from .models import (
    normalize_photo,
    normalize_photo_detail,
    normalize_video,
    normalize_video_detail,
    normalize_user,
    normalize_media_item,
    normalize_collection,
    normalize_collection_summary,
)

BASE_URL = "https://www.pexels.com"
SUGGESTIONS_URL = f"{BASE_URL}/en-us/api/v3/search/suggestions"

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class PexelsClient:
    """Client for fetching data from Pexels via SSR page parsing."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def _request(self, url: str, params: dict | None = None) -> curl_requests.Response:
        """Make an HTTP GET request with Cloudflare bypass."""
        try:
            resp = curl_requests.get(
                url,
                params=params,
                headers=_HEADERS,
                impersonate="chrome",
                timeout=self.timeout,
                allow_redirects=True,
            )
        except RequestException as e:
            raise NetworkError(f"Request failed: {e}")
        except Exception as e:
            if "timeout" in str(e).lower():
                raise NetworkError(f"Request timed out: {url}")
            raise NetworkError(f"Connection failed: {e}")

        self._check_status(resp, url)
        return resp

    @staticmethod
    def _check_status(resp, url: str) -> None:
        """Check HTTP status and raise typed exceptions."""
        code = resp.status_code
        if code < 400:
            return
        text = resp.text[:200]
        msg = f"HTTP {code}: {text}"
        if code == 404:
            raise NotFoundError(msg)
        if code == 429:
            retry_after = resp.headers.get("Retry-After")
            raise RateLimitError(msg, retry_after=float(retry_after) if retry_after else None)
        if 500 <= code < 600:
            raise ServerError(msg, status_code=code)
        raise AppError(msg)

    def _get_page(self, path: str, params: dict | None = None) -> dict:
        """Fetch an SSR page and extract __NEXT_DATA__ JSON."""
        url = f"{BASE_URL}{path}"
        filtered = {k: v for k, v in (params or {}).items() if v is not None}
        resp = self._request(url, params=filtered if filtered else None)

        match = _NEXT_DATA_RE.search(resp.text)
        if not match:
            raise ParseError(f"No __NEXT_DATA__ found at {url}")

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid __NEXT_DATA__ JSON: {e}")

        return data.get("props", {}).get("pageProps", {})

    def _get_json(self, url: str, params: dict | None = None) -> Any:
        """Fetch a JSON API endpoint."""
        resp = self._request(url, params=params)
        return resp.json()

    # ── Photos ─────────────────────────────────────────────────────────

    def search_photos(
        self,
        query: str,
        page: int = 1,
        orientation: str | None = None,
        size: str | None = None,
        color: str | None = None,
    ) -> dict:
        """Search photos. Returns {data, pagination}."""
        params = {
            "page": page if page > 1 else None,
            "orientation": orientation,
            "size": size,
            "color": color,
        }
        props = self._get_page(f"/search/{query}/", params)
        initial = props.get("initialData", {})
        return {
            "data": [normalize_photo(p) for p in (initial.get("data") or [])],
            "pagination": initial.get("pagination", {}),
        }

    def get_photo(self, slug: str) -> dict:
        """Get photo detail by slug (e.g., 'green-leaves-1072179')."""
        if slug.isdigit():
            slug = f"photo-{slug}"
        props = self._get_page(f"/photo/{slug}/")
        medium = props.get("medium", {})
        if not medium:
            raise NotFoundError(f"Photo not found: {slug}")
        details = props.get("mediumDetails", {})
        return normalize_photo_detail(medium, details)

    # ── Videos ─────────────────────────────────────────────────────────

    def search_videos(
        self,
        query: str,
        page: int = 1,
        orientation: str | None = None,
    ) -> dict:
        """Search videos. Returns {data, pagination}."""
        params = {
            "page": page if page > 1 else None,
            "orientation": orientation,
        }
        props = self._get_page(f"/search/videos/{query}/", params)
        initial = props.get("initialData", {})
        return {
            "data": [normalize_video(v) for v in (initial.get("data") or [])],
            "pagination": initial.get("pagination", {}),
        }

    def get_video(self, slug: str) -> dict:
        """Get video detail by slug."""
        if slug.isdigit():
            slug = f"video-{slug}"
        props = self._get_page(f"/video/{slug}/")
        medium = props.get("medium", {})
        if not medium:
            raise NotFoundError(f"Video not found: {slug}")
        return normalize_video_detail(medium)

    # ── Users ──────────────────────────────────────────────────────────

    def get_user(self, username: str) -> dict:
        """Get user profile by username."""
        props = self._get_page(f"/@{username}/")
        user = props.get("user", {})
        if not user:
            raise NotFoundError(f"User not found: {username}")
        media_page = props.get("firstPageOfMedia", {})
        return {
            "user": normalize_user(user),
            "media": {
                "data": [
                    normalize_media_item(m)
                    for m in (media_page.get("data") or [])
                ],
                "pagination": media_page.get("pagination", {}),
            },
        }

    def get_user_media(self, username: str, page: int = 1) -> dict:
        """Get paginated user media."""
        params = {"page": page if page > 1 else None}
        props = self._get_page(f"/@{username}/", params)
        media_page = props.get("firstPageOfMedia") or props.get("initialData") or {}
        return {
            "data": [
                normalize_media_item(m)
                for m in (media_page.get("data") or [])
            ],
            "pagination": media_page.get("pagination", {}),
        }

    # ── Collections ────────────────────────────────────────────────────

    def get_collection(self, slug: str, page: int = 1) -> dict:
        """Get collection detail + media."""
        params = {"page": page if page > 1 else None}
        props = self._get_page(f"/collections/{slug}/", params)
        collection = props.get("collection", {})
        if not collection:
            raise NotFoundError(f"Collection not found: {slug}")
        initial = props.get("initialData", {})
        return {
            "collection": normalize_collection(collection),
            "media": {
                "data": [
                    normalize_media_item(m)
                    for m in (initial.get("data") or [])
                ],
                "pagination": initial.get("pagination", {}),
            },
        }

    def discover(self) -> dict:
        """Get discover page data (popular collections, challenges)."""
        props = self._get_page("/discover/")
        initial = props.get("initialData", {})
        return {
            "popular": [
                normalize_collection_summary(c)
                for c in (initial.get("popular") or [])
            ],
            "collections": self._flatten_collection_groups(
                initial.get("collections") or []
            ),
        }

    # ── Suggestions ────────────────────────────────────────────────────

    def search_suggestions(self, query: str) -> list[str]:
        """Get search autocomplete suggestions."""
        data = self._get_json(f"{SUGGESTIONS_URL}/{query}?")
        attrs = data.get("data", {}).get("attributes", {})
        return attrs.get("suggestions", [])

    # ── Download helpers ───────────────────────────────────────────────

    def download_file(self, url: str, output_path: str) -> str:
        """Download a file (photo or video) to disk."""
        try:
            resp = curl_requests.get(
                url,
                headers=_HEADERS,
                impersonate="chrome",
                timeout=120.0,
                allow_redirects=True,
            )
        except Exception as e:
            raise NetworkError(f"Download failed: {e}")

        self._check_status(resp, url)

        with open(output_path, "wb") as f:
            f.write(resp.content)

        return output_path

    @staticmethod
    def _flatten_collection_groups(groups: list) -> list[dict]:
        """Flatten nested collection groups from discover page."""
        result = []
        for group in groups:
            if isinstance(group, list):
                for item in group:
                    attrs = item.get("attributes", {})
                    result.append({
                        "id": attrs.get("id"),
                        "title": attrs.get("title"),
                        "slug": attrs.get("slug"),
                        "media_count": attrs.get("collection_media_count"),
                        "photos_count": attrs.get("photos_count"),
                        "videos_count": attrs.get("videos_count"),
                    })
            elif isinstance(group, dict):
                attrs = group.get("attributes", {})
                result.append({
                    "id": attrs.get("id"),
                    "title": attrs.get("title"),
                    "slug": attrs.get("slug"),
                    "media_count": attrs.get("collection_media_count"),
                    "photos_count": attrs.get("photos_count"),
                    "videos_count": attrs.get("videos_count"),
                })
        return result
