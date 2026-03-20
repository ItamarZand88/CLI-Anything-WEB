"""Response models for Unsplash API data."""

from __future__ import annotations


def format_photo_summary(photo: dict) -> dict:
    """Extract key fields from a photo response for display."""
    user = photo.get("user", {})
    return {
        "id": photo.get("id"),
        "description": photo.get("alt_description") or photo.get("description") or "",
        "width": photo.get("width"),
        "height": photo.get("height"),
        "likes": photo.get("likes", 0),
        "color": photo.get("color"),
        "author": user.get("name") or user.get("username", ""),
        "url": photo.get("urls", {}).get("regular", ""),
        "link": f"https://unsplash.com/photos/{photo.get('slug') or photo.get('id')}",
        "premium": photo.get("premium", False),
    }


def format_photo_detail(photo: dict) -> dict:
    """Full photo details for --json output."""
    user = photo.get("user", {})
    exif = photo.get("exif", {})
    location = photo.get("location", {})
    position = location.get("position", {}) if location else {}
    tags = [t.get("title", "") for t in photo.get("tags", [])]

    return {
        "id": photo.get("id"),
        "slug": photo.get("slug"),
        "description": photo.get("alt_description") or photo.get("description") or "",
        "width": photo.get("width"),
        "height": photo.get("height"),
        "color": photo.get("color"),
        "likes": photo.get("likes", 0),
        "views": photo.get("views", 0),
        "downloads": photo.get("downloads", 0),
        "created_at": photo.get("created_at"),
        "author": {
            "username": user.get("username"),
            "name": user.get("name"),
        },
        "urls": photo.get("urls", {}),
        "exif": {
            "camera": f"{exif.get('make', '')} {exif.get('model', '')}".strip() or None,
            "aperture": exif.get("aperture"),
            "exposure": exif.get("exposure_time"),
            "focal_length": exif.get("focal_length"),
            "iso": exif.get("iso"),
        },
        "location": {
            "name": location.get("name") if location else None,
            "city": location.get("city") if location else None,
            "country": location.get("country") if location else None,
            "latitude": position.get("latitude"),
            "longitude": position.get("longitude"),
        },
        "tags": tags,
        "premium": photo.get("premium", False),
        "link": f"https://unsplash.com/photos/{photo.get('slug') or photo.get('id')}",
    }


def format_user_summary(user: dict) -> dict:
    """Extract key fields from a user response for display."""
    return {
        "username": user.get("username"),
        "name": user.get("name"),
        "bio": user.get("bio") or "",
        "location": user.get("location") or "",
        "total_photos": user.get("total_photos", 0),
        "total_likes": user.get("total_likes", 0),
        "total_collections": user.get("total_collections", 0),
        "link": f"https://unsplash.com/@{user.get('username')}",
    }


def format_collection_summary(collection: dict) -> dict:
    """Extract key fields from a collection response for display."""
    user = collection.get("user", {})
    return {
        "id": collection.get("id"),
        "title": collection.get("title"),
        "description": collection.get("description") or "",
        "total_photos": collection.get("total_photos", 0),
        "author": user.get("name") or user.get("username", ""),
        "link": f"https://unsplash.com/collections/{collection.get('id')}",
    }


def format_topic_summary(topic: dict) -> dict:
    """Extract key fields from a topic response for display."""
    return {
        "slug": topic.get("slug"),
        "title": topic.get("title"),
        "description": (topic.get("description") or "")[:100],
        "total_photos": topic.get("total_photos", 0),
        "featured": topic.get("featured", False),
        "link": f"https://unsplash.com/t/{topic.get('slug')}",
    }
