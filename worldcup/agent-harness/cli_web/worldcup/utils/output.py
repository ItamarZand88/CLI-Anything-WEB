"""Structured JSON output helpers for cli-web-worldcup."""

from __future__ import annotations

import json


def json_success(data, **extra) -> str:
    """Format a successful result as JSON string."""
    payload = {"success": True, "data": data}
    payload.update(extra)
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def json_error(code: str, message: str, **extra) -> str:
    """Format an error result as JSON string."""
    payload = {"error": True, "code": code, "message": message}
    payload.update(extra)
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def json_lines(items) -> str:
    """Render list data as JSON Lines — one compact object per line (--jsonl)."""
    return "\n".join(
        json.dumps(item, separators=(",", ":"), ensure_ascii=False, default=str) for item in items
    )


def print_table(rows: list[dict], columns: list[tuple[str, str]]) -> None:
    """Print a simple aligned table.

    ``columns`` is a list of ``(header, dict_key)`` pairs. Cell values are
    truncated to the widest of header/values per column.
    """
    import click

    if not rows:
        return
    headers = [h for h, _ in columns]
    keys = [k for _, k in columns]
    widths = [
        max(len(h), *(len(str(r.get(k, ""))) for r in rows))
        for h, k in zip(headers, keys, strict=True)
    ]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    click.echo(fmt.format(*headers))
    click.echo(fmt.format(*("-" * w for w in widths)))
    for r in rows:
        click.echo(fmt.format(*(str(r.get(k, "")) for k in keys)))
