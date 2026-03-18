"""Domain-specific exception hierarchy for cli-web-futbin."""


class FutbinError(Exception):
    """Base exception for all futbin CLI errors."""


class AuthError(FutbinError):
    """Authentication issue (cookies expired, login required)."""
    def __init__(self, message: str, recoverable: bool = True):
        self.recoverable = recoverable
        super().__init__(message)


class NetworkError(FutbinError):
    """Connection failed, DNS error, timeout."""


class RateLimitError(FutbinError):
    """HTTP 429 — too many requests."""
    def __init__(self, message: str, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(message)


class ParsingError(FutbinError):
    """HTML/JSON response could not be parsed — site structure may have changed."""


class NotFoundError(FutbinError):
    """Resource not found (player, SBC, evolution)."""


class ServerError(FutbinError):
    """FUTBIN returned 5xx."""
    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)


class InvalidInputError(FutbinError):
    """Invalid parameter (bad year, unknown position, etc.)."""


EXCEPTION_CODE_MAP = {
    AuthError: "AUTH_ERROR",
    RateLimitError: "RATE_LIMITED",
    NotFoundError: "NOT_FOUND",
    ServerError: "SERVER_ERROR",
    NetworkError: "NETWORK_ERROR",
    ParsingError: "PARSING_ERROR",
    InvalidInputError: "INVALID_INPUT",
}


def error_code_for(exc: Exception) -> str:
    """Get the JSON error code string for an exception."""
    for exc_type, code in EXCEPTION_CODE_MAP.items():
        if isinstance(exc, exc_type):
            return code
    return "UNKNOWN_ERROR"
