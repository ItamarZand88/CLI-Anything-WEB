"""Output formatting for NotebookLM CLI."""

import json
import sys


def output_json(data, file=None):
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str), file=file or sys.stdout)


def output_table(headers: list[str], rows: list[list[str]]):
    """Print a simple text table."""
    if not rows:
        print("  (no results)")
        return

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    # Cap widths
    col_widths = [min(w, 50) for w in col_widths]

    def pad(text, width):
        t = str(text)[:width]
        return t + " " * (width - len(t))

    header_line = " | ".join(pad(h, col_widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * w for w in col_widths)

    print(f"  {header_line}")
    print(f"  {sep_line}")
    for row in rows:
        cells = [pad(row[i] if i < len(row) else "", col_widths[i]) for i in range(len(headers))]
        print(f"  {' | '.join(cells)}")
