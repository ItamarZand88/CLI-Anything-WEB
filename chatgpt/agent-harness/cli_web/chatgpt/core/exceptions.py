"""Domain-specific exception hierarchy for cli-web-chatgpt."""

from __future__ import annotations


class ChatGPTError(Exception):
    """Base exception for all ChatGPT CLI errors."""

    def to_dict(self) -> dict:
        return {"error": True, "code": error_code_for(self), "message": str(self)}


class AuthError(ChatGPTError):
    """Authentication failed or credentials missing."""

    def __init__(self, message: str = "Authentication required", recoverable: bool = False):
        super().__init__(message)
        self.recoverable = recoverable


class RateLimitError(ChatGPTError):
    """Rate limited by ChatGPT API."""

    def __init__(self, message: str = "Rate limited", retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        return d


class NetworkError(ChatGPTError):
    """Network connectivity error."""


class ServerError(ChatGPTError):
    """Server returned 5xx error."""

    def __init__(self, message: str = "Server error", status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(ChatGPTError):
    """Resource not found (404)."""


# --- JSON error code mapping (matches utils/helpers.py conventions) ---

EXCEPTION_CODE_MAP = {
    AuthError: "AUTH_EXPIRED",
    RateLimitError: "RATE_LIMITED",
    NotFoundError: "NOT_FOUND",
    ServerError: "SERVER_ERROR",
    NetworkError: "NETWORK_ERROR",
}


def error_code_for(exc: Exception) -> str:
    """Get the JSON error code string for an exception."""
    for exc_type, code in EXCEPTION_CODE_MAP.items():
        if isinstance(exc, exc_type):
            return code
    return "ERROR"
