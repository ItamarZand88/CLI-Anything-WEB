"""Domain-specific exception hierarchy for cli-web-unsplash."""


class UnsplashError(Exception):
    """Base for all Unsplash CLI errors."""

    def to_dict(self) -> dict:
        return {"error": True, "code": error_code_for(self), "message": str(self)}


class RateLimitError(UnsplashError):
    """429 — retry with backoff."""

    def __init__(self, message: str, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(message)

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        return d


class NetworkError(UnsplashError):
    """Connection/DNS/timeout errors."""


class ServerError(UnsplashError):
    """5xx responses."""

    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(UnsplashError):
    """404 — resource not found."""


# --- JSON error code mapping (matches utils/helpers.py conventions) ---

EXCEPTION_CODE_MAP = {
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
