"""Domain exception hierarchy for cli-web-stitch."""


class StitchError(Exception):
    """Base exception for all Stitch CLI errors."""

    def to_dict(self) -> dict:
        return {"error": True, "code": error_code_for(self), "message": str(self)}


class AuthError(StitchError):
    """Authentication or authorization failure."""

    def __init__(self, message: str = "Authentication failed", recoverable: bool = True):
        super().__init__(message)
        self.recoverable = recoverable


class RateLimitError(StitchError):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: "float | None" = None):
        super().__init__(message)
        self.retry_after = retry_after

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        return d


class NetworkError(StitchError):
    """Network connectivity failure."""


class ServerError(StitchError):
    """Server-side error (5xx)."""

    def __init__(self, message: str = "Server error", status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(StitchError):
    """Requested resource not found."""


class RPCError(StitchError):
    """Google batchexecute RPC protocol error."""


# --- JSON error code mapping (matches utils/helpers.py conventions) ---

EXCEPTION_CODE_MAP = {
    AuthError: "AUTH_ERROR",
    RateLimitError: "RATE_LIMITED",
    NetworkError: "NETWORK_ERROR",
    ServerError: "SERVER_ERROR",
    NotFoundError: "NOT_FOUND",
    RPCError: "RPC_ERROR",
}


def error_code_for(exc: Exception) -> str:
    """Get the JSON error code string for an exception."""
    for exc_type, code in EXCEPTION_CODE_MAP.items():
        if isinstance(exc, exc_type):
            return code
    return "STITCH_ERROR"
