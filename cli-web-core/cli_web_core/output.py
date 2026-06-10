"""The ``--json`` output envelope shared by every cli-web-* CLI.

Success: ``{"success": true, "data": ...}``
Error:   ``{"error": true, "code": "...", "message": "..."}``
JSONL:   one compact object per line for list data (``jq``/agent piping).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any


def json_success(data: Any, **extra: Any) -> str:
    payload: dict[str, Any] = {"success": True, "data": data}
    payload.update(extra)
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def json_error(code: str, message: str, **extra: Any) -> str:
    payload: dict[str, Any] = {"error": True, "code": code, "message": message}
    payload.update(extra)
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def json_lines(items: Iterable[Any]) -> str:
    """Render list data as JSON Lines — one compact object per line.

    For ``--jsonl`` flags on list commands: streams cleanly into ``jq``,
    ``grep``, and agent loops without parsing a wrapper object.
    """
    return "\n".join(
        json.dumps(item, separators=(",", ":"), ensure_ascii=False, default=str) for item in items
    )
