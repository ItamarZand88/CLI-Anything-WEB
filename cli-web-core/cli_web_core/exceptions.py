"""Canonical exception hierarchy for cli-web-* CLIs.

Matches the contract in HARNESS.md / CONVENTIONS.md:

- every error carries a stable JSON error code (``error_code_for``)
- ``to_dict()`` produces the ``--json`` error envelope payload
- ``raise_for_status()`` maps HTTP status codes to typed exceptions

Generated CLIs historically vendor an app-named copy of this hierarchy
(``<App>Error`` base); new CLIs may subclass :class:`AppError` directly.
"""

from __future__ import annotations

from typing import Any, Protocol


class AppError(Exception):
    """Base exception for all CLI errors."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": True,
            "code": error_code_for(self),
            "message": str(self),
        }


class AuthError(AppError):
    """Authentication failed — expired cookies, invalid tokens, session timeout.

    Args:
        recoverable: If True, client runs the 3-attempt auto-refresh
                     (current cookies -> reload auth.json -> browser refresh;
                     see HARNESS.md "Token Auto-Refresh").
                     If False, user must re-login.
    """

    def __init__(self, message: str, recoverable: bool = True):
        self.recoverable = recoverable
        super().__init__(message)


class RateLimitError(AppError):
    """Server returned 429 — too many requests.

    Args:
        retry_after: Seconds to wait before retrying (from Retry-After header).
    """

    def __init__(self, message: str, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        return d


class NetworkError(AppError):
    """Connection failed — DNS resolution, TCP connect, TLS handshake, timeout."""


class ServerError(AppError):
    """Server returned 5xx.

    Args:
        status_code: The HTTP status code (500, 502, 503, ...).
    """

    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found (HTTP 404)."""


class ValidationError(AppError):
    """Invalid input — bad parameters, missing required fields."""


class RPCError(AppError):
    """Non-REST protocol error (batchexecute / custom RPC envelope)."""


_EXCEPTION_CODES: dict[type[AppError], str] = {
    AuthError: "AUTH_EXPIRED",
    RateLimitError: "RATE_LIMITED",
    NotFoundError: "NOT_FOUND",
    ServerError: "SERVER_ERROR",
    NetworkError: "NETWORK_ERROR",
    ValidationError: "VALIDATION_ERROR",
    RPCError: "RPC_ERROR",
}


def error_code_for(exc: BaseException) -> str:
    """Stable JSON error code for an exception (``UNKNOWN_ERROR`` fallback)."""
    for exc_type, code in _EXCEPTION_CODES.items():
        if isinstance(exc, exc_type):
            return code
    return "UNKNOWN_ERROR"


# ── Numeric exit-code contract ───────────────────────────────────────────────
# 0 = ok, 1 = unknown/internal, 2 = usage (Click's own convention), then one
# code per recoverable failure class so scripts/agents can branch on $?.
# New CLIs adopt this via the helpers template; the existing fleet keeps its
# historical 0/1 exits until a coordinated major release (documented in
# CONVENTIONS.md §Exit Codes).

EXIT_OK = 0
EXIT_UNKNOWN = 1
EXIT_USAGE = 2
EXIT_AUTH = 3
EXIT_NOT_FOUND = 4
EXIT_RATE_LIMIT = 5
EXIT_SERVER = 6
EXIT_NETWORK = 7

_EXIT_CODES: dict[type[AppError], int] = {
    AuthError: EXIT_AUTH,
    NotFoundError: EXIT_NOT_FOUND,
    RateLimitError: EXIT_RATE_LIMIT,
    ServerError: EXIT_SERVER,
    NetworkError: EXIT_NETWORK,
}


def exit_code_for(exc: BaseException) -> int:
    """Numeric exit code for an exception (``EXIT_UNKNOWN`` fallback)."""
    for exc_type, code in _EXIT_CODES.items():
        if isinstance(exc, exc_type):
            return code
    return EXIT_UNKNOWN


class _ResponseLike(Protocol):
    """Anything with status_code/text/headers (httpx, curl_cffi, requests)."""

    status_code: int
    text: str

    @property
    def headers(self) -> Any: ...


def raise_for_status(response: _ResponseLike) -> None:
    """Map an HTTP error status to a typed exception. No-op below 400."""
    status = response.status_code
    if status < 400:
        return

    snippet = (response.text or "")[:200]
    msg = f"HTTP {status}: {snippet}"

    if status in (401, 403):
        raise AuthError(msg, recoverable=True)
    if status == 404:
        raise NotFoundError(msg)
    if status == 429:
        retry_after = None
        raw = response.headers.get("Retry-After")
        if raw:
            try:
                retry_after = float(raw)
            except (TypeError, ValueError):
                retry_after = None
        raise RateLimitError(msg, retry_after=retry_after)
    if 500 <= status < 600:
        raise ServerError(msg, status_code=status)
    raise AppError(msg)
