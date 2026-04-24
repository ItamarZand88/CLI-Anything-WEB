"""Shared JSON-state I/O helpers for phase-state.py and capture-checkpoint.py.

Both scripts manage a JSON state file in an app directory and need the same
primitives: load-or-default, save-with-timestamp, UTC now. Extracted here so
there is one implementation — a bugfix (e.g., atomic write, file locking)
lands in one place.

Note: Deliberately does NOT unify the two scripts' schemas or CLIs. Skills
invoke them by subcommand, and changing either public surface would break
downstream callers.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def load_json_state(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Load a JSON state file. If missing, return `default` (None if not given).

    Returns None-by-default lets callers distinguish 'no state yet' from an
    empty dict.
    """
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_state(path: Path, state: dict[str, Any]) -> None:
    """Write state as JSON, stamping `updated_at` with current UTC time.

    Creates parent directories as needed. Mutates `state` by setting
    `updated_at`.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = utc_now_iso()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
