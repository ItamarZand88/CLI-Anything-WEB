"""Output formatting helpers for cli-web-producthunt."""

import json
import sys


def print_json(data):
    """Print data as formatted JSON to stdout."""
    if isinstance(data, list):
        output = [item.to_dict() if hasattr(item, "to_dict") else item for item in data]
    elif hasattr(data, "to_dict"):
        output = data.to_dict()
    else:
        output = data
    print(json.dumps(output, indent=2, default=str))


def print_table(rows: list[list[str]], headers: list[str]):
    """Print a simple formatted table to stdout."""
    if not headers or not rows:
        return

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    # Print header
    header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("  ".join("-" * w for w in col_widths))

    # Print rows
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            if i < len(col_widths):
                cells.append(str(cell).ljust(col_widths[i]))
        print("  ".join(cells))
