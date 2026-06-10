"""Shared helpers for cli-web-worldcup."""

from __future__ import annotations

import io
import json
import os
import sys
from contextlib import contextmanager

import click

from ..core.exceptions import (
    AuthError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    WorldcupError,
)

ODDS_KEY_ENV = "CLI_WEB_WORLDCUP_ODDS_API_KEY"


def odds_api_key(explicit: str | None = None) -> str | None:
    """Resolve the Odds API key: explicit flag wins, else the env var."""
    return explicit or os.environ.get(ODDS_KEY_ENV)


def resolve_team(query: str, teams: list) -> dict:
    """Resolve a team by id, abbreviation, or name (case-insensitive).

    ``teams`` is a list of normalized team dicts (Team.to_dict()). Raises
    NotFoundError on no match, or on an ambiguous name substring.
    """
    q = query.strip().lower()
    for t in teams:
        if str(t.get("id")) == query or t.get("abbreviation", "").lower() == q:
            return t
    exact = [t for t in teams if t.get("name", "").lower() == q]
    if exact:
        return exact[0]
    partial = [t for t in teams if q in t.get("name", "").lower()]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        names = ", ".join(t.get("name", "") for t in partial[:8])
        raise NotFoundError(f"Ambiguous team '{query}', matches: {names}")
    raise NotFoundError(f"No team matching '{query}' (try the 3-letter code, e.g. MEX)")


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
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        else:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


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
        raise SystemExit(130) from None
    except (click.exceptions.Exit, click.UsageError):
        raise
    except WorldcupError as exc:
        if json_mode:
            print_json(exc.to_dict())
        else:
            click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(_exit_code_for(exc)) from None
    except Exception as exc:
        if json_mode:
            print_json({"error": True, "code": "INTERNAL_ERROR", "message": str(exc)})
        else:
            click.secho(f"Error: {exc}", fg="red", err=True)
        raise SystemExit(1) from None


def print_json(data) -> None:
    """Print data as formatted JSON to stdout."""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
