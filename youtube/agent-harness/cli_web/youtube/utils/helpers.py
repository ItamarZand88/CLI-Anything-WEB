"""Shared helpers for cli-web-youtube."""

from __future__ import annotations

import contextlib
import json
import sys

import click
from cli_web.youtube.core.exceptions import RateLimitError, YouTubeError


@contextlib.contextmanager
def handle_errors(json_mode: bool = False):
    """Context manager for consistent error handling in commands."""
    try:
        yield
    except YouTubeError as exc:
        d = exc.to_dict()
        if isinstance(exc, RateLimitError) and exc.retry_after is not None:
            d["retry_after"] = exc.retry_after
        if json_mode:
            click.echo(json.dumps(d))
        else:
            click.echo(f"Error: {exc.message}", err=True)
        sys.exit(1)
    except Exception as exc:
        if json_mode:
            click.echo(
                json.dumps(
                    {
                        "error": True,
                        "code": "UNEXPECTED_ERROR",
                        "message": str(exc),
                    }
                )
            )
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


def resolve_json_mode(use_json: bool) -> bool:
    """Resolve --json flag, checking parent context too."""
    if use_json:
        return True
    ctx = click.get_current_context(silent=True)
    if ctx and ctx.obj:
        return ctx.obj.get("json", False)
    return False


def print_json(data) -> None:
    """Print data as formatted JSON."""
    click.echo(json.dumps(data, indent=2, default=str))


def print_error_json(exc: YouTubeError) -> None:
    """Print a YouTubeError as JSON."""
    click.echo(json.dumps(exc.to_dict()))
