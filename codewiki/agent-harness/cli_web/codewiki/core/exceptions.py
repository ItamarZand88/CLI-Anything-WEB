"""Domain-specific exception hierarchy for cli-web-codewiki."""

from __future__ import annotations


class CodeWikiError(Exception):
    """Base exception for all Code Wiki errors."""

    def to_dict(self) -> dict:
        return {"error": True, "code": error_code_for(self), "message": str(self)}


class AuthError(CodeWikiError):
    """Authentication failure (unlikely for public API, but kept for completeness)."""

    def __init__(self, message: str, recoverable: bool = True):
        self.recoverable = recoverable
        super().__init__(message)


class RateLimitError(CodeWikiError):
    """Rate limited by the server."""

    def __init__(self, message: str, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(message)

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        return d


class NetworkError(CodeWikiError):
    """Network connectivity failure."""


class ServerError(CodeWikiError):
    """Server returned 5xx."""

    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(CodeWikiError):
    """Requested resource not found (404 or empty RPC result)."""


class RPCError(CodeWikiError):
    """Batchexecute RPC-level error."""

    def __init__(self, message: str, code: int | None = None):
        self.code = code
        super().__init__(message)


EXCEPTION_CODE_MAP: dict[type, str] = {
    AuthError: "AUTH_EXPIRED",
    RateLimitError: "RATE_LIMITED",
    NotFoundError: "NOT_FOUND",
    ServerError: "SERVER_ERROR",
    NetworkError: "NETWORK_ERROR",
    RPCError: "RPC_ERROR",
}


def error_code_for(exc: Exception) -> str:
    """Return standardized error code string for JSON output."""
    for cls, code in EXCEPTION_CODE_MAP.items():
        if isinstance(exc, cls):
            return code
    return "INTERNAL_ERROR"
