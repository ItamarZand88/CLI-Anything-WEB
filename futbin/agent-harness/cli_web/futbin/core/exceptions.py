"""Domain exception hierarchy for cli-web-* CLIs.

CANONICAL SOURCE — synced into each CLI at ``core/exceptions.py`` by
``scripts/sync-shared.py``. Do NOT edit the per-CLI copies; edit this file and
re-run the sync. App-specific *messages* belong at the raise-site, not here —
this module defines only the shared exception vocabulary and JSON error codes.

Hierarchy (per CLAUDE.md):
    AppError
    ├── AuthError            (recoverable flag)   └── WAFChallengeError
    ├── RateLimitError       (retry_after)
    ├── NetworkError
    ├── ServerError          (status_code)
    ├── NotFoundError
    ├── ParseError
    ├── RPCError
    ├── ValidationError      (alias: InvalidInputError)
    ├── BotBlockedError                            └── CaptchaError
    ├── BrowserError
    ├── RequestTimeoutError  (timeout_seconds)
    └── SubmitError
"""

from __future__ import annotations


def error_code_for(exc: Exception) -> str:
    """Map an exception instance to its JSON error-code string.

    Iterates most-specific first; returns ``UNKNOWN_ERROR`` if unmapped.
    """
    for exc_type, code in EXCEPTION_CODE_MAP.items():
        if isinstance(exc, exc_type):
            return code
    return "UNKNOWN_ERROR"


# Backwards-compatible alias (some CLIs imported the private name).
_error_code_for = error_code_for


class AppError(Exception):
    """Base exception for all cli-web errors."""

    def __init__(self, message: str = "") -> None:
        # Expose ``.message`` for call sites that read it directly.
        self.message = message
        super().__init__(message)

    def to_dict(self) -> dict:
        """Structured error dict for ``--json`` output."""
        return {"error": True, "code": error_code_for(self), "message": str(self)}


class AuthError(AppError):
    """Authentication required, expired, or rejected (401/403).

    Args:
        recoverable: if True, the client may refresh credentials and retry once.
    """

    def __init__(self, message: str = "Authentication required — run `auth login`", recoverable: bool = True) -> None:
        self.recoverable = recoverable
        super().__init__(message)


class RateLimitError(AppError):
    """Rate limit exceeded (429).

    Args:
        retry_after: seconds to wait before retrying (from ``Retry-After``).
    """

    def __init__(self, message: str = "Rate limit exceeded", retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(message)

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        return d


class NetworkError(AppError):
    """Connection failure — DNS, TCP, TLS, or timeout."""


class ServerError(AppError):
    """Remote server returned a 5xx response.

    Args:
        status_code: the HTTP status code (500, 502, 503, ...).
    """

    def __init__(self, message: str = "Server error", status_code: int = 500) -> None:
        self.status_code = status_code
        super().__init__(message)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["status_code"] = self.status_code
        return d


class NotFoundError(AppError):
    """Requested resource does not exist (404)."""


class ParseError(AppError):
    """Could not parse the expected data from the response or page HTML."""


class RPCError(AppError):
    """Error in an RPC protocol layer (e.g. Google batchexecute).

    Args:
        code: optional protocol-level error code, if the RPC layer provides one.
    """

    def __init__(self, message: str, code: int | None = None) -> None:
        self.code = code
        super().__init__(message)


class ValidationError(AppError):
    """Invalid user input or command arguments."""


# Alias — some CLIs raise this name.
InvalidInputError = ValidationError


class BotBlockedError(AppError):
    """Request blocked by bot-protection / WAF / anti-automation (403)."""


class WAFChallengeError(AuthError):
    """A WAF / anti-bot challenge page was returned instead of content.

    Subclass of AuthError because the remedy is re-authentication; recoverable
    so the client can attempt to refresh the challenge token once.
    """

    def __init__(
        self,
        message: str = "Bot/WAF challenge detected — re-authenticate with `auth login`",
        recoverable: bool = True,
    ) -> None:
        super().__init__(message, recoverable=recoverable)


class BrowserError(AppError):
    """Browser launch or navigation failure (browser-driven CLIs)."""


class CaptchaError(BotBlockedError):
    """A CAPTCHA challenge was presented."""


class RequestTimeoutError(AppError):
    """Operation did not complete within the timeout window.

    Named to avoid shadowing the builtin ``TimeoutError``.

    Args:
        timeout_seconds: the timeout that elapsed, for diagnostics.
    """

    def __init__(self, message: str = "Request timed out", timeout_seconds: float = 0) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(message)


class SubmitError(AppError):
    """A write / submit operation failed."""


# --- JSON error-code mapping ------------------------------------------------
# Order matters: most-specific subclasses MUST precede their parents so
# error_code_for() returns the narrowest matching code.
EXCEPTION_CODE_MAP = {
    WAFChallengeError: "WAF_CHALLENGE",
    CaptchaError: "CAPTCHA",
    AuthError: "AUTH_EXPIRED",
    BotBlockedError: "BOT_BLOCKED",
    RateLimitError: "RATE_LIMITED",
    NotFoundError: "NOT_FOUND",
    ServerError: "SERVER_ERROR",
    NetworkError: "NETWORK_ERROR",
    RPCError: "RPC_ERROR",
    ParseError: "PARSE_ERROR",
    ValidationError: "INVALID_INPUT",
    BrowserError: "BROWSER_ERROR",
    RequestTimeoutError: "TIMEOUT",
    SubmitError: "SUBMIT_ERROR",
}


# --- HTTP status -> typed exception -----------------------------------------
_CODE_MAP = {
    401: lambda msg: AuthError(msg, recoverable=True),
    403: lambda msg: AuthError(msg, recoverable=True),
    404: lambda msg: NotFoundError(msg),
    # 429 handled separately below to extract the Retry-After header.
}


def raise_for_status(response) -> None:
    """Map an HTTP response status to a typed exception. Call after each request."""
    if response.status_code < 400:
        return

    text = getattr(response, "text", "")[:200]
    msg = f"HTTP {response.status_code}: {text}"

    if response.status_code in _CODE_MAP:
        raise _CODE_MAP[response.status_code](msg)

    if response.status_code == 429:
        retry_after = None
        if hasattr(response, "headers"):
            raw = response.headers.get("Retry-After")
            if raw:
                try:
                    retry_after = float(raw)
                except ValueError:
                    retry_after = None  # HTTP-date format, ignore
        raise RateLimitError(msg, retry_after=retry_after)

    if 500 <= response.status_code < 600:
        raise ServerError(msg, status_code=response.status_code)

    raise AppError(msg)
