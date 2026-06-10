"""Domain-specific exception hierarchy for cli-web-gai."""


class GAIError(Exception):
    """Base exception for all cli-web-gai errors."""

    def to_dict(self) -> dict:
        return {"error": True, "code": error_code_for(self), "message": str(self)}


class BrowserError(GAIError):
    """Browser launch or navigation failure."""


class TimeoutError(GAIError):
    """Response did not arrive within the timeout window."""

    def __init__(self, message: str, timeout_seconds: float = 0):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


class RateLimitError(GAIError):
    """Google rate-limiting detected."""


class NetworkError(GAIError):
    """Network or connection failure."""


class ServerError(GAIError):
    """Google returned a server-side error page."""


class NotFoundError(GAIError):
    """Requested resource or result was not found."""


class AuthError(GAIError):
    """Authentication failure (unused — cli-web-gai requires no auth)."""


class ParseError(GAIError):
    """Failed to parse AI Mode response from the page."""


class CaptchaError(GAIError):
    """Google presented a CAPTCHA challenge."""


# --- JSON error code mapping (matches utils/helpers.py conventions) ---

EXCEPTION_CODE_MAP = {
    BrowserError: "BROWSER_ERROR",
    CaptchaError: "CAPTCHA_REQUIRED",
    AuthError: "AUTH_ERROR",
    NetworkError: "NETWORK_ERROR",
    NotFoundError: "NOT_FOUND",
    ServerError: "SERVER_ERROR",
    ParseError: "PARSE_ERROR",
    RateLimitError: "RATE_LIMITED",
    TimeoutError: "TIMEOUT",
}


def error_code_for(exc: Exception) -> str:
    """Get the JSON error code string for an exception."""
    for exc_type, code in EXCEPTION_CODE_MAP.items():
        if isinstance(exc, exc_type):
            return code
    return "UNKNOWN"
