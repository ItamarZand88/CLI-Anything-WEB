"""Domain-specific exception hierarchy for cli-web-amazon."""


class AmazonError(Exception):
    """Base exception for all amazon CLI errors."""

    def to_dict(self) -> dict:
        return {"error": True, "code": "ERROR", "message": str(self)}


class NetworkError(AmazonError):
    """Connection failed, DNS error, timeout."""

    def to_dict(self) -> dict:
        return {"error": True, "code": "NETWORK_ERROR", "message": str(self)}


class RateLimitError(AmazonError):
    """HTTP 429 — too many requests."""
    def __init__(self, message: str, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(message)

    def to_dict(self) -> dict:
        d = {"error": True, "code": "RATE_LIMITED", "message": str(self)}
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        return d


class ParsingError(AmazonError):
    """HTML/JSON response could not be parsed — site structure may have changed."""

    def to_dict(self) -> dict:
        return {"error": True, "code": "PARSING_ERROR", "message": str(self)}


class NotFoundError(AmazonError):
    """Resource not found (product ASIN, category, etc.)."""

    def to_dict(self) -> dict:
        return {"error": True, "code": "NOT_FOUND", "message": str(self)}


class ServerError(AmazonError):
    """Amazon returned 5xx."""
    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)

    def to_dict(self) -> dict:
        return {"error": True, "code": "SERVER_ERROR", "message": str(self),
                "status_code": self.status_code}


EXCEPTION_CODE_MAP = {
    RateLimitError: "RATE_LIMITED",
    NotFoundError: "NOT_FOUND",
    ServerError: "SERVER_ERROR",
    NetworkError: "NETWORK_ERROR",
    ParsingError: "PARSING_ERROR",
}


def error_code_for(exc: Exception) -> str:
    """Get the JSON error code string for an exception."""
    for exc_type, code in EXCEPTION_CODE_MAP.items():
        if isinstance(exc, exc_type):
            return code
    return "UNKNOWN_ERROR"
