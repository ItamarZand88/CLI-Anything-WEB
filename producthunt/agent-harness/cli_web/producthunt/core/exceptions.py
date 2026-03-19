"""Domain-specific exception hierarchy for cli-web-producthunt."""


class AppError(Exception):
    """Base for all producthunt CLI errors."""

    def to_dict(self):
        return {"error": True, "code": "UNKNOWN", "message": str(self)}


class AuthError(AppError):
    def __init__(self, message: str, recoverable: bool = True):
        self.recoverable = recoverable
        super().__init__(message)

    def to_dict(self):
        return {"error": True, "code": "AUTH_EXPIRED", "message": str(self)}


class RateLimitError(AppError):
    def __init__(self, message: str, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(message)

    def to_dict(self):
        return {"error": True, "code": "RATE_LIMITED", "message": str(self),
                "retry_after": self.retry_after}


class NetworkError(AppError):
    def to_dict(self):
        return {"error": True, "code": "NETWORK_ERROR", "message": str(self)}


class ServerError(AppError):
    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)

    def to_dict(self):
        return {"error": True, "code": "SERVER_ERROR", "message": str(self)}


class NotFoundError(AppError):
    def to_dict(self):
        return {"error": True, "code": "NOT_FOUND", "message": str(self)}


class GraphQLError(AppError):
    """GraphQL-specific error returned by the API."""

    def to_dict(self):
        return {"error": True, "code": "GRAPHQL_ERROR", "message": str(self)}
