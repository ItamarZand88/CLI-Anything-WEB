"""HTTP client for Unsplash internal /napi/ endpoints."""

from __future__ import annotations

import httpx

from .exceptions import (
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    UnsplashError,
)

BASE_URL = "https://unsplash.com"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


class UnsplashClient:
    """Client for Unsplash's internal /napi/ REST API."""

    def __init__(self) -> None:
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers=DEFAULT_HEADERS,
            timeout=30.0,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> UnsplashClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # ── HTTP helpers ────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        try:
            resp = self._http.get(path, params=params)
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {exc}") from exc
        except httpx.ConnectError as exc:
            raise NetworkError(f"Connection failed: {exc}") from exc

        if resp.status_code == 404:
            raise NotFoundError(f"Not found: {path}")
        if resp.status_code == 429:
            retry = resp.headers.get("retry-after")
            raise RateLimitError(
                "Rate limited by Unsplash",
                retry_after=float(retry) if retry else None,
            )
        if resp.status_code >= 500:
            raise ServerError(
                f"Server error {resp.status_code}", status_code=resp.status_code
            )
        if resp.status_code >= 400:
            raise UnsplashError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        return resp.json()

    # ── Search ──────────────────────────────────────────────────

    def search_photos(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
        orientation: str | None = None,
        color: str | None = None,
        order_by: str | None = None,
    ) -> dict:
        params: dict = {"query": query, "page": page, "per_page": per_page}
        if orientation:
            params["orientation"] = orientation
        if color:
            params["color"] = color
        if order_by:
            params["order_by"] = order_by
        return self._get("/napi/search/photos", params=params)

    def search_collections(
        self, query: str, page: int = 1, per_page: int = 20
    ) -> dict:
        return self._get(
            "/napi/search/collections",
            params={"query": query, "page": page, "per_page": per_page},
        )

    def search_users(self, query: str, page: int = 1, per_page: int = 20) -> dict:
        return self._get(
            "/napi/search/users",
            params={"query": query, "page": page, "per_page": per_page},
        )

    def autocomplete(self, query: str) -> dict:
        return self._get(f"/nautocomplete/{query}")

    # ── Photos ──────────────────────────────────────────────────

    def get_photo(self, id_or_slug: str) -> dict:
        return self._get(f"/napi/photos/{id_or_slug}")

    def get_photo_related(self, photo_id: str) -> dict:
        return self._get(f"/napi/photos/{photo_id}/related")

    def get_photo_statistics(self, photo_id: str) -> dict:
        return self._get(f"/napi/photos/{photo_id}/statistics")

    def get_random_photos(
        self,
        count: int = 1,
        query: str | None = None,
        topics: str | None = None,
        orientation: str | None = None,
    ) -> list:
        params: dict = {"count": count}
        if query:
            params["query"] = query
        if topics:
            params["topics"] = topics
        if orientation:
            params["orientation"] = orientation
        return self._get("/napi/photos/random", params=params)

    # ── Topics ──────────────────────────────────────────────────

    def list_topics(
        self, page: int = 1, per_page: int = 20, order_by: str | None = None
    ) -> list:
        params: dict = {"page": page, "per_page": per_page}
        if order_by:
            params["order_by"] = order_by
        return self._get("/napi/topics", params=params)

    def get_topic(self, slug: str) -> dict:
        return self._get(f"/napi/topics/{slug}")

    def get_topic_photos(
        self,
        slug: str,
        page: int = 1,
        per_page: int = 20,
        order_by: str | None = None,
    ) -> list:
        params: dict = {"page": page, "per_page": per_page}
        if order_by:
            params["order_by"] = order_by
        return self._get(f"/napi/topics/{slug}/photos", params=params)

    # ── Collections ─────────────────────────────────────────────

    def get_collection(self, collection_id: int | str) -> dict:
        return self._get(f"/napi/collections/{collection_id}")

    def get_collection_photos(
        self, collection_id: int | str, page: int = 1, per_page: int = 20
    ) -> list:
        return self._get(
            f"/napi/collections/{collection_id}/photos",
            params={"page": page, "per_page": per_page},
        )

    # ── Users ───────────────────────────────────────────────────

    def get_user(self, username: str) -> dict:
        return self._get(f"/napi/users/{username}")

    def get_user_photos(
        self,
        username: str,
        page: int = 1,
        per_page: int = 20,
        order_by: str | None = None,
    ) -> list:
        params: dict = {"page": page, "per_page": per_page}
        if order_by:
            params["order_by"] = order_by
        return self._get(f"/napi/users/{username}/photos", params=params)

    def get_user_collections(
        self, username: str, page: int = 1, per_page: int = 20
    ) -> list:
        return self._get(
            f"/napi/users/{username}/collections",
            params={"page": page, "per_page": per_page},
        )
