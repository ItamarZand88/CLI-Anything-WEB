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

    def _rpc(self, method: RPCMethod, params: list, retry_on_auth: bool = True) -> list:
        """Execute an RPC call and return the decoded response.

        Args:
            method: The RPC method descriptor.
            params: RPC params (encoded into ``f.req``).
            retry_on_auth: If True, refresh tokens and retry once on 401/403.
                           Set to False on the retry itself to avoid loops.
        """
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

        # Batchexecute tokens (CSRF / session_id / build_label) are short-lived
        # but cookies outlive them — a 401/403 typically means tokens expired,
        # not that cookies are bad. Refresh and retry once.
        if resp.status_code in (401, 403) and retry_on_auth:
            self._refresh_tokens()
            return self._rpc(method, params, retry_on_auth=False)

        raise_for_status(resp)
        return decode_response(resp.text, method)

    def _refresh_tokens(self) -> None:
        """Fetch homepage to extract fresh CSRF/session tokens.

        Customize the regex patterns below for the target app. For Google
        batchexecute apps the canonical extractors are ``SNlM0e`` (CSRF),
        ``FdrFJe`` (session_id), and ``cfb2h`` (build_label) — see
        ``stitch/core/auth.py`` or ``notebooklm/core/auth.py`` for worked
        examples, and CLAUDE.md's "Auth cookie priority" section.
        """
        import re
        resp = self._client.get("/", cookies=self._cookies, follow_redirects=True)
        if resp.status_code != 200:
            raise AuthError("Token refresh failed. Run: cli-web-${app_name} auth login", recoverable=False)
        html = resp.text
        m = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', html)
        if m:
            self._csrf_token = m.group(1)
        # TODO: extract session_id (FdrFJe) and build_label (cfb2h) here too
        # if your batchexecute URL needs them.

    # --- Add RPC method wrappers here ---

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
