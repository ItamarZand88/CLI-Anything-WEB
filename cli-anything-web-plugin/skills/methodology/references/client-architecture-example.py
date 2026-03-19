"""
Reference: Namespaced Sub-Client Architecture
================================================
For apps with 3+ resource types, split the client into namespaced sub-clients.
Each sub-client handles one API domain and shares the core HTTP transport.

Pattern: client.notebooks.list(), client.sources.add_url(), client.artifacts.generate()

This example shows a generic pattern with REST-style endpoints.
Adapt for batchexecute (add rpc/ encoder/decoder) or GraphQL (query templates).
"""
import httpx
import json
import time
from pathlib import Path

# These would be imported from the generated package
# from .exceptions import AuthError, RateLimitError, ServerError, raise_for_status
# from .rpc.encoder import encode_request, build_url
# from .rpc.decoder import decode_response


class ClientCore:
    """Shared HTTP transport — all sub-clients delegate here.

    Responsibilities:
    - HTTP connection management (httpx.Client)
    - Auth header/cookie injection
    - Status code → exception mapping
    - Auth retry (refresh tokens on 401/403, retry once)
    """

    def __init__(self, base_url: str, cookies: dict | None = None):
        self.base_url = base_url
        self._cookies = cookies or {}
        self._csrf_token = None
        self._session_id = None
        self._client = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=30.0),
            headers={"User-Agent": "cli-web-app/0.1.0"},
        )

    def request(self, method: str, url: str, retry_on_auth: bool = True, **kwargs) -> httpx.Response:
        """Make HTTP request with auth injection and error mapping."""
        # Inject auth
        kwargs.setdefault("cookies", self._cookies)

        try:
            response = self._client.request(method, url, **kwargs)
        except httpx.ConnectError as e:
            raise NetworkError(f"Connection failed: {e}")
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}")

        # Map status to exception
        if response.status_code in (401, 403) and retry_on_auth:
            self._refresh_tokens()
            return self.request(method, url, retry_on_auth=False, **kwargs)

        raise_for_status(response)
        return response

    def _refresh_tokens(self):
        """Re-fetch homepage to extract fresh CSRF/session tokens.

        For browser-delegated auth (Google, Microsoft), the cookies are
        still valid — only the page-embedded tokens (CSRF, session ID)
        have expired. Fetch the homepage with existing cookies and
        re-extract tokens from the HTML.
        """
        import re
        resp = self._client.get("/", cookies=self._cookies, follow_redirects=True)
        if resp.status_code != 200:
            raise AuthError("Token refresh failed — session may have expired. "
                            "Run: cli-web-<app> auth login", recoverable=False)
        html = resp.text
        # Example: Google batchexecute token extraction
        # Adapt these regex patterns for your target app
        m = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', html)
        if m:
            self._csrf_token = m.group(1)
        m = re.search(r'"FdrFJe"\s*:\s*"([^"]+)"', html)
        if m:
            self._session_id = m.group(1)


class NotebooksAPI:
    """Notebook operations — list, create, get, rename, delete."""

    def __init__(self, core: ClientCore):
        self._core = core

    def list(self) -> list:
        """List all notebooks."""
        resp = self._core.request("POST", "/api/notebooks")
        return resp.json()

    def create(self, title: str) -> dict:
        resp = self._core.request("POST", "/api/notebooks", json={"title": title})
        return resp.json()

    def get(self, notebook_id: str) -> dict:
        resp = self._core.request("GET", f"/api/notebooks/{notebook_id}")
        return resp.json()

    def delete(self, notebook_id: str) -> None:
        self._core.request("DELETE", f"/api/notebooks/{notebook_id}")


class SourcesAPI:
    """Source operations — add, list, get, delete."""

    def __init__(self, core: ClientCore):
        self._core = core

    def add_url(self, notebook_id: str, url: str) -> dict:
        resp = self._core.request("POST", f"/api/notebooks/{notebook_id}/sources",
                                  json={"url": url})
        return resp.json()

    def list(self, notebook_id: str) -> list:
        resp = self._core.request("GET", f"/api/notebooks/{notebook_id}/sources")
        return resp.json()


class ArtifactsAPI:
    """Artifact operations — generate, list, download."""

    def __init__(self, core: ClientCore):
        self._core = core

    def generate(self, notebook_id: str, artifact_type: str) -> dict:
        resp = self._core.request("POST", f"/api/notebooks/{notebook_id}/artifacts",
                                  json={"type": artifact_type})
        return resp.json()

    def wait_for_completion(self, notebook_id: str, task_id: str,
                            timeout: float = 300.0) -> dict:
        """Poll until artifact is ready. Uses exponential backoff."""
        from .polling import poll_until_complete  # see polling-backoff-example.py

        def check():
            artifacts = self.list(notebook_id)
            match = [a for a in artifacts if a.get("task_id") == task_id]
            if match and match[0].get("status") in ("completed", "failed"):
                return match[0]
            return None

        return poll_until_complete(check, timeout=timeout)

    def list(self, notebook_id: str) -> list:
        resp = self._core.request("GET", f"/api/notebooks/{notebook_id}/artifacts")
        return resp.json()


class AppClient:
    """Main client — assembles sub-clients with shared transport.

    Usage:
        client = AppClient(cookies=get_cookies())
        notebooks = client.notebooks.list()
        client.sources.add_url(nb_id, "https://example.com")
        client.artifacts.generate(nb_id, "audio")
    """

    def __init__(self, base_url: str = "https://app.example.com", cookies: dict | None = None):
        self._core = ClientCore(base_url, cookies)
        self.notebooks = NotebooksAPI(self._core)
        self.sources = SourcesAPI(self._core)
        self.artifacts = ArtifactsAPI(self._core)

    def close(self):
        self._core._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
