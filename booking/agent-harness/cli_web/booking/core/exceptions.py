"""Domain-specific exception hierarchy for cli-web-booking."""


class BookingError(Exception):
    """Base for all Booking.com CLI errors."""

    def to_dict(self) -> dict:
        return {"error": True, "code": error_code_for(self), "message": str(self)}


class AuthError(BookingError):
    """WAF cookie expired or missing."""

    def __init__(self, message: str, recoverable: bool = True):
        self.recoverable = recoverable
        super().__init__(message)


class RateLimitError(BookingError):
    """Too many requests — retry with backoff."""

    def __init__(self, message: str, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(message)

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        return d


class NetworkError(BookingError):
    """Connection, DNS, or timeout errors."""


class ServerError(BookingError):
    """5xx responses from Booking.com."""

    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(BookingError):
    """404 — property or destination not found."""


class WAFChallengeError(AuthError):
    """AWS WAF challenge page returned instead of content."""

    def __init__(self):
        super().__init__(
            "WAF challenge detected. Run: cli-web-booking auth login",
            recoverable=True,
        )


# --- JSON error code mapping (matches utils/helpers.py conventions) ---

EXCEPTION_CODE_MAP = {
    WAFChallengeError: "WAF_CHALLENGE",
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
