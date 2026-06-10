"""Typed model for one captured HTTP exchange.

This is the canonical schema for entries in ``raw-traffic.json``. The
capture scripts (``parse-trace.py``, ``mitmproxy-capture.py``) produce this
shape and the analysis/validation scripts consume it; this model is the
single place the shape is defined.

Optional *enhanced* fields (timestamps, cookies, body sizes) are only
present in mitmproxy captures.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = 1


@dataclass
class TrafficEntry:
    url: str
    method: str = "GET"
    status: int = 0
    request_headers: dict[str, str] = field(default_factory=dict)
    response_headers: dict[str, str] = field(default_factory=dict)
    post_data: str | None = None
    response_body: Any = None
    mime_type: str = ""
    time_ms: float = 0.0
    # Enhanced fields (mitmproxy captures only)
    timestamp: float | None = None
    response_body_size: int | None = None
    request_cookies: dict[str, str] | None = None
    response_cookies: list[dict[str, Any]] | None = None

    KNOWN_FIELDS = (
        "url",
        "method",
        "status",
        "request_headers",
        "response_headers",
        "post_data",
        "response_body",
        "mime_type",
        "time_ms",
        "timestamp",
        "response_body_size",
        "request_cookies",
        "response_cookies",
    )

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> TrafficEntry:
        if "url" not in raw:
            raise ValueError("traffic entry missing required field 'url'")
        kwargs = {k: raw[k] for k in cls.KNOWN_FIELDS if k in raw}
        entry = cls(**kwargs)
        entry.status = int(entry.status or 0)
        return entry

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Keep serialized form compact: drop unset enhanced fields.
        for key in ("timestamp", "response_body_size", "request_cookies", "response_cookies"):
            if d[key] is None:
                del d[key]
        return d

    @property
    def is_write(self) -> bool:
        return self.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}

    @property
    def is_error(self) -> bool:
        return self.status >= 400


def load_entries(raw: list[dict[str, Any]]) -> list[TrafficEntry]:
    return [TrafficEntry.from_dict(e) for e in raw]
