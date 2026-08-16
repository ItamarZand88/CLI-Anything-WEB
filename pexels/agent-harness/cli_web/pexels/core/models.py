"""Data models for cli-web-pexels.

Normalizer functions that transform raw Pexels __NEXT_DATA__ structures
into clean, flat dictionaries for CLI output and --json serialization.
"""

from __future__ import annotations


def _canonical_slug(attrs: dict) -> str | None:
    """Return the route slug Pexels accepts, including the media ID."""
    slug = attrs.get("slug")
    media_id = attrs.get("id")
    if not slug or not media_id:
        return slug
    suffix = f"-{media_id}"
    return slug if str(slug).endswith(suffix) else f"{slug}{suffix}"


def normalize_photo(item: dict) -> dict:
    """Normalize a photo item from search results."""
    attrs = item.get("attributes", {})
    user = attrs.get("user", {})
    image = attrs.get("image", {})
    return {
        "id": attrs.get("id"),
        "type": "photo",
        "slug": _canonical_slug(attrs),
        "title": attrs.get("title"),
        "description": attrs.get("description"),
        "width": attrs.get("width"),
        "height": attrs.get("height"),
        "license": attrs.get("license"),
        "photographer": _format_name(user),
        "photographer_username": user.get("username"),
        "image_url": image.get("large") or image.get("medium"),
        "download_url": image.get("download_link"),
        "tags": [t.get("name") for t in (attrs.get("tags") or [])[:5]],
        "colors": attrs.get("colors", []),
    }


def normalize_photo_detail(medium: dict, details: dict) -> dict:
    """Normalize a photo detail page."""
    attrs = medium.get("attributes", {})
    user = attrs.get("user", {})
    image = attrs.get("image", {})
    det_attrs = details.get("attributes", {})
    return {
        "id": attrs.get("id"),
        "type": "photo",
        "slug": _canonical_slug(attrs),
        "title": attrs.get("title"),
        "description": attrs.get("description"),
        "alt": attrs.get("alt"),
        "width": attrs.get("width"),
        "height": attrs.get("height"),
        "license": attrs.get("license"),
        "created_at": attrs.get("created_at"),
        "photographer": _format_name(user),
        "photographer_username": user.get("username"),
        "photographer_url": f"https://www.pexels.com/@{user.get('slug', '')}",
        "image": {
            "small": image.get("small"),
            "medium": image.get("medium"),
            "large": image.get("large"),
            "download": image.get("download_link"),
        },
        "tags": [t.get("name") for t in (attrs.get("tags") or [])],
        "colors": attrs.get("colors", []),
        "main_color": attrs.get("main_color"),
        "exif": {
            "camera": det_attrs.get("camera"),
            "aperture": det_attrs.get("aperture"),
            "focal_length": det_attrs.get("focal_length"),
            "iso": det_attrs.get("iso"),
            "shutter_speed": det_attrs.get("shutter_speed"),
        },
        "location": det_attrs.get("location"),
        "file_size": det_attrs.get("size"),
    }


def normalize_video(item: dict) -> dict:
    """Normalize a video item from search results."""
    attrs = item.get("attributes", {})
    user = attrs.get("user", {})
    video = attrs.get("video", {})
    thumb = video.get("thumbnail", {}) if video else {}
    return {
        "id": attrs.get("id"),
        "type": "video",
        "slug": _canonical_slug(attrs),
        "title": attrs.get("title"),
        "description": attrs.get("description"),
        "width": attrs.get("width"),
        "height": attrs.get("height"),
        "license": attrs.get("license"),
        "photographer": _format_name(user),
        "photographer_username": user.get("username"),
        "thumbnail_url": thumb.get("medium") or thumb.get("small"),
        "preview_url": video.get("preview_src") if video else None,
        "download_url": video.get("download_link") if video else None,
    }


