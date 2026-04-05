"""Shared CLI helpers for cli-web-airbnb."""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager

import click

from ..core.exceptions import (
    AirbnbError,
    AuthError,
    BotBlockedError,
    NetworkError,
    NotFoundError,
    ParseError,
    RateLimitError,
    ServerError,
)


def json_error(code: str, message: str, **extra) -> str:
    """Format an error as a JSON string."""
    return json.dumps({"error": True, "code": code, "message": message, **extra})


@contextmanager
def handle_errors(json_mode: bool = False):
    """Context manager for consistent error handling across all commands."""
    try:
        yield
    except BotBlockedError as exc:
        if json_mode:
            click.echo(json.dumps(exc.to_dict()))
        else:
            click.echo(f"Bot blocked: {exc}", err=True)
            click.echo("Hint: Airbnb bot protection triggered. Try again later.", err=True)
        sys.exit(1)
    except AuthError as exc:
        if json_mode:
            click.echo(json.dumps(exc.to_dict()))
        else:
            click.echo(f"Auth error: {exc}", err=True)
        sys.exit(1)
    except NotFoundError as exc:
        if json_mode:
            click.echo(json.dumps(exc.to_dict()))
        else:
            click.echo(f"Not found: {exc}", err=True)
        sys.exit(1)
    except ParseError as exc:
        if json_mode:
            click.echo(json.dumps(exc.to_dict()))
        else:
            click.echo(f"Parse error: {exc}", err=True)
            click.echo("Hint: Bot protection may have blocked the request. Try again.", err=True)
        sys.exit(1)
    except RateLimitError as exc:
        retry = f" (retry after {exc.retry_after}s)" if exc.retry_after else ""
        if json_mode:
            click.echo(json.dumps(exc.to_dict()))
        else:
            click.echo(f"Rate limited{retry}: {exc}", err=True)
        sys.exit(1)
    except ServerError as exc:
        if json_mode:
            click.echo(json.dumps(exc.to_dict()))
        else:
            click.echo(f"Server error: {exc}", err=True)
        sys.exit(2)
    except NetworkError as exc:
        if json_mode:
            click.echo(json.dumps(exc.to_dict()))
        else:
            click.echo(f"Network error: {exc}", err=True)
        sys.exit(2)
    except AirbnbError as exc:
        if json_mode:
            click.echo(json.dumps(exc.to_dict()))
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
    """Truncate text to a maximum length."""
    if not text:
        return ""
    return text[:length] + "…" if len(text) > length else text
