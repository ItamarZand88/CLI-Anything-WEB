"""
Reference: Shared CLI Helpers Module
======================================
Every generated CLI should have utils/helpers.py with these utilities:
1. resolve_partial_id() — let users type short prefixes instead of full UUIDs
2. handle_errors() — context manager replacing try/except in every command
3. require_notebook() — get context from arg or persistent file
4. sanitize_filename() — safe filenames from user content
5. poll_until_complete() — exponential backoff polling

These eliminate boilerplate across all command files.
"""
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import click


# ---------------------------------------------------------------------------
# Partial ID resolution
# ---------------------------------------------------------------------------

def resolve_partial_id(partial, items, id_attr="id", label_attr="title", kind="item"):
    """Resolve a partial ID prefix to a full item.

    Users can type 'abc' instead of 'abc123-long-uuid'. If >= 20 chars,
    skip list lookup (assume complete). Otherwise prefix-match.

    Example:
        nbs = client.list_notebooks()
        matched = resolve_partial_id("abc", nbs, kind="notebook")
        nb = client.get_notebook(matched.id)
    """
    if len(partial) >= 20:
        for item in items:
            if getattr(item, id_attr) == partial:
                return item
        raise click.BadParameter(f"{kind} '{partial}' not found")

    partial_lower = partial.lower()
    matches = [i for i in items if getattr(i, id_attr, "").lower().startswith(partial_lower)]

    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0:
        raise click.BadParameter(f"No {kind} matching '{partial}'")

    lines = [f"  {getattr(m, id_attr)[:16]}...  {getattr(m, label_attr, '')}" for m in matches[:5]]
    raise click.BadParameter(f"Ambiguous: '{partial}' matches {len(matches)} {kind}s:\n" + "\n".join(lines))


# ---------------------------------------------------------------------------
# Error handler context manager
# ---------------------------------------------------------------------------

@contextmanager
def handle_errors(json_mode=False):
    """Context manager that catches exceptions and outputs proper error messages.

    Exit codes: 1=user error, 2=system error, 130=keyboard interrupt.
    In json_mode, outputs {"error": true, "code": "...", "message": "..."}.

    Example:
        @cli.command("list")
        @click.option("--json", "use_json", is_flag=True)
        def list_items(use_json):
            with handle_errors(json_mode=use_json):
                client = AppClient()
                items = client.list_items()
                print_json(items) if use_json else print_table(items)
    """
    try:
        yield
    except KeyboardInterrupt:
        sys.exit(130)
    except click.exceptions.Exit:
        raise
    except click.UsageError:
        raise
    # Catch AppError (your base exception) with code mapping
    # except AppError as exc:
    #     code = error_code_for(exc)
    #     if json_mode:
    #         click.echo(json.dumps({"error": True, "code": code, "message": str(exc)}))
    #     else:
    #         click.echo(f"Error: {exc}", err=True)
    #     sys.exit(1)
    except Exception as exc:
        if json_mode:
            click.echo(json.dumps({"error": True, "code": "INTERNAL_ERROR", "message": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(2)


# ---------------------------------------------------------------------------
# Persistent context
# ---------------------------------------------------------------------------

CONTEXT_FILE = Path.home() / ".config" / "cli-web-APP" / "context.json"

def get_context_value(key):
    """Get a value from persistent context.json."""
    try:
        if CONTEXT_FILE.exists():
            return json.loads(CONTEXT_FILE.read_text(encoding="utf-8")).get(key)
    except (json.JSONDecodeError, OSError):
        pass
    return None

def set_context_value(key, value):
    """Set a value in persistent context.json."""
    ctx = {}
    try:
        if CONTEXT_FILE.exists():
            ctx = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    ctx[key] = value
    CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONTEXT_FILE.write_text(json.dumps(ctx, indent=2), encoding="utf-8")

def require_notebook(notebook_arg):
    """Get notebook ID from argument or persistent context.

    Enables: sources list  (uses context)  vs  sources list --notebook abc123
    """
    if notebook_arg:
        return notebook_arg
    ctx_id = get_context_value("notebook_id")
    if ctx_id:
        return ctx_id
    raise click.UsageError("No notebook specified. Use --notebook <id> or: cli-web-APP use <id>")


# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------

_INVALID = set('/\\:*?"<>|')

def sanitize_filename(name, max_length=240):
    """Convert a title to a safe filename."""
    if not name or not name.strip():
        return "untitled"
    safe = "".join(c if c not in _INVALID else "_" for c in name).strip(". ")
    return safe[:max_length] if safe else "untitled"


# ---------------------------------------------------------------------------
# Retry on rate limit
# ---------------------------------------------------------------------------

def retry_on_rate_limit(fn, max_retries=3):
    """Retry a function on RateLimitError with exponential backoff.

    Example:
        result = retry_on_rate_limit(
            lambda: client.generate_artifact(nb_id, "audio"),
            max_retries=3,
        )
    """
    import time
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            if not hasattr(e, 'retry_after') and 'rate limit' not in str(e).lower():
                raise
            if attempt == max_retries:
                raise
            delay = getattr(e, 'retry_after', None) or (60 * (2 ** attempt))
            delay = min(delay, 300)
            click.echo(f"  Rate limited. Retrying in {delay:.0f}s ({attempt+1}/{max_retries})...", err=True)
            time.sleep(delay)
