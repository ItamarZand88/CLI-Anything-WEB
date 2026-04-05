"""Domain exception hierarchy for cli-web-tripadvisor."""

from __future__ import annotations


class TripAdvisorError(Exception):
    """Base exception for all cli-web-tripadvisor errors."""

    def to_dict(self) -> dict:
        return {"error": True, "code": "ERROR", "message": str(self)}


class AuthError(TripAdvisorError):
    """Bot-protection block (HTTP 401/403) — not user auth, TripAdvisor is public."""

    def __init__(self, message: str = "Access blocked (bot protection)", recoverable: bool = False) -> None:
        super().__init__(message)
        self.recoverable = recoverable

    def to_dict(self) -> dict:
        return {"error": True, "code": "AUTH_EXPIRED", "message": str(self)}


class RateLimitError(TripAdvisorError):
    """API rate limit exceeded (HTTP 429)."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after

    def to_dict(self) -> dict:
        return {
            "error": True,
            "code": "RATE_LIMITED",
            "message": str(self),
            "retry_after": self.retry_after,
        }


class NetworkError(TripAdvisorError):
    """Network / connectivity failure."""

    def to_dict(self) -> dict:
        return {"error": True, "code": "NETWORK_ERROR", "message": str(self)}


class ServerError(TripAdvisorError):
    """Remote server returned a 5xx response."""

    def __init__(self, message: str = "Server error", status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code

    def to_dict(self) -> dict:
        return {
            "error": True,
            "code": "SERVER_ERROR",
            "message": str(self),
            "status_code": self.status_code,
        }


class NotFoundError(TripAdvisorError):
    """Requested resource does not exist (HTTP 404)."""

    def to_dict(self) -> dict:
        return {"error": True, "code": "NOT_FOUND", "message": str(self)}


class ParseError(TripAdvisorError):
    """Could not parse expected JSON-LD / structured data from the page HTML.

    Typically caused by bot-protection triggering a CAPTCHA or challenge page,
    or by a TripAdvisor page-layout change.
    """

    def to_dict(self) -> dict:
        return {"error": True, "code": "PARSE_ERROR", "message": str(self)}
