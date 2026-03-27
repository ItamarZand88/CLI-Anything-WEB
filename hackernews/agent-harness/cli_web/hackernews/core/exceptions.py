"""Domain exception hierarchy for cli-web-hackernews."""


class AppError(Exception):
    """Base exception for all cli-web-hackernews errors."""

    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

    def to_dict(self) -> dict:
        return {"error": True, "code": self.code, "message": self.message}


class RateLimitError(AppError):
    """API rate limit hit."""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(
            f"Rate limited. Retry after {retry_after}s.",
            "RATE_LIMITED",
        )

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["retry_after"] = self.retry_after
        return d


class NetworkError(AppError):
    """Network or connectivity error."""

    def __init__(self, message: str):
        super().__init__(message, "NETWORK_ERROR")


class ServerError(AppError):
    """Remote server returned a 5xx error."""

    def __init__(self, status: int):
        self.status_code = status
        super().__init__(f"Server error: HTTP {status}", "SERVER_ERROR")


class AuthError(AppError):
    """Authentication failed or credentials missing."""

    def __init__(self, message: str = "Authentication required. Run: cli-web-hackernews auth login",
                 recoverable: bool = False):
        self.recoverable = recoverable
        super().__init__(message, "AUTH_EXPIRED")


class NotFoundError(AppError):
    """Requested resource not found."""

    def __init__(self, resource: str = "resource"):
        super().__init__(f"{resource} not found", "NOT_FOUND")
