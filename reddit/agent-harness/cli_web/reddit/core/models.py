"""Response models for Reddit API data."""

from __future__ import annotations

from datetime import datetime, timezone


def _ts(utc: float | None) -> str:
    """Convert Unix timestamp to human-readable string."""
    if utc is None:
        return ""
    return datetime.fromtimestamp(utc, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def _compact_number(n: int) -> str:
    """Format large numbers compactly: 1234 -> 1.2k, 1234567 -> 1.2M."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def format_post_summary(child: dict) -> dict:
    """Extract key fields from a post (t3) for display."""
    d = child.get("data", child)
    return {
        "id": d.get("id", ""),
        "title": d.get("title", ""),
        "author": d.get("author", "[deleted]"),
        "subreddit": d.get("subreddit", ""),
        "score": d.get("score", 0),
        "num_comments": d.get("num_comments", 0),
        "upvote_ratio": d.get("upvote_ratio", 0),
        "created": _ts(d.get("created_utc")),
        "url": d.get("url", ""),
        "permalink": f"https://www.reddit.com{d.get('permalink', '')}",
        "is_self": d.get("is_self", False),
        "over_18": d.get("over_18", False),
        "stickied": d.get("stickied", False),
        "flair": d.get("link_flair_text") or "",
        "selftext": d.get("selftext", ""),
    }


def format_post_detail(post_data: dict, comments_data: dict | None = None) -> dict:
    """Full post detail with comments for --json output."""
    post = format_post_summary(post_data)
    post["selftext"] = (post_data.get("data", post_data)).get("selftext", "")

    comments = []
    if comments_data:
        _collect_comments(comments_data.get("data", {}).get("children", []), comments)

    post["comments"] = comments
    return post


def _collect_comments(children: list[dict], comments: list[dict]) -> None:
    """Flatten Reddit comment trees while preserving depth."""
    for child in children:
        if child.get("kind") != "t1":
            continue
        comments.append(format_comment(child))
        replies = child.get("data", {}).get("replies")
        if isinstance(replies, dict):
            _collect_comments(replies.get("data", {}).get("children", []), comments)


def format_comment(child: dict) -> dict:
    """Extract key fields from a comment (t1)."""
    d = child.get("data", child)
    return {
        "id": d.get("id", ""),
        "parent_id": d.get("parent_id", ""),
        "author": d.get("author", "[deleted]"),
        "body": d.get("body", ""),
        "score": d.get("score", 0),
        "created": _ts(d.get("created_utc")),
        "is_submitter": d.get("is_submitter", False),
        "depth": d.get("depth", 0),
    }


def format_subreddit_info(data: dict) -> dict:
    """Extract key fields from a subreddit (t5)."""
    d = data.get("data", data)
    return {
        "name": d.get("display_name", ""),
        "title": d.get("title", ""),
        "description": d.get("public_description", ""),
        "subscribers": d.get("subscribers", 0),
        "active_users": d.get("active_user_count") or d.get("accounts_active", 0),
        "created": _ts(d.get("created_utc")),
        "over_18": d.get("over18", False),
        "type": d.get("subreddit_type", "public"),
        "url": f"https://www.reddit.com/r/{d.get('display_name', '')}",
    }


def format_subreddit_search(child: dict) -> dict:
    """Extract key fields from a subreddit search result."""
    d = child.get("data", child)
    return {
        "name": d.get("display_name", ""),
        "title": d.get("title", ""),
        "description": (d.get("public_description") or "")[:100],
        "subscribers": d.get("subscribers", 0),
        "over_18": d.get("over18", False),
    }


def format_user_info(data: dict) -> dict:
    """Extract key fields from a user (t2)."""
    d = data.get("data", data)
    return {
        "name": d.get("name", ""),
        "link_karma": d.get("link_karma", 0),
        "comment_karma": d.get("comment_karma", 0),
        "total_karma": d.get("total_karma", 0),
        "created": _ts(d.get("created_utc")),
        "is_gold": d.get("is_gold", False),
        "verified": d.get("has_verified_email", False),
        "url": f"https://www.reddit.com/user/{d.get('name', '')}",
    }


def extract_listing_posts(response: dict) -> tuple[list[dict], str | None]:
    """Extract posts from a Listing response. Returns (posts, after_cursor)."""
    data = response.get("data", {})
    children = data.get("children", [])
    posts = [format_post_summary(c) for c in children if c.get("kind") == "t3"]
    after = data.get("after")
    return posts, after


def extract_listing_posts_and_comments(response: dict) -> tuple[list[dict], list[dict], str | None]:
    """Extract posts AND comments from a mixed Listing (e.g., saved items).

    Returns (posts, comments, after_cursor).
    """
    data = response.get("data", {})
    children = data.get("children", [])
    posts = [format_post_summary(c) for c in children if c.get("kind") == "t3"]
    comments = [format_saved_comment(c) for c in children if c.get("kind") == "t1"]
    after = data.get("after")
    return posts, comments, after


def format_saved_comment(child: dict) -> dict:
    """Format a saved comment (t1) with subreddit and permalink."""
    d = child.get("data", child)
    comment = format_comment(child)
    comment["subreddit"] = d.get("subreddit", "")
    comment["permalink"] = f"https://www.reddit.com{d.get('permalink', '')}"
    return comment


def extract_listing_comments(response: dict) -> tuple[list[dict], str | None]:
    """Extract comments from a Listing response."""
    data = response.get("data", {})
    children = data.get("children", [])
    comments = [format_comment(c) for c in children if c.get("kind") == "t1"]
    after = data.get("after")
    return comments, after


def extract_listing_subreddits(response: dict) -> tuple[list[dict], str | None]:
    """Extract subreddits from a Listing response."""
    data = response.get("data", {})
    children = data.get("children", [])
    subs = [format_subreddit_search(c) for c in children if c.get("kind") == "t5"]
    after = data.get("after")
    return subs, after
