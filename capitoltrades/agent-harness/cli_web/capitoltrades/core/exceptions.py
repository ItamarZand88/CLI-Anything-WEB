"""Typed exception hierarchy for cli-web-capitoltrades.

Every exception carries enough context for:
- Retry decisions (recoverable flag, retry_after)
- Structured JSON output (to_dict / error_code_for)
- CLI exit codes (auth=1, server=2, network=3)
"""
from __future__ import annotations


class CapitoltradesError(Exception):
    """Base exception for all cli-web-capitoltrades errors."""

    def to_dict(self) -> dict:
        return {
            "error": True,
            "code": _error_code_for(self),
            "message": str(self),
        }


class AuthError(CapitoltradesError):
    """Authentication failed -- expired cookies, invalid tokens, session timeout.

    Args:
        recoverable: If True, client retries once (token refresh).
                     If False, user must re-login.
    """

    def __init__(self, message: str, recoverable: bool = True):
        self.recoverable = recoverable
        super().__init__(message)


class RateLimitError(CapitoltradesError):
    """Server returned 429 -- too many requests.

    Args:
        retry_after: Seconds to wait before retrying (from Retry-After header).
    """

    def __init__(self, message: str, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(message)

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        return d


class NetworkError(CapitoltradesError):
    """Connection failed -- DNS resolution, TCP connect, TLS handshake."""


class ServerError(CapitoltradesError):
    """Server returned 5xx -- internal error, bad gateway, service unavailable.

    Args:
        status_code: The HTTP status code (500, 502, 503, etc.)
    """

    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(CapitoltradesError):
    """Resource not found (HTTP 404)."""


class RPCError(CapitoltradesError):
    """RPC call failed (batchexecute decode error, unexpected response shape)."""


# --- HTTP status code mapping ---

_CODE_MAP = {
    401: lambda msg: AuthError(msg, recoverable=True),
    403: lambda msg: AuthError(msg, recoverable=True),
    404: lambda msg: NotFoundError(msg),
    # 429 handled separately below to extract Retry-After header
}


def _error_code_for(exc: CapitoltradesError) -> str:
    """Map exception type to a JSON error code string."""
    mapping = {
        AuthError: "AUTH_EXPIRED",
        RateLimitError: "RATE_LIMITED",
        NotFoundError: "NOT_FOUND",
        ServerError: "SERVER_ERROR",
        NetworkError: "NETWORK_ERROR",
        RPCError: "RPC_ERROR",
    }
    for exc_type, code in mapping.items():
        if isinstance(exc, exc_type):
            return code
    return "UNKNOWN_ERROR"


def raise_for_status(response) -> None:
    """Map HTTP response status to a typed exception. Call after every request."""
    if response.status_code < 400:
        return

    text = getattr(response, "text", "")[:200]
    msg = f"HTTP {response.status_code}: {text}"

    # Specific status codes
    if response.status_code in _CODE_MAP:
        raise _CODE_MAP[response.status_code](msg)

    # Extract Retry-After for 429
    if response.status_code == 429:
        retry_after = None
        if hasattr(response, "headers"):
            raw = response.headers.get("Retry-After")
            if raw:
                try:
                    retry_after = float(raw)
                except ValueError:
                    retry_after = None  # HTTP-date format, ignore
        raise RateLimitError(msg, retry_after=retry_after)

    # 5xx range
    if 500 <= response.status_code < 600:
        raise ServerError(msg, status_code=response.status_code)

    # 4xx fallback
    raise CapitoltradesError(msg)
