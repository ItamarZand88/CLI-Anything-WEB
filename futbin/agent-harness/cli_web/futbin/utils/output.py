"""Output formatting utilities — JSON and human-readable tables."""
from __future__ import annotations

import json
import sys
from typing import Any


def print_json(data: Any) -> None:
    """Print data as indented JSON to stdout."""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def print_table(rows: list[dict], columns: list[str] | None = None) -> None:
    """Print a list of dicts as a formatted table."""
    if not rows:
        print("(no results)")
        return

    if columns is None:
        columns = list(rows[0].keys())

    # Compute column widths
    widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            val = str(row.get(col, ""))
            widths[col] = max(widths[col], len(val))

    header = "  ".join(col.upper().ljust(widths[col]) for col in columns)
    sep = "  ".join("-" * widths[col] for col in columns)
    print(header)
    print(sep)
    for row in rows:
        line = "  ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns)
        print(line)


def print_error(msg: str, exit_code: int = 1) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(exit_code)


def coins_display(value: int | None) -> str:
    """Format coin value for display."""
    if value is None:
        return "N/A"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)
