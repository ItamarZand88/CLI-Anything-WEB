"""Shared CLI helpers for cli-web-tripadvisor."""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager

import click

from ..core.exceptions import (
    AuthError,
    NetworkError,
    NotFoundError,
    ParseError,
    RateLimitError,
    ServerError,
    TripAdvisorError,
)


def json_error(code: str, message: str, **extra) -> str:
    """Format an error as a JSON string for --json mode output."""
    return json.dumps({"error": True, "code": code, "message": message, **extra})


@contextmanager
def handle_errors(json_mode: bool = False):
    """Context manager for consistent error handling across all commands.

    Exit codes:
      1 = user-level error (not found, auth block, parse failure)
      2 = system-level error (network failure, server error)
      130 = keyboard interrupt (Ctrl+C)
    """
    try:
        yield
    except AuthError as exc:
        if json_mode:
            click.echo(json_error("AUTH_EXPIRED", str(exc)))
        else:
            click.echo(f"Auth/access error: {exc}", err=True)
            click.echo(
                "Hint: DataDome bot protection may have triggered. "
                "curl_cffi Chrome impersonation should bypass it — "
                "if errors persist, try again after a short delay.",
                err=True,
            )
        sys.exit(1)
    except NotFoundError as exc:
        if json_mode:
            click.echo(json_error("NOT_FOUND", str(exc)))
        else:
            click.echo(f"Not found: {exc}", err=True)
        sys.exit(1)
    except ParseError as exc:
        if json_mode:
            click.echo(json_error("PARSE_ERROR", str(exc)))
        else:
            click.echo(f"Parse error: {exc}", err=True)
            click.echo(
                "Hint: Bot protection may have returned a challenge page. "
                "Try again in a few seconds.",
                err=True,
            )
        sys.exit(1)
    except RateLimitError as exc:
        retry = f" (retry after {exc.retry_after}s)" if exc.retry_after else ""
        if json_mode:
            click.echo(json_error("RATE_LIMITED", str(exc), retry_after=exc.retry_after))
        else:
            click.echo(f"Rate limited{retry}: {exc}", err=True)
        sys.exit(1)
    except ServerError as exc:
        if json_mode:
            click.echo(json_error("SERVER_ERROR", str(exc), status_code=exc.status_code))
        else:
            click.echo(f"Server error: {exc}", err=True)
        sys.exit(2)
    except NetworkError as exc:
        if json_mode:
            click.echo(json_error("NETWORK_ERROR", str(exc)))
        else:
            click.echo(f"Network error: {exc}", err=True)
        sys.exit(2)
    except TripAdvisorError as exc:
        if json_mode:
            click.echo(json_error("ERROR", str(exc)))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


def resolve_json_mode(json_mode: bool, ctx: click.Context | None = None) -> bool:
    """Merge command-level --json with parent context json flag."""
    if json_mode:
        return True
    if ctx is not None:
        obj = ctx.obj or {}
        return bool(obj.get("json", False))
    return False


def print_json(data) -> None:
    """Print data as formatted JSON to stdout."""
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


def truncate(text: str | None, length: int = 60) -> str:
    """Truncate text to a maximum display length with ellipsis."""
    if not text:
        return ""
    return text[:length] + "…" if len(text) > length else text


def format_rating(rating: str | None, review_count: int | None) -> str:
    """Format rating and review count for display."""
    if not rating:
        return "—"
    if review_count:
        return f"{rating} ({review_count:,})"
    return rating
