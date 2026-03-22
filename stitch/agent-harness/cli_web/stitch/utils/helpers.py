"""Shared helpers for cli-web-stitch."""
import json
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Optional

import click

from ..core.exceptions import (
    AuthError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    RPCError,
    ServerError,
    StitchError,
)

CONFIG_DIR = Path.home() / ".config" / "cli-web-stitch"
CONTEXT_FILE = CONFIG_DIR / "context.json"


# ── Error handling ────────────────────────────────────────────────────

_EXCEPTION_CODE_MAP = {
    AuthError: "AUTH_ERROR",
    RateLimitError: "RATE_LIMITED",
    NetworkError: "NETWORK_ERROR",
    ServerError: "SERVER_ERROR",
    NotFoundError: "NOT_FOUND",
    RPCError: "RPC_ERROR",
    StitchError: "STITCH_ERROR",
}


@contextmanager
def handle_errors(json_mode: bool = False):
    """Context manager that catches exceptions and formats error output.

    JSON mode outputs ``{"error": true, "code": "...", "message": "..."}``.
    Exit codes: 1 = user/expected error, 2 = internal error.
    """
    try:
        yield
    except KeyboardInterrupt:
        if json_mode:
            _print_json_error("INTERRUPTED", "Interrupted by user")
        raise SystemExit(130)
    except click.exceptions.Exit:
        raise
    except click.UsageError as exc:
        if json_mode:
            _print_json_error("USAGE_ERROR", str(exc))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
    except AuthError as exc:
        if json_mode:
            _print_json_error("AUTH_ERROR", str(exc))
        else:
            click.echo(f"Auth error: {exc}", err=True)
        raise SystemExit(1)
    except NotFoundError as exc:
        if json_mode:
            _print_json_error("NOT_FOUND", str(exc))
        else:
            click.echo(f"Not found: {exc}", err=True)
        raise SystemExit(1)
    except RateLimitError as exc:
        if json_mode:
            _print_json_error("RATE_LIMITED", str(exc))
        else:
            click.echo(f"Rate limited: {exc}", err=True)
        raise SystemExit(1)
    except (NetworkError, ServerError, RPCError, StitchError) as exc:
        code = _EXCEPTION_CODE_MAP.get(type(exc), "STITCH_ERROR")
        if json_mode:
            _print_json_error(code, str(exc))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
    except Exception as exc:
        if json_mode:
            _print_json_error("INTERNAL_ERROR", str(exc))
        else:
            click.echo(f"Internal error: {exc}", err=True)
        raise SystemExit(2)


def _print_json_error(code: str, message: str):
    click.echo(json.dumps({"error": True, "code": code, "message": message}, indent=2))


# ── Partial ID resolution ─────────────────────────────────────────────

def resolve_partial_id(
    partial: str,
    items: list,
    id_attr: str = "id",
    label_attr: str = "name",
    kind: str = "item",
) -> Any:
    """Resolve a partial ID to a single item from a list.

    For IDs >= 20 chars, requires exact match.
    For shorter strings, does case-insensitive prefix matching.
    Shows up to 5 candidates on ambiguity.
    """
    # Exact match first
    for item in items:
        if getattr(item, id_attr) == partial:
            return item

    # Short partial — prefix match
    if len(partial) < 20:
        matches = [
            item
            for item in items
            if getattr(item, id_attr, "").lower().startswith(partial.lower())
        ]
    else:
        matches = []

    if len(matches) == 1:
        return matches[0]

    if len(matches) == 0:
        raise click.UsageError(f"{kind} not found: {partial}")

    # Ambiguous
    candidates = matches[:5]
    lines = [f"  {getattr(c, id_attr)}  ({getattr(c, label_attr, '')})" for c in candidates]
    extra = f"\n  ... and {len(matches) - 5} more" if len(matches) > 5 else ""
    raise click.UsageError(
        f"Ambiguous {kind} ID '{partial}'. Did you mean:\n" + "\n".join(lines) + extra
    )


# ── Project context ───────────────────────────────────────────────────

def get_context_value(key: str) -> Optional[str]:
    """Read a value from persistent context.json."""
    if not CONTEXT_FILE.exists():
        return None
    try:
        data = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))
        return data.get(key)
    except (json.JSONDecodeError, OSError):
        return None


def set_context_value(key: str, value: Any):
    """Write a value to persistent context.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {}
    if CONTEXT_FILE.exists():
        try:
            data = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    data[key] = value
    CONTEXT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def require_project(project_arg: Optional[str] = None) -> str:
    """Resolve project ID from argument or persistent context.

    Args:
        project_arg: Explicit project ID (takes priority).

    Returns:
        Project ID string.

    Raises:
        click.UsageError: If no project ID can be determined.
    """
    if project_arg:
        return project_arg
    ctx_id = get_context_value("project_id")
    if ctx_id:
        return ctx_id
    raise click.UsageError(
        "No active project. Use: cli-web-stitch use <project-id>"
    )


# ── Filename sanitization ────────────────────────────────────────────

def sanitize_filename(name: str, max_length: int = 240) -> str:
    """Convert a string to a safe filename."""
    # Replace common unsafe characters
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    safe = safe.strip(". ")
    if not safe:
        safe = "unnamed"
    return safe[:max_length]


# ── Rate limit retry ─────────────────────────────────────────────────

def retry_on_rate_limit(fn: Callable, max_retries: int = 3) -> Any:
    """Call *fn* with exponential backoff retry on RateLimitError.

    Backoff: 2s -> 4s -> 8s (capped by retry_after header if present).
    """
    delay = 2.0
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except RateLimitError as exc:
            if attempt >= max_retries:
                raise
            wait = exc.retry_after if exc.retry_after else delay
            time.sleep(wait)
            delay *= 2.0
