"""Domain-specific exception hierarchy for cli-web-chatgpt."""

from __future__ import annotations


class ChatGPTError(Exception):
    """Base exception for all ChatGPT CLI errors."""


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


class NetworkError(ChatGPTError):
    """Network connectivity error."""


class ServerError(ChatGPTError):
    """Server returned 5xx error."""

    def __init__(self, message: str = "Server error", status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(ChatGPTError):
    """Resource not found (404)."""
