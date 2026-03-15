"""Output formatting helpers — JSON and human-readable."""

from __future__ import annotations

import json
import sys
from typing import Any

import click


def output_json(data: Any) -> None:
    """Print data as formatted JSON to stdout."""
    click.echo(json.dumps(data, indent=2, default=str))


def output_error(message: str) -> None:
    """Print an error message to stderr."""
    click.echo(f"Error: {message}", err=True)


def output_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print a simple ASCII table."""
    if not headers:
        return

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    # Header
    header_line = "  ".join(
        str(h).ljust(col_widths[i]) for i, h in enumerate(headers)
    )
    click.echo(header_line)
    click.echo("  ".join("-" * w for w in col_widths))

    # Rows
    for row in rows:
        line = "  ".join(
            str(cell).ljust(col_widths[i])
            for i, cell in enumerate(row)
            if i < len(col_widths)
        )
        click.echo(line)


def truncate(text: str, max_len: int = 60) -> str:
    """Truncate text with ellipsis if it exceeds max_len."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
