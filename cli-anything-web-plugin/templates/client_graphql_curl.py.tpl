"""HTTP client for cli-web-${app_name} (GraphQL + curl_cffi anti-bot)."""
from __future__ import annotations

from curl_cffi import requests as curl_requests

from .exceptions import (
    ${AppName}Error,
    AuthError,
    NetworkError,
    raise_for_status,
)


class ${AppName}Client:
    """GraphQL client using curl_cffi Chrome TLS impersonation."""

    BASE_URL = "https://FILL_IN_BASE_URL"

    def __init__(self, cookies: dict | None = None):
        self._cookies = cookies or {}
        self._session = curl_requests.Session(impersonate="chrome")
        self._session.headers.update({"User-Agent": "cli-web-${app_name}/0.1.0"})

    def _request(
        self,
        method: str,
        url: str,
        *,
        retry_on_auth: bool = True,
        **kwargs,
    ):
        if not url.startswith("http"):
            url = self.BASE_URL + url
        kwargs.setdefault("cookies", self._cookies)
        try:
            resp = self._session.request(method, url, **kwargs)
        except Exception as exc:
            raise NetworkError(f"Connection failed: {exc}")

        if resp.status_code in (401, 403) and retry_on_auth:
            self._refresh_auth()
            return self._request(method, url, retry_on_auth=False, **kwargs)

        raise_for_status(resp)
        return resp

    def _graphql(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query and return the data payload."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = self._request("POST", "/graphql", json=payload)
        body = resp.json()
        if "errors" in body:
            raise ${AppName}Error(f"GraphQL error: {body['errors'][0].get('message', body['errors'])}")
        return body.get("data", {})

    def _refresh_auth(self) -> None:
        raise AuthError("Auth expired. Run: cli-web-${app_name} auth login", recoverable=False)

    # --- Add endpoint methods here ---

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
