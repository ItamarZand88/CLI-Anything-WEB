"""Domain exception hierarchy for cli-web-stitch."""


class StitchError(Exception):
    """Base exception for all Stitch CLI errors."""


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
