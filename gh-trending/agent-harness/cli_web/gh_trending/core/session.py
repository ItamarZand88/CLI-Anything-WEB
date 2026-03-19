"""Session state management for cli-web-github (minimal — trending is stateless)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SessionState:
    """Lightweight session state for the REPL."""

    # Last-used filter defaults for convenience
    last_language: str = ""
    last_since: str = "daily"
    last_spoken_language: str = ""

    # History for undo/redo (simple stack)
    _history: list[dict] = field(default_factory=list)

    def remember_filters(
        self,
        language: str = "",
        since: str = "daily",
        spoken_language: str = "",
    ) -> None:
        self.last_language = language
        self.last_since = since
        self.last_spoken_language = spoken_language

    def to_dict(self) -> dict:
        return {
            "last_language": self.last_language,
            "last_since": self.last_since,
            "last_spoken_language": self.last_spoken_language,
        }


# Global singleton for REPL use
_session = SessionState()


def get_session() -> SessionState:
    return _session
