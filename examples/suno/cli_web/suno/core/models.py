"""Response models for Suno API data.

Lightweight dataclass wrappers for clean access to API response fields.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    id: str
    email: str
    display_name: str
    handle: str
    avatar_image_url: str = ""
    clerk_id: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "User":
        return cls(
            id=d.get("id", ""),
            email=d.get("email", ""),
            display_name=d.get("display_name", ""),
            handle=d.get("handle", ""),
            avatar_image_url=d.get("avatar_image_url", ""),
            clerk_id=d.get("clerk_id", ""),
        )


@dataclass
class Clip:
    id: str
    title: str
    status: str
    audio_url: str = ""
    image_url: str = ""
    video_url: str = ""
    play_count: int = 0
    upvote_count: int = 0
    duration: float = 0.0
    tags: str = ""
    prompt: str = ""
    gpt_description_prompt: str = ""
    model_name: str = ""
    major_model_version: str = ""
    task: str = ""
    is_public: bool = False
    is_liked: bool = False
    is_trashed: bool = False
    created_at: str = ""
    user_id: str = ""
    display_name: str = ""
    handle: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Clip":
        meta = d.get("metadata", {})
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            status=d.get("status", ""),
            audio_url=d.get("audio_url", ""),
            image_url=d.get("image_url", ""),
            video_url=d.get("video_url", ""),
            play_count=d.get("play_count", 0),
            upvote_count=d.get("upvote_count", 0),
            duration=meta.get("duration", 0.0),
            tags=meta.get("tags", ""),
            prompt=meta.get("prompt", ""),
            gpt_description_prompt=meta.get("gpt_description_prompt", ""),
            model_name=d.get("model_name", ""),
            major_model_version=d.get("major_model_version", ""),
            task=meta.get("task", ""),
            is_public=d.get("is_public", False),
            is_liked=d.get("is_liked", False),
            is_trashed=d.get("is_trashed", False),
            created_at=d.get("created_at", ""),
            user_id=d.get("user_id", ""),
            display_name=d.get("display_name", ""),
            handle=d.get("handle", ""),
        )

    def to_summary(self) -> dict:
        """Return a summary dict for table/JSON output."""
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "duration": f"{self.duration:.1f}s" if self.duration else "",
            "model": self.major_model_version,
            "plays": self.play_count,
            "likes": self.upvote_count,
            "created": self.created_at[:10] if self.created_at else "",
        }


@dataclass
class Project:
    id: str
    name: str
    description: str = ""
    clip_count: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            description=d.get("description", ""),
            clip_count=d.get("clip_count", 0),
        )


@dataclass
class BillingInfo:
    credits: int = 0
    total_credits_left: int = 0
    is_active: bool = False
    subscription_type: str = ""
    monthly_usage: int = 0
    monthly_limit: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "BillingInfo":
        return cls(
            credits=d.get("credits", 0),
            total_credits_left=d.get("total_credits_left", 0),
            is_active=d.get("is_active", False),
            subscription_type=str(d.get("subscription_type", "")),
            monthly_usage=d.get("monthly_usage", 0),
            monthly_limit=d.get("monthly_limit", 0),
        )
