"""HTTP client for cli-web-${app_name} (curl_cffi for anti-bot bypass)."""
from __future__ import annotations

from curl_cffi import requests as curl_requests

from .auth import load_auth, refresh_auth
from .exceptions import (
    ${AppName}Error,
    AuthError,
    NetworkError,
    raise_for_status,
)


class ${AppName}Client:
    """REST client using curl_cffi Chrome TLS impersonation."""

    BASE_URL = "https://FILL_IN_BASE_URL"

    def __init__(self, cookies: dict | None = None):
        if cookies is None:
            try:
                auth_data = load_auth()
                cookies = auth_data.get("cookies", {})
            except AuthError:
                cookies = {}
        self._cookies = cookies
        self._session = curl_requests.Session(impersonate="chrome")
        self._session.headers.update({"User-Agent": "cli-web-${app_name}/0.1.0"})

    def _request(
        self,
        method: str,
        url: str,
        *,
        _attempt: int = 0,
        **kwargs,
    ):
        """Issue HTTP request with 3-attempt auto-refresh on 401/403.

        Attempt 0: try with current cookies
        Attempt 1: reload cookies from auth.json (user may have re-logged in)
        Attempt 2: headless browser refresh (silently navigate to site)
        """
        if not url.startswith("http"):
            url = self.BASE_URL + url
        kwargs.setdefault("cookies", self._cookies)
        try:
            resp = self._session.request(method, url, **kwargs)
        except Exception as exc:
            raise NetworkError(f"Connection failed: {exc}")

        if resp.status_code in (401, 403) and _attempt < 2:
            if _attempt == 0:
                self._reload_cookies_from_disk()
            elif _attempt == 1:
                self._refresh_via_browser()
            kwargs.pop("cookies", None)
            kwargs["cookies"] = self._cookies
            return self._request(method, url, _attempt=_attempt + 1, **kwargs)

        raise_for_status(resp)
        return resp

    def _reload_cookies_from_disk(self) -> None:
        """Reload cookies from auth.json (user may have re-logged in)."""
        try:
            auth_data = load_auth()
            self._cookies = auth_data.get("cookies", {})
        except AuthError:
            pass

    def _refresh_via_browser(self) -> None:
        """Silently refresh cookies using headless browser with saved profile."""
        auth_data = refresh_auth()
        if auth_data:
            self._cookies = auth_data.get("cookies", {})
        else:
            raise AuthError(
                "Session expired and auto-refresh failed. "
                "Run: cli-web-${app_name} auth login",
                recoverable=False,
            )

    # --- Add endpoint methods here ---

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