def normalize_video_detail(medium: dict) -> dict:
    """Normalize a video detail page."""
    attrs = medium.get("attributes", {})
    user = attrs.get("user", {})
    video = attrs.get("video", {})
    thumb = video.get("thumbnail", {}) if video else {}
    files = video.get("video_files", []) if video else []
    return {
        "id": attrs.get("id"),
        "type": "video",
        "slug": _canonical_slug(attrs),
        "title": attrs.get("title"),
        "description": attrs.get("description"),
        "width": attrs.get("width"),
        "height": attrs.get("height"),
        "license": attrs.get("license"),
        "created_at": attrs.get("created_at"),
        "photographer": _format_name(user),
        "photographer_username": user.get("username"),
        "photographer_url": f"https://www.pexels.com/@{user.get('slug', '')}",
        "thumbnail": {
            "small": thumb.get("small"),
            "medium": thumb.get("medium"),
            "large": thumb.get("large"),
        },
        "video_src": video.get("src") if video else None,
        "preview_src": video.get("preview_src") if video else None,
        "video_files": [
            {
                "quality": f.get("quality"),
                "width": f.get("width"),
                "height": f.get("height"),
                "fps": f.get("fps"),
                "file_type": f.get("file_type"),
                "link": f.get("link"),
            }
            for f in files
        ],
        "tags": [t.get("name") for t in (attrs.get("tags") or [])],
    }


def normalize_user(user: dict) -> dict:
    """Normalize a user profile."""
    attrs = user.get("attributes", {})
    avatar = attrs.get("avatar", {})
    return {
        "id": attrs.get("id"),
        "username": attrs.get("username"),
        "first_name": attrs.get("first_name"),
        "last_name": attrs.get("last_name"),
        "location": attrs.get("location"),
        "bio": attrs.get("bio"),
        "avatar": avatar.get("medium") or avatar.get("small"),
        "photos_count": attrs.get("photos_count"),
        "media_count": attrs.get("media_count"),
        "followers_count": attrs.get("followers_count"),
        "hero": attrs.get("hero", False),
        "url": f"https://www.pexels.com/@{attrs.get('slug', '')}",
    }


def normalize_media_item(item: dict) -> dict:
    """Normalize a media item (photo or video) from user/collection pages."""
    item_type = item.get("type", "photo")
    attrs = item.get("attributes", {})
    image = attrs.get("image", {})
    video = attrs.get("video", {})
    result = {
        "id": attrs.get("id"),
        "type": item_type,
        "slug": attrs.get("slug"),
        "title": attrs.get("title"),
        "width": attrs.get("width"),
        "height": attrs.get("height"),
    }
    if item_type == "video" and video:
        thumb = video.get("thumbnail", {})
        result["thumbnail_url"] = thumb.get("medium") or thumb.get("small")
    elif image:
        result["image_url"] = image.get("medium") or image.get("small")
    return result


def normalize_collection(collection: dict) -> dict:
    """Normalize a collection."""
    attrs = collection.get("attributes", {})
    return {
        "id": attrs.get("id"),
        "title": attrs.get("title"),
        "description": attrs.get("description"),
        "slug": attrs.get("slug"),
        "media_count": attrs.get("collection_media_count"),
        "photos_count": attrs.get("photos_count"),
        "videos_count": attrs.get("videos_count"),
    }


def normalize_collection_summary(item: dict) -> dict:
    """Normalize a collection from discover/popular."""
    attrs = item.get("attributes", {})
    return {
        "id": attrs.get("id"),
        "title": attrs.get("title"),
        "slug": attrs.get("slug"),
        "media_count": attrs.get("collection_media_count"),
        "photos_count": attrs.get("photos_count"),
        "videos_count": attrs.get("videos_count"),
    }


# ── Helpers ──────────────────────────────────────────────────────────


def _format_name(user: dict) -> str:
    """Format user first/last name into a display string."""
    return f"{user.get('first_name', '')} {user.get('last_name', '') or ''}".strip()
