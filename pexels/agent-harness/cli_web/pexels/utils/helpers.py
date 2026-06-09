"""Shared CLI helpers for cli-web-pexels."""

import json
import sys
from contextlib import contextmanager

import click

from ..core.exceptions import AppError, RateLimitError, error_code_for


@contextmanager
def handle_errors(json_mode: bool = False):
    """Context manager that catches exceptions and outputs proper error messages."""
    try:
        yield
    except KeyboardInterrupt:
        sys.exit(130)
    except click.exceptions.Exit:
        raise
    except click.UsageError:
        raise
    except Exception as exc:
        code = error_code_for(exc)
        exit_code = 1 if isinstance(exc, AppError) else 2
        if json_mode:
            err_dict = {"error": True, "code": code, "message": str(exc)}
            if isinstance(exc, RateLimitError) and exc.retry_after is not None:
                err_dict["retry_after"] = exc.retry_after
            click.echo(json.dumps(err_dict))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(exit_code)


def sanitize_filename(name: str, max_length: int = 240) -> str:
    """Convert a title to a safe filename."""
    if not name or not name.strip():
        return "untitled"
    invalid = set('/\\:*?"<>|')
    safe = "".join(c if c not in invalid else "_" for c in name).strip(". ")
    return safe[:max_length] if safe else "untitled"
