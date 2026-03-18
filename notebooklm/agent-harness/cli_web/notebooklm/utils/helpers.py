"""Shared CLI helpers for cli-web-notebooklm.

Provides:
- resolve_partial_id() — prefix-match UUIDs so users can type short prefixes
- handle_errors() — context manager that catches exceptions, outputs JSON or text
- require_notebook() — gets notebook ID from arg or persistent context
- Shared Click option decorators for common patterns
"""
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import click

from ..core.exceptions import (
    AuthError,
    NetworkError,
    NotFoundError,
    NotebookLMError,
    RPCError,
    RateLimitError,
    ServerError,
    error_code_for,
)

AUTH_DIR = Path.home() / ".config" / "cli-web-notebooklm"
CONTEXT_FILE = AUTH_DIR / "context.json"


# ---------------------------------------------------------------------------
# Partial ID resolution
# ---------------------------------------------------------------------------

def resolve_partial_id(
    partial: str,
    items: list,
    id_attr: str = "id",
    label_attr: str | None = "title",
    kind: str = "item",
) -> Any:
    """Resolve a partial ID prefix to a full item.

    If *partial* is >= 20 chars, assume it's a complete ID and return it
    directly (skip list lookup). Otherwise, find all items whose ID starts
    with *partial* (case-insensitive).

    Args:
        partial: The ID prefix the user typed.
        items: List of objects to search.
        id_attr: Attribute name for the ID field.
        label_attr: Attribute name for a human-readable label (for messages).
        kind: Noun used in error messages ("notebook", "source", etc.).

    Returns:
        The matched item.

    Raises:
        click.BadParameter: If zero or multiple matches.
    """
    # Fast path: long IDs are assumed complete
    if len(partial) >= 20:
        for item in items:
            if getattr(item, id_attr) == partial:
                return item
        raise click.BadParameter(f"{kind} '{partial}' not found")

    partial_lower = partial.lower()
    matches = [
        item for item in items
        if getattr(item, id_attr, "").lower().startswith(partial_lower)
    ]

    if len(matches) == 1:
        matched = matches[0]
        label = getattr(matched, label_attr, "") if label_attr else ""
        mid = getattr(matched, id_attr)
        if label:
            click.echo(f"  Matched: {mid[:12]}... ({label})", err=True)
        return matched

    if len(matches) == 0:
        raise click.BadParameter(f"No {kind} matching '{partial}'")

    # Ambiguous — show up to 5 candidates
    lines = []
    for m in matches[:5]:
        mid = getattr(m, id_attr)
        label = getattr(m, label_attr, "") if label_attr else ""
        lines.append(f"  {mid[:16]}...  {label}")
    if len(matches) > 5:
        lines.append(f"  ... and {len(matches) - 5} more")
    candidates = "\n".join(lines)
    raise click.BadParameter(
        f"Ambiguous: '{partial}' matches {len(matches)} {kind}s:\n{candidates}"
    )


# ---------------------------------------------------------------------------
# Error handler context manager
# ---------------------------------------------------------------------------

@contextmanager
def handle_errors(json_mode: bool = False):
    """Context manager that catches exceptions and outputs proper error messages.

    Exit codes:
        1 — user/application error (auth, validation, not found, rate limit)
        2 — system/unexpected error (bugs, unknown exceptions)
        130 — keyboard interrupt (128 + SIGINT)

    Usage:
        with handle_errors(json_mode=use_json):
            client = NotebookLMClient()
            result = client.notebooks.list()
    """
    try:
        yield
    except KeyboardInterrupt:
        if not json_mode:
            click.echo("\nInterrupted.", err=True)
        sys.exit(130)
    except click.exceptions.Exit:
        raise  # Let Click handle its own exits
    except click.UsageError:
        raise  # Let Click handle usage errors
    except NotebookLMError as exc:
        code = error_code_for(exc)
        if json_mode:
            click.echo(json.dumps(
                {"error": True, "code": code, "message": str(exc)},
                ensure_ascii=False,
            ))
        else:
            hint = ""
            if isinstance(exc, AuthError):
                hint = "\n  Hint: Run 'cli-web-notebooklm auth login' to re-authenticate"
            elif isinstance(exc, RateLimitError) and exc.retry_after:
                hint = f"\n  Hint: Retry after {exc.retry_after:.0f}s"
            click.echo(f"Error: {exc}{hint}", err=True)
        sys.exit(1)
    except Exception as exc:
        if json_mode:
            click.echo(json.dumps(
                {"error": True, "code": "INTERNAL_ERROR", "message": str(exc)},
                ensure_ascii=False,
            ))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(2)


# ---------------------------------------------------------------------------
# Persistent context
# ---------------------------------------------------------------------------

def _load_context() -> dict:
    """Load context.json, returning empty dict on failure."""
    try:
        if CONTEXT_FILE.exists():
            return json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _save_context(data: dict) -> None:
    """Save context.json atomically."""
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    CONTEXT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_context_value(key: str) -> str | None:
    """Get a value from persistent context."""
    return _load_context().get(key)


def set_context_value(key: str, value: Any) -> None:
    """Set a value in persistent context."""
    ctx = _load_context()
    ctx[key] = value
    _save_context(ctx)


def clear_context() -> None:
    """Clear all persistent context."""
    _save_context({})


def require_notebook(notebook_arg: str | None) -> str:
    """Get notebook ID from argument or persistent context.

    Args:
        notebook_arg: The --notebook value (may be None).

    Returns:
        Notebook ID string.

    Raises:
        click.UsageError: If no notebook specified and none in context.
    """
    if notebook_arg:
        return notebook_arg
    ctx_id = get_context_value("notebook_id")
    if ctx_id:
        title = get_context_value("notebook_title") or ""
        click.echo(f"  Using notebook: {ctx_id[:12]}... ({title})", err=True)
        return ctx_id
    raise click.UsageError(
        "No notebook specified. Use --notebook <id> or set context with: "
        "cli-web-notebooklm use <id>"
    )


# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------

_INVALID_CHARS = set('/\\:*?"<>|')


def sanitize_filename(name: str, max_length: int = 240) -> str:
    """Convert a title to a safe filename.

    Replaces invalid characters with underscores, truncates to max_length,
    and falls back to 'untitled' for empty strings.
    """
    if not name or not name.strip():
        return "untitled"
    safe = "".join(c if c not in _INVALID_CHARS else "_" for c in name)
    safe = safe.strip(". ")  # Remove leading/trailing dots and spaces
    if not safe:
        return "untitled"
    return safe[:max_length]


# ---------------------------------------------------------------------------
# Polling utility
# ---------------------------------------------------------------------------

def poll_until_complete(check_fn, initial_interval=2.0, max_interval=10.0,
                        timeout=300.0, backoff_factor=1.5):
    """Poll with exponential backoff until complete or timeout.

    Args:
        check_fn: Callable returning a result dict when done, None when pending.
        initial_interval: First sleep duration (seconds).
        max_interval: Maximum sleep between polls.
        timeout: Total time before giving up.
        backoff_factor: Multiply interval each iteration.

    Returns:
        The completed result.

    Raises:
        TimeoutError: If not complete within timeout.
    """
    import time

    start = time.perf_counter()
    interval = initial_interval

    while True:
        result = check_fn()
        if result is not None:
            return result

        elapsed = time.perf_counter() - start
        remaining = timeout - elapsed
        if remaining <= 0:
            raise TimeoutError(f"Operation timed out after {elapsed:.0f}s")

        sleep_time = min(interval, max_interval, remaining)
        time.sleep(sleep_time)
        interval *= backoff_factor
