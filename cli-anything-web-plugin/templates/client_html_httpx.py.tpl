"""HTTP client for cli-web-${app_name} (HTML scraping)."""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from .exceptions import (
    ${AppName}Error,
    AuthError,
    NetworkError,
    raise_for_status,
)


class ${AppName}Client:
    """HTML scraping client with auth retry and typed exceptions."""

    BASE_URL = "https://FILL_IN_BASE_URL"

    def __init__(self, cookies: dict | None = None, api_key: str | None = None):
        self._cookies = cookies or {}
        self._api_key = api_key
        headers = {"User-Agent": "cli-web-${app_name}/0.1.0"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=30.0),
            headers=headers,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        retry_on_auth: bool = True,
        **kwargs,
    ) -> httpx.Response:
        kwargs.setdefault("cookies", self._cookies)
        try:
            resp = self._client.request(method, path, **kwargs)
        except httpx.ConnectError as exc:
            raise NetworkError(f"Connection failed: {exc}")
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {exc}")

        if resp.status_code in (401, 403) and retry_on_auth:
            self._refresh_auth()
            return self._request(method, path, retry_on_auth=False, **kwargs)

        raise_for_status(resp)
        return resp

    def _parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML response into a BeautifulSoup tree."""
        return BeautifulSoup(html, "html.parser")

    def _refresh_auth(self) -> None:
        """Override to implement token refresh logic."""
        raise AuthError("Auth expired. Run: cli-web-${app_name} auth login", recoverable=False)

    # --- Add endpoint methods here ---

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
