"""Shared CLI helpers for cli-web-unsplash."""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager

import click

from ..core.exceptions import (
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    UnsplashError,
)


def json_error(code: str, message: str, **extra) -> str:
    """Format an error as JSON string."""
    return json.dumps({"error": True, "code": code, "message": message, **extra})


@contextmanager
def handle_errors(json_mode: bool = False):
    """Context manager for consistent error handling across all commands."""
    try:
        yield
    except NotFoundError as exc:
        if json_mode:
            click.echo(json_error("NOT_FOUND", str(exc)))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except RateLimitError as exc:
        if json_mode:
            click.echo(json_error("RATE_LIMITED", str(exc), retry_after=exc.retry_after))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except ServerError as exc:
        if json_mode:
            click.echo(json_error("SERVER_ERROR", str(exc)))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(2)
    except NetworkError as exc:
        if json_mode:
            click.echo(json_error("NETWORK_ERROR", str(exc)))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(2)
    except UnsplashError as exc:
        if json_mode:
            click.echo(json_error("ERROR", str(exc)))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


def print_json(data) -> None:
    """Print data as formatted JSON."""
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


def truncate(text: str | None, length: int = 50) -> str:
    """Truncate text to a maximum length."""
    if not text:
        return ""
    return text[:length] + "..." if len(text) > length else text
