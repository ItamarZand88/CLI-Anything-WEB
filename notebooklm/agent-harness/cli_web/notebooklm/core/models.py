"""Data models for NotebookLM entities."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


@dataclass
class Notebook:
    """A NotebookLM notebook."""
    id: str
    title: str
    emoji: str = ""
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    source_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Source:
    """A source document within a notebook."""
    id: str
    title: str
    source_type: str = "unknown"   # paste, pdf, url, youtube
    word_count: int = 0
    created_at: str = ""
    notebook_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Note:
    """A note within a notebook."""
    id: str
    content: str = ""
    title: str = ""
    created_at: str = ""
    notebook_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Artifact:
    """A generated artifact (study guide, summary, audio overview, etc.)."""
    id: str
    artifact_type: str = ""   # study_guide, summary, audio_overview, etc.
    title: str = ""
    content: str = ""
    status: str = ""
    created_at: str = ""
    notebook_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ChatMessage:
    """A single chat message (query or response)."""
    role: str  # "user" or "assistant"
    content: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ChatSession:
    """A chat session containing messages."""
    id: str = ""
    messages: list[ChatMessage] = field(default_factory=list)
    notebook_id: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "notebook_id": self.notebook_id,
            "messages": [m.to_dict() for m in self.messages],
        }
