"""Data models for Hacker News CLI."""

from __future__ import annotations

import html
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class Story:
    """A Hacker News story."""

    id: int
    title: str
    url: str | None = None
    score: int = 0
    by: str = ""
    time: int = 0
    descendants: int = 0
    type: str = "story"

    @property
    def age(self) -> str:
        """Human-readable age like '2h ago'."""
        if not self.time:
            return ""
        delta = int(time.time()) - self.time
        if delta < 60:
            return f"{delta}s ago"
        if delta < 3600:
            return f"{delta // 60}m ago"
        if delta < 86400:
            return f"{delta // 3600}h ago"
        return f"{delta // 86400}d ago"

    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        if not self.url:
            return ""
        match = re.match(r"https?://(?:www\.)?([^/]+)", self.url)
        return match.group(1) if match else ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["age"] = self.age
        d["domain"] = self.domain
        return d


@dataclass
class Comment:
    """A Hacker News comment."""

    id: int
    by: str = ""
    text: str = ""
    time: int = 0
    parent: int = 0
    kids: list[int] = field(default_factory=list)
    dead: bool = False
    deleted: bool = False
    type: str = "comment"

    @property
    def text_plain(self) -> str:
        """Strip HTML tags from comment text."""
        if not self.text:
            return ""
        text = re.sub(r"<[^>]+>", "", self.text)
        return html.unescape(text)

    @property
    def age(self) -> str:
        if not self.time:
            return ""
        delta = int(time.time()) - self.time
        if delta < 60:
            return f"{delta}s ago"
        if delta < 3600:
            return f"{delta // 60}m ago"
        if delta < 86400:
            return f"{delta // 3600}h ago"
        return f"{delta // 86400}d ago"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["text_plain"] = self.text_plain
        d["age"] = self.age
        return d


@dataclass
class User:
    """A Hacker News user profile."""

    id: str
    karma: int = 0
    created: int = 0
    about: str = ""
    submitted: list[int] = field(default_factory=list)

    @property
    def about_plain(self) -> str:
        if not self.about:
            return ""
        text = re.sub(r"<[^>]+>", "", self.about)
        return html.unescape(text)

    @property
    def member_since(self) -> str:
        if not self.created:
            return ""
        dt = datetime.fromtimestamp(self.created, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["about_plain"] = self.about_plain
        d["member_since"] = self.member_since
        # Trim submitted to first 20 for readability
        d["submitted"] = self.submitted[:20]
        d["total_submissions"] = len(self.submitted)
        return d


@dataclass
class SearchResult:
    """A search result from HN Algolia API."""

    objectID: str
    title: str
    url: str | None = None
    author: str = ""
    points: int | None = None
    num_comments: int | None = None
    created_at: str = ""
    story_id: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)
