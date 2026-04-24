"""HTTP client for cli-web-capitoltrades.

Uses curl_cffi with Chrome TLS fingerprinting to bypass the AWS CloudFront
bot protection in front of capitoltrades.com. Falls back to BeautifulSoup for
HTML parsing and native JSON for the BFF autocomplete endpoint.
"""
from __future__ import annotations

from typing import Any

from curl_cffi import requests as curl_requests

from .exceptions import NetworkError, raise_for_status


class CapitoltradesClient:
    """HTTP client for capitoltrades.com (SSR HTML) and bff.capitoltrades.com (JSON)."""

    BASE_URL = "https://www.capitoltrades.com"
    BFF_URL = "https://bff.capitoltrades.com"
    IMPERSONATE = "chrome136"

    def __init__(self, impersonate: str | None = None, timeout: float = 20.0):
        self._impersonate = impersonate or self.IMPERSONATE
        self._timeout = timeout
        self._session = curl_requests.Session(impersonate=self._impersonate)
        self._session.headers.update({
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
        })

    def _request(self, method: str, url: str, **kwargs: Any):
        kwargs.setdefault("timeout", self._timeout)
        try:
            resp = self._session.request(method, url, **kwargs)
        except Exception as exc:
            raise NetworkError(f"Connection failed: {exc}") from exc
        raise_for_status(resp)
        return resp

    def get_html(self, path: str, params: dict | None = None):
        """GET a page on capitoltrades.com and return parsed BeautifulSoup."""
        from bs4 import BeautifulSoup
        if not path.startswith("http"):
            path = self.BASE_URL + path
        resp = self._request("GET", path, params=params)
        return BeautifulSoup(resp.text, "html.parser")

    def get_bff_json(self, path: str, params: dict | None = None) -> dict:
        """GET a JSON endpoint on bff.capitoltrades.com."""
        if not path.startswith("http"):
            path = self.BFF_URL + path
        headers = {
            "accept": "*/*",
            "origin": self.BASE_URL,
            "referer": self.BASE_URL + "/",
        }
        resp = self._request("GET", path, params=params, headers=headers)
        return resp.json()

    def close(self) -> None:
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
