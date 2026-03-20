"""Domain-specific exception hierarchy for cli-web-unsplash."""


class UnsplashError(Exception):
    """Base for all Unsplash CLI errors."""


class RateLimitError(UnsplashError):
    """429 — retry with backoff."""

    def __init__(self, message: str, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(message)


class NetworkError(UnsplashError):
    """Connection/DNS/timeout errors."""


class ServerError(UnsplashError):
    """5xx responses."""

    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(UnsplashError):
    """404 — resource not found."""
