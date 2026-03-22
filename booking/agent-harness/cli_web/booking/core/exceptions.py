"""Domain-specific exception hierarchy for cli-web-booking."""


class BookingError(Exception):
    """Base for all Booking.com CLI errors."""


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
