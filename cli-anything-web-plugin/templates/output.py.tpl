"""Structured JSON output helpers for cli-web-${app_name}."""
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
        json.dumps(item, separators=(",", ":"), ensure_ascii=False, default=str)
        for item in items
    )
