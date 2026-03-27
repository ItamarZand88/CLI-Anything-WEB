"""Shared helpers for cli-web-hackernews."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import sys

import click

from cli_web.hackernews.core.exceptions import AppError


@contextlib.contextmanager
def handle_errors(json_mode: bool = False):
    """Context manager for consistent error handling in commands."""
    try:
        yield
    except AppError as exc:
        if json_mode:
            click.echo(json.dumps(exc.to_dict()), err=False)
        else:
            click.echo(f"Error: {exc.message}", err=True)
        sys.exit(1)
    except Exception as exc:
        if json_mode:
            click.echo(json.dumps({
                "error": True,
                "code": "UNEXPECTED_ERROR",
                "message": str(exc),
            }), err=False)
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


def _resolve_cli(name: str) -> str:
    """Find the CLI binary path for subprocess tests."""
    # Check if forced to use installed version
    if os.environ.get("CLI_WEB_FORCE_INSTALLED"):
        path = shutil.which(name)
        if path:
            return path
        raise FileNotFoundError(f"{name} not found in PATH")

    # Try which first
    path = shutil.which(name)
    if path:
        return path

    # Fallback to python -m
    return f"{sys.executable} -m cli_web.hackernews"
