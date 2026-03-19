"""Domain exception hierarchy for cli-web-github."""


class AppError(Exception):
    """Base exception for all cli-web-github errors."""

    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

    def to_dict(self) -> dict:
        return {"error": True, "code": self.code, "message": self.message}


class AuthError(AppError):
    """Authentication failed or credentials missing."""

    def __init__(self, message: str = "Authentication required. Run: cli-web-github auth login"):
        super().__init__(message, "AUTH_ERROR")


class RateLimitError(AppError):
    """GitHub rate limit hit."""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(
            f"Rate limited by GitHub. Retry after {retry_after}s.",
            "RATE_LIMIT",
        )


class NetworkError(AppError):
    """Network or connectivity error."""

    def __init__(self, message: str):
        super().__init__(message, "NETWORK_ERROR")


class ServerError(AppError):
    """GitHub returned a 5xx error."""

    def __init__(self, status: int):
        super().__init__(f"GitHub server error: HTTP {status}", "SERVER_ERROR")


class NotFoundError(AppError):
    """Requested resource not found."""

    def __init__(self, resource: str = "resource"):
        super().__init__(f"{resource} not found", "NOT_FOUND")


class ParseError(AppError):
    """Failed to parse GitHub HTML response."""

    def __init__(self, message: str = "Failed to parse GitHub response"):
        super().__init__(message, "PARSE_ERROR")
