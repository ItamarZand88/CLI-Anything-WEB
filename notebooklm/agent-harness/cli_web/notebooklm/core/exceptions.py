"""Domain-specific exception hierarchy for cli-web-notebooklm."""


class NotebookLMError(Exception):
    """Base exception for all NotebookLM CLI errors."""


class AuthError(NotebookLMError):
    """Authentication failed — expired cookies, invalid tokens, session timeout.

    Args:
        recoverable: If True, client should refresh tokens and retry once.
    """
    def __init__(self, message: str, recoverable: bool = True):
        self.recoverable = recoverable
        super().__init__(message)


class RateLimitError(NotebookLMError):
    """Server returned 429 — too many requests.

    Args:
        retry_after: Seconds to wait before retrying.
    """
    def __init__(self, message: str, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(message)


class NetworkError(NotebookLMError):
    """Connection failed — DNS, TCP, TLS, or timeout."""


class ServerError(NotebookLMError):
    """Server returned 5xx.

    Args:
        status_code: The HTTP status code.
    """
    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(NotebookLMError):
    """Resource not found (HTTP 404)."""


class RPCError(NotebookLMError):
    """Error in the batchexecute RPC protocol layer."""


# --- JSON error code mapping ---

EXCEPTION_CODE_MAP = {
    AuthError: "AUTH_EXPIRED",
    RateLimitError: "RATE_LIMITED",
    NotFoundError: "NOT_FOUND",
    ServerError: "SERVER_ERROR",
    NetworkError: "NETWORK_ERROR",
    RPCError: "RPC_ERROR",
}


def error_code_for(exc: Exception) -> str:
    """Get the JSON error code string for an exception."""
    for exc_type, code in EXCEPTION_CODE_MAP.items():
        if isinstance(exc, exc_type):
            return code
    return "UNKNOWN_ERROR"
