"""HTTP client for cli-web-${app_name} (Google batchexecute RPC)."""
from __future__ import annotations

import httpx

from .exceptions import (
    ${AppName}Error,
    AuthError,
    NetworkError,
    RPCError,
    raise_for_status,
)
from .rpc.encoder import encode_rpc
from .rpc.decoder import decode_response
from .rpc.types import RPCMethod


class ${AppName}Client:
    """Google batchexecute RPC client."""

    BASE_URL = "https://FILL_IN_BASE_URL"
    BATCHEXECUTE_PATH = "/_/FILL_IN_SERVICE/data/batchexecute"

    def __init__(self, cookies: dict | None = None):
        self._cookies = cookies or {}
        self._csrf_token: str | None = None
        self._session_id: str | None = None
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=30.0),
            headers={"User-Agent": "cli-web-${app_name}/0.1.0"},
        )

    def _rpc(self, method: RPCMethod, params: list) -> list:
        """Execute an RPC call and return the decoded response."""
        body = encode_rpc(method, params, csrf_token=self._csrf_token)
        try:
            resp = self._client.post(
                self.BATCHEXECUTE_PATH,
                data=body,
                cookies=self._cookies,
            )
        except httpx.ConnectError as exc:
            raise NetworkError(f"Connection failed: {exc}")
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {exc}")

        raise_for_status(resp)
        return decode_response(resp.text, method)

    def _refresh_tokens(self) -> None:
        """Fetch homepage to extract fresh CSRF/session tokens."""
        import re
        resp = self._client.get("/", cookies=self._cookies, follow_redirects=True)
        if resp.status_code != 200:
            raise AuthError("Token refresh failed. Run: cli-web-${app_name} auth login", recoverable=False)
        # Customize these regex patterns for the target app
        html = resp.text
        m = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', html)
        if m:
            self._csrf_token = m.group(1)

    # --- Add RPC method wrappers here ---

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
