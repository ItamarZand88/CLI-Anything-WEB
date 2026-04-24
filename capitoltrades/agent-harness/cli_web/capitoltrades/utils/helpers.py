"""Shared helpers for cli-web-capitoltrades."""
from __future__ import annotations

import io
import json
import sys
from contextlib import contextmanager

import click

from ..core.exceptions import CapitoltradesError, _error_code_for


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
    except CapitoltradesError as exc:
        if json_mode:
            print_json(exc.to_dict())
        else:
            click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(1)
    except Exception as exc:
        if json_mode:
            print_json({"error": True, "code": "INTERNAL_ERROR", "message": str(exc)})
        else:
            click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(2)


def print_json(data) -> None:
    """Print data as formatted JSON to stdout."""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
