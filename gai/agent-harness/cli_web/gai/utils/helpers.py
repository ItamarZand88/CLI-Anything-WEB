"""Shared CLI helpers for cli-web-gai."""

import json
import sys
from contextlib import contextmanager

import click

from ..core.exceptions import (
    AppError,
    BrowserError,
    CaptchaError,
    NetworkError,
    ParseError,
    RateLimitError,
    RequestTimeoutError,
)


_ERROR_CODES = {
    BrowserError: "BROWSER_ERROR",
    CaptchaError: "CAPTCHA_REQUIRED",
    NetworkError: "NETWORK_ERROR",
    ParseError: "PARSE_ERROR",
    RateLimitError: "RATE_LIMITED",
    RequestTimeoutError: "TIMEOUT",
}


def json_error(code: str, message: str, **kwargs) -> str:
    """Format an error as a JSON string."""
    return json.dumps({"error": True, "code": code, "message": message, **kwargs})


@contextmanager
def handle_errors(json_mode: bool = False):
    """Context manager that catches exceptions and exits with proper codes."""
    try:
        yield
    except KeyboardInterrupt:
        if json_mode:
            click.echo(json_error("INTERRUPTED", "Operation cancelled by user"))
        else:
            click.secho("\nInterrupted.", fg="yellow", err=True)
        sys.exit(130)
    except AppError as e:
        code = "UNKNOWN"
        for exc_cls, error_code in _ERROR_CODES.items():
            if isinstance(e, exc_cls):
                code = error_code
                break
        if json_mode:
            click.echo(json_error(code, str(e)))
        else:
            click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        if json_mode:
            click.echo(json_error("UNEXPECTED", str(e)))
        else:
            click.secho(f"Unexpected error: {e}", fg="red", err=True)
        sys.exit(2)


def print_json(data: dict):
    """Print formatted JSON to stdout."""
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))
