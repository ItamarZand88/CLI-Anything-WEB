"""LinkedIn data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Post:
    """A LinkedIn post."""

    id: str
    text: str
    author_name: str
    author_headline: str = ""
    author_urn: str = ""
    created_at: str = ""
    num_likes: int = 0
    num_comments: int = 0
    num_repins: int = 0
    url: str = ""
    images: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "author_name": self.author_name,
            "author_headline": self.author_headline,
            "author_urn": self.author_urn,
            "created_at": self.created_at,
            "num_likes": self.num_likes,
            "num_comments": self.num_comments,
            "num_repins": self.num_repins,
            "url": self.url,
            "images": self.images,
        }


@dataclass
class Profile:
    """A LinkedIn user profile."""

    urn: str
    username: str
    first_name: str
    last_name: str
    headline: str = ""
    location: str = ""
    industry: str = ""
    follower_count: int = 0
    connection_count: int = 0
    summary: str = ""
    profile_url: str = ""
    image_url: str = ""

    def to_dict(self) -> dict:
        return {
            "urn": self.urn,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "headline": self.headline,
            "location": self.location,
            "industry": self.industry,
            "follower_count": self.follower_count,
            "connection_count": self.connection_count,
            "summary": self.summary,
            "profile_url": self.profile_url,
            "image_url": self.image_url,
        }


@dataclass
class Company:
    """A LinkedIn company page."""

    urn: str
    name: str
    universal_name: str = ""
    description: str = ""
    industry: str = ""
    follower_count: int = 0
    employee_count: int = 0
    url: str = ""
    logo_url: str = ""
    website: str = ""

    def to_dict(self) -> dict:
        return {
            "urn": self.urn,
            "name": self.name,
            "universal_name": self.universal_name,
            "description": self.description,
            "industry": self.industry,
            "follower_count": self.follower_count,
            "employee_count": self.employee_count,
            "url": self.url,
            "logo_url": self.logo_url,
            "website": self.website,
        }


@dataclass
class Job:
    """A LinkedIn job listing."""

    urn: str
    title: str
    company_name: str
    location: str = ""
    posted_at: str = ""
    applicant_count: int = 0
    description: str = ""
    url: str = ""
    workplace_type: str = ""  # remote / hybrid / onsite
    employment_type: str = ""

    def to_dict(self) -> dict:
        return {
            "urn": self.urn,
            "title": self.title,
            "company_name": self.company_name,
            "location": self.location,
            "posted_at": self.posted_at,
            "applicant_count": self.applicant_count,
            "description": self.description,
            "url": self.url,
            "workplace_type": self.workplace_type,
            "employment_type": self.employment_type,
        }


@dataclass
class SearchResult:
    """A LinkedIn search result entry."""

    urn: str
    name: str
    headline: str = ""
    location: str = ""
    url: str = ""
    type: str = ""  # person / company / job / post
    image_url: str = ""

    def to_dict(self) -> dict:
        return {
            "urn": self.urn,
            "name": self.name,
            "headline": self.headline,
            "location": self.location,
            "url": self.url,
            "type": self.type,
            "image_url": self.image_url,
        }


@dataclass
class Comment:
    """A comment on a LinkedIn post."""

    id: str
    text: str
    author_name: str
    author_urn: str = ""
    created_at: str = ""
    num_likes: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "author_name": self.author_name,
            "author_urn": self.author_urn,
            "created_at": self.created_at,
            "num_likes": self.num_likes,
        }
