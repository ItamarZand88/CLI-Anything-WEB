"""Shared helpers for cli-web-codewiki."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import sys

import click

from ..core.exceptions import AppError, RateLimitError, error_code_for


@contextlib.contextmanager
def handle_errors(json_mode: bool = False):
    """Context manager for consistent error handling in commands."""
    try:
        yield
    except KeyboardInterrupt:
        if not json_mode:
            click.echo("\nInterrupted.", err=True)
        sys.exit(130)
    except click.exceptions.Exit:
        raise
    except click.UsageError:
        raise
    except AppError as exc:
        code = error_code_for(exc)
        if json_mode:
            err = {"error": True, "code": code, "message": str(exc)}
            if isinstance(exc, RateLimitError) and exc.retry_after is not None:
                err["retry_after"] = exc.retry_after
            click.echo(json.dumps(err))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        if json_mode:
            click.echo(json.dumps({
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": str(exc),
            }))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(2)


def _resolve_cli(name: str = "cli-web-codewiki") -> str:
    """Find the CLI binary path for subprocess tests."""
    if os.environ.get("CLI_WEB_FORCE_INSTALLED"):
        path = shutil.which(name)
        if path:
            return path
        raise FileNotFoundError(f"{name} not found in PATH")

    path = shutil.which(name)
    if path:
        return path

    return sys.executable
