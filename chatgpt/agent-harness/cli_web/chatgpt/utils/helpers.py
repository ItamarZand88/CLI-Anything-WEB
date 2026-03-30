"""Shared CLI helpers for cli-web-chatgpt."""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager

import click

from ..core.exceptions import (
    AuthError,
    ChatGPTError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
)


def json_error(code: str, message: str, **extra) -> str:
    return json.dumps({"error": True, "code": code, "message": message, **extra})


@contextmanager
def handle_errors(json_mode: bool = False):
    try:
        yield
    except AuthError as exc:
        if json_mode:
            click.echo(json_error("AUTH_EXPIRED", str(exc)))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
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
    except ChatGPTError as exc:
        if json_mode:
            click.echo(json_error("ERROR", str(exc)))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


def print_json(data) -> None:
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


def truncate(text: str | None, length: int = 60) -> str:
    if not text:
        return ""
    return text[:length] + "..." if len(text) > length else text
