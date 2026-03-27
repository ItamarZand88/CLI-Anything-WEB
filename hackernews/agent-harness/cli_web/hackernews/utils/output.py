"""Output formatting for cli-web-hackernews (JSON and human-readable tables)."""

from __future__ import annotations

import json
import sys
from typing import Any


def _safe(text: str, width: int = 0) -> str:
    """Truncate text to width and replace un-encodable characters."""
    if width:
        text = text[:width]
    encoding = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding)


def print_json(data: Any) -> None:
    """Print data as formatted JSON to stdout."""
    print(json.dumps(data, indent=2, default=str))


def print_error_json(error: Exception) -> None:
    """Print an error as JSON."""
    from cli_web.hackernews.core.exceptions import AppError

    if isinstance(error, AppError):
        print_json(error.to_dict())
    else:
        print_json({"error": True, "code": "UNKNOWN_ERROR", "message": str(error)})


def print_stories_table(stories: list) -> None:
    """Print stories as a human-readable table."""
    if not stories:
        print("No stories found.")
        return

    col_rank = 4
    col_title = 55
    col_score = 6
    col_by = 14
    col_comments = 8
    col_age = 8

    header = (
        f"{'#':<{col_rank}} "
        f"{'Title':<{col_title}} "
        f"{'Pts':>{col_score}} "
        f"{'By':<{col_by}} "
        f"{'Cmts':>{col_comments}} "
        f"{'Age':>{col_age}}"
    )
    print(header)
    print("-" * len(header))

    for i, story in enumerate(stories, start=1):
        title = _safe(story.title, col_title)
        by = _safe(story.by, col_by)
        print(
            f"{i:<{col_rank}} "
            f"{title:<{col_title}} "
            f"{story.score:>{col_score}} "
            f"{by:<{col_by}} "
            f"{story.descendants:>{col_comments}} "
            f"{story.age:>{col_age}}"
        )


def print_comments_list(comments: list) -> None:
    """Print comments in a readable format."""
    if not comments:
        print("No comments found.")
        return

    for i, comment in enumerate(comments, start=1):
        by = comment.by or "[deleted]"
        age = comment.age
        text = comment.text_plain[:200]
        if len(comment.text_plain) > 200:
            text += "..."
        replies = len(comment.kids)
        reply_note = f" ({replies} replies)" if replies else ""

        print(f"  {i}. {by} — {age}{reply_note}")
        print(f"     {text}")
        print()


def print_user_profile(user) -> None:
    """Print user profile in a readable format."""
    print(f"  Username:    {user.id}")
    print(f"  Karma:       {user.karma:,}")
    print(f"  Member since:{user.member_since}")
    if user.about_plain:
        about = user.about_plain[:300]
        if len(user.about_plain) > 300:
            about += "..."
        print(f"  About:       {about}")
    print(f"  Submissions: {len(user.submitted):,}")


def print_search_results_table(results: list) -> None:
    """Print search results as a table."""
    if not results:
        print("No results found.")
        return

    col_id = 10
    col_title = 55
    col_pts = 6
    col_by = 14
    col_cmts = 6

    header = (
        f"{'ID':<{col_id}} "
        f"{'Title':<{col_title}} "
        f"{'Pts':>{col_pts}} "
        f"{'By':<{col_by}} "
        f"{'Cmts':>{col_cmts}}"
    )
    print(header)
    print("-" * len(header))

    for result in results:
        title = _safe(result.title or "", col_title)
        by = _safe(result.author, col_by)
        pts = result.points if result.points is not None else 0
        cmts = result.num_comments if result.num_comments is not None else 0
        print(
            f"{result.objectID:<{col_id}} "
            f"{title:<{col_title}} "
            f"{pts:>{col_pts}} "
            f"{by:<{col_by}} "
            f"{cmts:>{col_cmts}}"
        )
