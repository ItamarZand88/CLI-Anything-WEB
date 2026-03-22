"""Shared CLI helpers for cli-web-booking."""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager

import click

from ..core.exceptions import (
    AuthError,
    BookingError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    WAFChallengeError,
)

ERROR_CODE_MAP = {
    AuthError: "AUTH_EXPIRED",
    WAFChallengeError: "WAF_CHALLENGE",
    RateLimitError: "RATE_LIMITED",
    NotFoundError: "NOT_FOUND",
    ServerError: "SERVER_ERROR",
    NetworkError: "NETWORK_ERROR",
}


def json_error(code: str, message: str, **extra) -> str:
    """Format an error as JSON."""
    return json.dumps({"error": True, "code": code, "message": message, **extra})


def print_json(data) -> None:
    """Print JSON output."""
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


@contextmanager
def handle_errors(json_mode: bool = False):
    """Context manager for consistent error handling across all commands."""
    try:
        yield
    except KeyboardInterrupt:
        if json_mode:
            click.echo(json_error("INTERRUPTED", "Operation cancelled"))
        sys.exit(130)
    except WAFChallengeError as e:
        if json_mode:
            click.echo(json_error("WAF_CHALLENGE", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except AuthError as e:
        if json_mode:
            click.echo(json_error("AUTH_EXPIRED", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except NotFoundError as e:
        if json_mode:
            click.echo(json_error("NOT_FOUND", str(e)))
        else:
            click.echo(f"Not found: {e}", err=True)
        sys.exit(1)
    except RateLimitError as e:
        if json_mode:
            click.echo(json_error("RATE_LIMITED", str(e),
                                  retry_after=e.retry_after))
        else:
            click.echo(f"Rate limited: {e}", err=True)
        sys.exit(2)
    except ServerError as e:
        if json_mode:
            click.echo(json_error("SERVER_ERROR", str(e)))
        else:
            click.echo(f"Server error: {e}", err=True)
        sys.exit(2)
    except NetworkError as e:
        if json_mode:
            click.echo(json_error("NETWORK_ERROR", str(e)))
        else:
            click.echo(f"Network error: {e}", err=True)
        sys.exit(2)
    except BookingError as e:
        if json_mode:
            click.echo(json_error("ERROR", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)
