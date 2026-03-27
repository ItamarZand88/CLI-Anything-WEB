"""
Reference: Domain-Specific Exception Hierarchy
================================================
Every generated CLI must have core/exceptions.py with typed exceptions.
The client maps HTTP status codes to these exceptions, enabling:
- Proper retry logic (only retry on recoverable errors)
- Structured JSON error output (error code from exception type)
- Correct CLI exit codes (auth=1, server=2, etc.)

Adapt class names to the target app (e.g., NotebookLMError, FutbinError).
"""


class AppError(Exception):
    """Base exception for all CLI errors."""

    def to_dict(self):
        return {
            "error": True,
            "code": error_code_for(self),
            "message": str(self),
        }


class AuthError(AppError):
    """Authentication failed — expired cookies, invalid tokens, session timeout.

    Args:
        recoverable: If True, client should refresh tokens and retry once.
                     If False (e.g., cookies deleted), user must re-login.
    """
    def __init__(self, message: str, recoverable: bool = True):
        self.recoverable = recoverable
        super().__init__(message)


class RateLimitError(AppError):
    """Server returned 429 — too many requests.

    Args:
        retry_after: Seconds to wait before retrying (from Retry-After header).
    """
    def __init__(self, message: str, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(message)

    def to_dict(self):
        d = super().to_dict()
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        return d


class NetworkError(AppError):
    """Connection failed — DNS resolution, TCP connect, TLS handshake."""


class ServerError(AppError):
    """Server returned 5xx — internal error, bad gateway, service unavailable.

    Args:
        status_code: The HTTP status code (500, 502, 503, etc.)
    """
    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found (HTTP 404)."""


class ValidationError(AppError):
    """Invalid input — bad parameters, missing required fields."""


# --- Domain-specific extensions (examples) ---

class ArtifactNotReadyError(AppError):
    """Artifact generation still in progress — poll again later."""


class SourceProcessingError(AppError):
    """Source failed to process (e.g., PDF parsing error on server side)."""


# --- HTTP status code mapping (used in client.py) ---

STATUS_CODE_MAP = {
    401: lambda msg: AuthError(msg, recoverable=True),
    403: lambda msg: AuthError(msg, recoverable=True),
    404: lambda msg: NotFoundError(msg),
    # 429 handled separately below to extract Retry-After header
    # 5xx handled by range check in client
}


def raise_for_status(response) -> None:
    """Map HTTP status to typed exception. Call after every API request."""
    if response.status_code < 400:
        return

    text = response.text[:200]
    msg = f"HTTP {response.status_code}: {text}"

    # Check specific status codes first
    if response.status_code in STATUS_CODE_MAP:
        raise STATUS_CODE_MAP[response.status_code](msg)

    # Extract retry-after for 429
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        raise RateLimitError(msg, retry_after=float(retry_after) if retry_after else None)

    # 5xx range
    if 500 <= response.status_code < 600:
        raise ServerError(msg, status_code=response.status_code)

    # 4xx fallback
    raise AppError(msg)


# --- JSON error output mapping (used in commands) ---

EXCEPTION_CODE_MAP = {
    AuthError: "AUTH_EXPIRED",
    RateLimitError: "RATE_LIMITED",
    NotFoundError: "NOT_FOUND",
    ServerError: "SERVER_ERROR",
    NetworkError: "NETWORK_ERROR",
    ValidationError: "VALIDATION_ERROR",
}


def error_code_for(exc: AppError) -> str:
    """Get the JSON error code string for an exception."""
    for exc_type, code in EXCEPTION_CODE_MAP.items():
        if isinstance(exc, exc_type):
            return code
    return "UNKNOWN_ERROR"
