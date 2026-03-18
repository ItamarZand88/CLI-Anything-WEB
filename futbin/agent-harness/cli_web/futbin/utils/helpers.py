"""Shared CLI helpers for cli-web-futbin."""
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import click

from ..core.exceptions import (
    AuthError,
    FutbinError,
    InvalidInputError,
    NetworkError,
    NotFoundError,
    ParsingError,
    RateLimitError,
    ServerError,
    error_code_for,
)

CONFIG_DIR = Path.home() / ".config" / "cli-web-futbin"
CONFIG_FILE = CONFIG_DIR / "config.json"


# ---------------------------------------------------------------------------
# Partial ID resolution (for player search results)
# ---------------------------------------------------------------------------

def resolve_partial_id(partial, items, id_attr="id", label_attr="name", kind="item"):
    """Resolve a partial ID prefix to a full item.

    If partial is >= 8 chars (player IDs are typically 3-6 digits),
    assume it's complete and match exactly. Otherwise prefix-match.
    """
    partial_str = str(partial)

    # Exact match first
    for item in items:
        if str(getattr(item, id_attr)) == partial_str:
            return item

    # Prefix match
    matches = [
        item for item in items
        if str(getattr(item, id_attr, "")).startswith(partial_str)
    ]

    if len(matches) == 1:
        matched = matches[0]
        label = getattr(matched, label_attr, "") if label_attr else ""
        mid = str(getattr(matched, id_attr))
        if label:
            click.echo(f"  Matched: {mid} ({label})", err=True)
        return matched

    if len(matches) == 0:
        raise click.BadParameter(f"No {kind} matching '{partial}'")

    lines = []
    for m in matches[:5]:
        mid = str(getattr(m, id_attr))
        label = getattr(m, label_attr, "") if label_attr else ""
        lines.append(f"  {mid}  {label}")
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

    Exit codes: 1=user/app error, 2=system error, 130=keyboard interrupt.
    """
    try:
        yield
    except KeyboardInterrupt:
        if not json_mode:
            click.echo("\nInterrupted.", err=True)
        sys.exit(130)
    except click.exceptions.Exit:
        raise
    except click.UsageError:
        raise
    except FutbinError as exc:
        code = error_code_for(exc)
        if json_mode:
            click.echo(json.dumps(
                {"error": True, "code": code, "message": str(exc)},
                ensure_ascii=False,
            ))
        else:
            hint = ""
            if isinstance(exc, RateLimitError) and exc.retry_after:
                hint = f"\n  Hint: Retry after {exc.retry_after:.0f}s"
            elif isinstance(exc, ParsingError):
                hint = "\n  Hint: FUTBIN site structure may have changed"
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
# Persistent config
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    """Load config.json, returning empty dict on failure."""
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _save_config(data: dict) -> None:
    """Save config.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_config_value(key: str) -> Any:
    """Get a value from persistent config."""
    return _load_config().get(key)


def set_config_value(key: str, value: Any) -> None:
    """Set a value in persistent config."""
    cfg = _load_config()
    cfg[key] = value
    _save_config(cfg)


def clear_config() -> None:
    """Clear all persistent config."""
    _save_config({})


def get_all_config() -> dict:
    """Get the entire config dict."""
    return _load_config()


def require_year(year_arg: int | None) -> int:
    """Get year from argument or persistent config (default 26)."""
    if year_arg is not None:
        return year_arg
    cfg_year = get_config_value("year")
    if cfg_year is not None:
        return int(cfg_year)
    return 26


def require_platform(platform_arg: str | None) -> str:
    """Get platform from argument or persistent config (default 'ps')."""
    if platform_arg:
        return platform_arg
    cfg_platform = get_config_value("platform")
    if cfg_platform:
        return str(cfg_platform)
    return "ps"


# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------

_INVALID_CHARS = set('/\\:*?"<>|')


def sanitize_filename(name: str, max_length: int = 240) -> str:
    """Convert a title to a safe filename."""
    if not name or not name.strip():
        return "untitled"
    safe = "".join(c if c not in _INVALID_CHARS else "_" for c in name)
    safe = safe.strip(". ")
    return safe[:max_length] if safe else "untitled"
