"""Shared helpers for cli-web-${app_name}."""
from __future__ import annotations

import io
import json
import sys
from contextlib import contextmanager

import click

from ..core.exceptions import (
    ${AppName}Error,
    AuthError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    _error_code_for,
)

# Numeric exit-code contract (CONVENTIONS.md §Exit Codes):
# 0 ok | 1 unknown | 2 usage (Click) | 3 auth | 4 not-found | 5 rate-limit
# | 6 server | 7 network — lets scripts/agents branch on $? without
# parsing output.
_EXIT_CODES = {
    AuthError: 3,
    NotFoundError: 4,
    RateLimitError: 5,
    ServerError: 6,
    NetworkError: 7,
}


def _exit_code_for(exc: BaseException) -> int:
    for exc_type, code in _EXIT_CODES.items():
        if isinstance(exc, exc_type):
            return code
    return 1



# --- Windows UTF-8 fix (always include) ---
def ensure_utf8() -> None:
    """Force UTF-8 on stdout and stderr for Windows compatibility."""
    if sys.platform == "win32":
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        else:
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding="utf-8", errors="replace"
            )
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        else:
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer, encoding="utf-8", errors="replace"
            )


# --- Structured error handler ---
@contextmanager
def handle_errors(json_mode: bool = False):
    """Catch domain exceptions and emit structured output or Rich errors.

    Usage:
        with handle_errors(json_mode=ctx.obj.get("json")):
            do_something()
    """
    try:
        yield
    except KeyboardInterrupt:
        raise SystemExit(130)
    except (click.exceptions.Exit, click.UsageError):
        raise
    except ${AppName}Error as exc:
        if json_mode:
            print_json(exc.to_dict())
        else:
            click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(_exit_code_for(exc))
    except Exception as exc:
        if json_mode:
            print_json({"error": True, "code": "INTERNAL_ERROR", "message": str(exc)})
        else:
            click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(1)


def print_json(data) -> None:
    """Print data as formatted JSON to stdout."""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
