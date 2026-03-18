"""Output formatting utilities — JSON and human-readable table output."""

import json
import sys
from typing import Any


def output_json(data: Any):
    """Output data as formatted JSON."""
    print(json.dumps(data, indent=2, default=str))


def output_table(rows: list[dict], columns: list[str] = None):
    """Output data as a formatted table."""
    if not rows:
        print("(no results)")
        return

    if columns is None:
        columns = list(rows[0].keys())

    # Calculate column widths
    widths = {}
    for col in columns:
        widths[col] = max(
            len(col),
            max((len(str(row.get(col, ""))) for row in rows), default=0),
        )

    # Header
    header = " | ".join(col.ljust(widths[col]) for col in columns)
    separator = "-+-".join("-" * widths[col] for col in columns)
    print(header)
    print(separator)

    # Rows
    for row in rows:
        line = " | ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns)
        print(line)


def output_result(data: Any, as_json: bool = False, columns: list[str] = None):
    """Output data as JSON or table based on --json flag."""
    if as_json:
        output_json(data)
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        output_table(data, columns)
    elif isinstance(data, dict):
        for k, v in data.items():
            print(f"{k}: {v}")
    else:
        print(data)
