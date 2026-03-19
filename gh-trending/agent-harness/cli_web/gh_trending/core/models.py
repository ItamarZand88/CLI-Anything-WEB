"""Data models for GitHub Trending CLI."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class TrendingRepo:
    """A trending GitHub repository."""

    rank: int
    owner: str
    name: str
    full_name: str
    description: str
    language: str | None
    stars: int
    forks: int
    stars_today: int
    url: str
    contributors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrendingDeveloper:
    """A trending GitHub developer."""

    rank: int
    login: str
    name: str | None
    avatar_url: str
    profile_url: str
    popular_repo: str | None = None
    popular_repo_desc: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _parse_int(text: str) -> int:
    """Parse '4,859' or '4.2k' or '1,394 stars today' → int."""
    if not text:
        return 0
    # Extract first number group (handles "1,394 stars today")
    import re
    text = text.strip()
    match = re.search(r"[\d,]+", text)
    if not match:
        return 0
    return int(match.group().replace(",", ""))
