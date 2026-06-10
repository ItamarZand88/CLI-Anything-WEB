"""Data models for cli-web-youtube — normalize InnerTube responses."""

from __future__ import annotations


def format_video_from_renderer(renderer: dict) -> dict:
    """Extract video data from a videoRenderer object."""
    title_runs = renderer.get("title", {}).get("runs", [])
    title = title_runs[0].get("text", "") if title_runs else ""

    owner_runs = renderer.get("ownerText", {}).get("runs", [])
    channel = owner_runs[0].get("text", "") if owner_runs else ""
    channel_id = ""
    if owner_runs:
        nav = owner_runs[0].get("navigationEndpoint", {})
        channel_id = nav.get("browseEndpoint", {}).get("browseId", "")

    views_text = renderer.get("viewCountText", {}).get("simpleText", "")
    length_text = renderer.get("lengthText", {}).get("simpleText", "")
    published = renderer.get("publishedTimeText", {}).get("simpleText", "")

    thumbs = renderer.get("thumbnail", {}).get("thumbnails", [])
    thumbnail = thumbs[-1].get("url", "") if thumbs else ""

    desc_runs = renderer.get("detailedMetadataSnippets", [])
    description = ""
    if desc_runs:
        snippet_runs = desc_runs[0].get("snippetText", {}).get("runs", [])
        description = "".join(r.get("text", "") for r in snippet_runs)

    return {
        "id": renderer.get("videoId", ""),
        "title": title,
        "channel": channel,
        "channel_id": channel_id,
        "views": views_text,
        "duration": length_text,
        "published": published,
        "thumbnail": thumbnail,
        "description": description,
        "url": f"https://www.youtube.com/watch?v={renderer.get('videoId', '')}",
    }


def format_video_detail(video_details: dict, microformat: dict | None = None) -> dict:
    """Extract full video details from player response."""
    thumbs = video_details.get("thumbnail", {}).get("thumbnails", [])
    thumbnail = thumbs[-1].get("url", "") if thumbs else ""

    result = {
        "id": video_details.get("videoId", ""),
        "title": video_details.get("title", ""),
        "channel": video_details.get("author", ""),
        "channel_id": video_details.get("channelId", ""),
        "views": int(video_details.get("viewCount", 0)),
        "duration_seconds": int(video_details.get("lengthSeconds", 0)),
        "description": video_details.get("shortDescription", ""),
        "keywords": video_details.get("keywords", []),
        "thumbnail": thumbnail,
        "is_live": video_details.get("isLiveContent", False),
        "url": f"https://www.youtube.com/watch?v={video_details.get('videoId', '')}",
    }

    if microformat:
        mf = microformat.get("playerMicroformatRenderer", {})
        result["publish_date"] = mf.get("publishDate", "")
        result["category"] = mf.get("category", "")
        result["is_family_safe"] = mf.get("isFamilySafe", True)

    return result


def format_channel(header: dict, metadata: dict | None = None) -> dict:
    """Extract channel info from browse response."""
    # Try c4TabbedHeaderRenderer (standard channels)
    c4 = header.get("c4TabbedHeaderRenderer", {})
    if c4:
        thumbs = c4.get("avatar", {}).get("thumbnails", [])
        avatar = thumbs[-1].get("url", "") if thumbs else ""
        banner_thumbs = c4.get("banner", {}).get("thumbnails", [])
        banner = banner_thumbs[-1].get("url", "") if banner_thumbs else ""

        sub_text = c4.get("subscriberCountText", {}).get("simpleText", "")

        return {
            "channel_id": c4.get("channelId", ""),
            "title": c4.get("title", ""),
            "subscriber_count": sub_text,
            "avatar": avatar,
            "banner": banner,
            "url": f"https://www.youtube.com/channel/{c4.get('channelId', '')}",
        }

    # Try pageHeaderRenderer (newer layout)
    ph = header.get("pageHeaderRenderer", {})
    if ph:
        title = ph.get("pageTitle", "")
        content = ph.get("content", {}).get("pageHeaderViewModel", {})
        desc = content.get("description", {}).get("descriptionPreviewViewModel", {})
        desc_text = desc.get("description", {}).get("content", "")

        image = (
            content.get("image", {})
            .get("decoratedAvatarViewModel", {})
            .get("avatar", {})
            .get("avatarViewModel", {})
            .get("image", {})
            .get("sources", [])
        )
        avatar = image[-1].get("url", "") if image else ""

        metadata_row = (
            content.get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows", [])
        )
        subs = ""
        videos = ""
        for row in metadata_row:
            for part in row.get("metadataParts", []):
                text = part.get("text", {}).get("content", "")
                if "subscriber" in text.lower():
                    subs = text
                elif "video" in text.lower():
                    videos = text

        return {
            "channel_id": "",
            "title": title,
            "description": desc_text,
            "subscriber_count": subs,
            "video_count": videos,
            "avatar": avatar,
            "url": "",
        }

    return {"error": "Unknown header format", "keys": list(header.keys())}


def format_trending_videos(contents: list) -> list[dict]:
    """Extract videos from trending browse response."""
    videos = []
    for section in contents:
        items = section.get("itemSectionRenderer", {}).get("contents", []) or section.get(
            "shelfRenderer", {}
        ).get("content", {}).get("expandedShelfContentsRenderer", {}).get("items", [])
        for item in items:
            renderer = item.get("videoRenderer")
            if renderer:
                videos.append(format_video_from_renderer(renderer))
    return videos
