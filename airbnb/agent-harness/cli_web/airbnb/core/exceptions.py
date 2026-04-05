"""Domain exception hierarchy for cli-web-airbnb."""

from __future__ import annotations


class AirbnbError(Exception):
    """Base exception for all cli-web-airbnb errors."""

    def to_dict(self) -> dict:
        """Return structured error dict for --json output."""
        return {"error": True, "code": "ERROR", "message": str(self)}


class AuthError(AirbnbError):
    """Authentication required or token expired (401)."""

    def __init__(self, message: str = "Authentication required", recoverable: bool = False) -> None:
        super().__init__(message)
        self.recoverable = recoverable

    def to_dict(self) -> dict:
        return {"error": True, "code": "AUTH_EXPIRED", "message": str(self)}


class BotBlockedError(AirbnbError):
    """Request blocked by bot-protection (403/CAPTCHA)."""

    def to_dict(self) -> dict:
        return {"error": True, "code": "BOT_BLOCKED", "message": str(self)}


class RateLimitError(AirbnbError):
    """API rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after

    def to_dict(self) -> dict:
        return {"error": True, "code": "RATE_LIMITED", "message": str(self), "retry_after": self.retry_after}


class NetworkError(AirbnbError):
    """Network / connectivity failure."""

    def to_dict(self) -> dict:
        return {"error": True, "code": "NETWORK_ERROR", "message": str(self)}


class ServerError(AirbnbError):
    """Remote server returned a 5xx response."""

    def __init__(self, message: str = "Server error", status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code

    def to_dict(self) -> dict:
        return {"error": True, "code": "SERVER_ERROR", "message": str(self), "status_code": self.status_code}


class NotFoundError(AirbnbError):
    """Requested resource does not exist (404)."""

    def to_dict(self) -> dict:
        return {"error": True, "code": "NOT_FOUND", "message": str(self)}


class ParseError(AirbnbError):
    """Could not parse the expected data from the page HTML."""

    def to_dict(self) -> dict:
        return {"error": True, "code": "PARSE_ERROR", "message": str(self)}
