"""Data models for Product Hunt scraped responses."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Post:
    id: str
    name: str
    tagline: str
    slug: str
    url: str
    description: Optional[str] = None
    votes_count: int = 0
    comments_count: int = 0
    topics: list[str] = field(default_factory=list)
    thumbnail_url: Optional[str] = None
    rank: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "tagline": self.tagline,
            "slug": self.slug,
            "url": self.url,
            "description": self.description,
            "votes_count": self.votes_count,
            "comments_count": self.comments_count,
            "topics": self.topics,
            "thumbnail_url": self.thumbnail_url,
            "rank": self.rank,
        }

    @classmethod
    def from_card(cls, card_data: dict) -> Post:
        """Build a Post from scraped card data.

        ``card_data`` keys: id, name, tagline, slug, votes_count,
        comments_count, topics, thumbnail_url.
        """
        name = card_data.get("name", "")
        # Extract rank from name prefix like "1. Stitch..."
        rank = None
        rank_match = re.match(r"^(\d+)\.\s+", name)
        if rank_match:
            rank = int(rank_match.group(1))
            name = name[rank_match.end():]

        slug = card_data.get("slug", "")
        return cls(
            id=card_data.get("id", ""),
            name=name,
            tagline=card_data.get("tagline", ""),
            slug=slug,
            url=f"https://www.producthunt.com/products/{slug}" if slug else "",
            description=card_data.get("description"),
            votes_count=card_data.get("votes_count", 0),
            comments_count=card_data.get("comments_count", 0),
            topics=card_data.get("topics", []),
            thumbnail_url=card_data.get("thumbnail_url"),
            rank=rank,
        )


@dataclass
class User:
    id: str
    name: str
    username: str
    headline: Optional[str] = None
    profile_image: Optional[str] = None
    website_url: Optional[str] = None
    followers_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "username": self.username,
            "headline": self.headline,
            "profile_image": self.profile_image,
            "website_url": self.website_url,
            "followers_count": self.followers_count,
        }

    @classmethod
    def from_card(cls, card_data: dict) -> User:
        """Build a User from scraped profile data."""
        return cls(
            id=card_data.get("id", ""),
            name=card_data.get("name", ""),
            username=card_data.get("username", ""),
            headline=card_data.get("headline"),
            profile_image=card_data.get("profile_image"),
            website_url=card_data.get("website_url"),
            followers_count=card_data.get("followers_count", 0),
        )
