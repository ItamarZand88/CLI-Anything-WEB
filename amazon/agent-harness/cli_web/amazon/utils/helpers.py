"""Shared CLI helpers for cli-web-amazon."""
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import click

from ..core.exceptions import (
    AmazonError,
    NetworkError,
    NotFoundError,
    ParsingError,
    RateLimitError,
    ServerError,
    error_code_for,
)

CONFIG_DIR = Path.home() / ".config" / "cli-web-amazon"
CONFIG_FILE = CONFIG_DIR / "config.json"


# ---------------------------------------------------------------------------
# JSON output helper
# ---------------------------------------------------------------------------

def print_json(data: Any) -> None:
    """Print data as pretty JSON."""
    click.echo(json.dumps(data, ensure_ascii=False, indent=2))


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
    except AmazonError as exc:
        code = error_code_for(exc)
        if json_mode:
            err_dict: dict = {"error": True, "code": code, "message": str(exc)}
            if isinstance(exc, RateLimitError) and exc.retry_after is not None:
                err_dict["retry_after"] = exc.retry_after
            click.echo(json.dumps(err_dict, ensure_ascii=False))
        else:
            hint = ""
            if isinstance(exc, RateLimitError) and exc.retry_after:
                hint = f"\n  Hint: Retry after {exc.retry_after:.0f}s"
            elif isinstance(exc, ParsingError):
                hint = "\n  Hint: Amazon page structure may have changed"
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
