"""HTTP client for cli-web-${app_name} (Google batchexecute RPC)."""
from __future__ import annotations

from typing import Any, Optional

import httpx

from .auth import load_auth, refresh_auth
from .exceptions import (
    ${AppName}Error,
    AuthError,
    NetworkError,
    RPCError,
    raise_for_status,
)
from .rpc.decoder import decode_response
from .rpc.encoder import build_url, encode_request
from .rpc.types import BASE_URL, RPCMethod  # noqa: F401  (RPCMethod re-exported for callers)


class ${AppName}Client:
    """Google batchexecute RPC client with transparent auth-token refresh.

    Tokens (CSRF / session_id / build_label) are short-lived and re-fetched
    from the homepage on every session. Cookies outlive tokens, so a 401/403
    means tokens expired — refresh + retry once. See CLAUDE.md "Auth retry".
    """

    def __init__(self, cookies: Optional[dict] = None):
        self._cookies = cookies or {}
        self._csrf: Optional[str] = None
        self._session_id: Optional[str] = None
        self._build_label: Optional[str] = None
        self._req_id = 100000
        self._client = httpx.Client(
            base_url=BASE_URL,
            timeout=httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=30.0),
            headers={"User-Agent": "cli-web-${app_name}/0.1.0"},
        )

    # ------------------------------------------------------------------
    # Request lifecycle
    # ------------------------------------------------------------------

    def _next_req_id(self) -> int:
        self._req_id += 100000
        return self._req_id

    def _ensure_auth(self) -> None:
        """Populate CSRF / session_id / build_label if not already cached."""
        if self._csrf is None:
            self._refresh_tokens()

    def _rpc(
        self,
        rpc_id: str,
        params: list,
        source_path: str = "/",
        retry_on_auth: bool = True,
    ) -> Any:
        """Execute a batchexecute RPC call and return the decoded result.

        Args:
            rpc_id: The RPC method identifier (from ``RPCMethod``).
            params: RPC params (JSON-encoded into ``f.req``).
            source_path: The ``source-path`` query param context.
            retry_on_auth: If True, refresh tokens + retry once on 401/403.
        """
        self._ensure_auth()

        url = build_url(
            rpc_id=rpc_id,
            session_id=self._session_id or "",
            build_label=self._build_label or "",
            source_path=source_path,
            req_id=self._next_req_id(),
        )
        body = encode_request(rpc_id, params, csrf_token=self._csrf or "")
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            resp = self._client.post(url, data=body, headers=headers, cookies=self._cookies)
        except httpx.ConnectError as exc:
            raise NetworkError(f"Connection failed: {exc}")
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {exc}")

        # Short-lived tokens expire before cookies — refresh + retry once.
        if resp.status_code in (401, 403) and retry_on_auth:
            self._refresh_tokens()
            return self._rpc(rpc_id, params, source_path=source_path, retry_on_auth=False)

        raise_for_status(resp)
        return decode_response(resp.text, rpc_id)

    def _refresh_tokens(self) -> None:
        """Fetch the homepage and extract fresh CSRF/session tokens.

        Default implementation extracts only ``SNlM0e`` (CSRF). Override or
        extend for apps that also need ``FdrFJe`` (session_id) and
        ``cfb2h`` (build_label). See stitch/core/auth.py and
        notebooklm/core/auth.py for worked examples, plus CLAUDE.md's
        "Auth cookie priority" section.
        """
        import re

        resp = self._client.get("/", cookies=self._cookies, follow_redirects=True)
        if resp.status_code != 200:
            raise AuthError(
                "Token refresh failed. Run: cli-web-${app_name} auth login",
                recoverable=False,
            )
        html = resp.text
        m = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', html)
        if m:
            self._csrf = m.group(1)
        m = re.search(r'"FdrFJe"\s*:\s*"(-?[0-9]+)"', html)
        if m:
            self._session_id = m.group(1)
        m = re.search(r'"cfb2h"\s*:\s*"([^"]+)"', html)
        if m:
            self._build_label = m.group(1)

        if not self._csrf:
            raise AuthError(
                "Could not extract CSRF token from homepage. Session may be "
                "expired — run: cli-web-${app_name} auth login",
                recoverable=False,
            )

    # --- Add RPC method wrappers here ---

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        self.close()
