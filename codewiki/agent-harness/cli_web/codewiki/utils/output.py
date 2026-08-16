"""Output formatting for cli-web-codewiki (JSON and human-readable tables)."""

from __future__ import annotations

import json
from typing import Any


def print_json(data: Any) -> None:
    """Print data as formatted JSON to stdout."""
    payload = (
        data
        if isinstance(data, dict) and ("success" in data or data.get("error"))
        else {"success": True, "data": data}
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
