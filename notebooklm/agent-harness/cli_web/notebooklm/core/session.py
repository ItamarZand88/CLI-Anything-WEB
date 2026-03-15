"""Session state management — CSRF token, session ID, build label."""

from __future__ import annotations

import re
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# File for caching session params between calls
SESSION_CACHE = Path.home() / ".config" / "cli-web-notebooklm" / "session.json"


@dataclass
class SessionParams:
    """Parameters extracted from the NotebookLM page load."""
    at: str            # CSRF token (SNlM0e)
    f_sid: str         # Session ID (FdrFJe)
    bl: str            # Build label (cfb2h)

    def to_dict(self) -> dict:
        return {"at": self.at, "f_sid": self.f_sid, "bl": self.bl}


def extract_session_params(html: str) -> SessionParams:
    """Extract session parameters from the NotebookLM page HTML.

    Args:
        html: The raw HTML of the NotebookLM main page.

    Returns:
        SessionParams with CSRF token, session ID, and build label.

    Raises:
        ValueError: If required parameters cannot be found in HTML.
    """
    # Extract CSRF token: "SNlM0e":"<token>"
    at_match = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', html)
    if not at_match:
        raise ValueError(
            "Could not extract CSRF token (SNlM0e) from page HTML. "
            "Authentication cookies may be invalid or expired."
        )

    # Extract session ID: "FdrFJe":"<sid>"
    sid_match = re.search(r'"FdrFJe"\s*:\s*"([^"]+)"', html)
    if not sid_match:
        raise ValueError(
            "Could not extract session ID (FdrFJe) from page HTML."
        )

    # Extract build label: "cfb2h":"<bl>"
    bl_match = re.search(r'"cfb2h"\s*:\s*"([^"]+)"', html)
    if not bl_match:
        raise ValueError(
            "Could not extract build label (cfb2h) from page HTML."
        )

    return SessionParams(
        at=at_match.group(1),
        f_sid=sid_match.group(1),
        bl=bl_match.group(1),
    )


def save_session(params: SessionParams) -> None:
    """Cache session params to disk."""
    SESSION_CACHE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_CACHE.write_text(
        json.dumps(params.to_dict(), indent=2), encoding="utf-8"
    )


def load_session() -> SessionParams | None:
    """Load cached session params. Returns None if not found."""
    if not SESSION_CACHE.exists():
        return None
    try:
        data = json.loads(SESSION_CACHE.read_text(encoding="utf-8"))
        return SessionParams(
            at=data["at"], f_sid=data["f_sid"], bl=data["bl"]
        )
    except (json.JSONDecodeError, KeyError):
        return None
