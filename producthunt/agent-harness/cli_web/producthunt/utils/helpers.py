"""Shared helpers for cli-web-producthunt commands."""

import json
import sys
from contextlib import contextmanager

from ..core.exceptions import AppError, AuthError


@contextmanager
def handle_errors(json_mode: bool = False):
    """Context manager that catches AppError and prints to stderr or JSON.

    Exit codes:
        0 — success
        1 — application error
        2 — auth error
        130 — keyboard interrupt
    """
    try:
        yield
    except KeyboardInterrupt:
        if json_mode:
            print(json.dumps({"error": True, "code": "INTERRUPTED", "message": "Interrupted"}))
        else:
            print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except AuthError as exc:
        if json_mode:
            print(json.dumps(exc.to_dict()))
        else:
            print(f"Auth error: {exc}", file=sys.stderr)
        sys.exit(2)
    except AppError as exc:
        if json_mode:
            print(json.dumps(exc.to_dict()))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
