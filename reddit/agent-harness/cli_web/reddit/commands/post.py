"""Post commands for cli-web-reddit."""

from __future__ import annotations

import re

import click

from ..core.client import RedditClient
from ..core.models import format_post_detail
from ..utils.helpers import handle_errors, print_json, resolve_json_mode
from ..utils.output import comment_table, post_detail_display


@click.group("post")
def post():
    """View post details and comments."""


def _parse_post_url(url_or_id: str) -> tuple[str, str, str]:
    """Parse a Reddit post URL or ID into (subreddit, post_id, slug).

    Accepts:
      - Full URL: https://www.reddit.com/r/python/comments/abc123/my_post/
      - Short path: r/python/comments/abc123/my_post
      - Just the post ID: abc123 (subreddit resolved by Reddit API)
      - Fullname: t3_abc123 (stripped to abc123)
    """
    # Full URL or path with /r/sub/comments/id/slug pattern
    match = re.search(r"r/([^/]+)/comments/([^/]+)(?:/([^/?]+))?", url_or_id)
    if match:
        return match.group(1), match.group(2), match.group(3) or ""
    # Strip t3_ prefix if present
    post_id = url_or_id.strip("/")
    if post_id.startswith("t3_"):
        post_id = post_id[3:]
    return "", post_id, ""


@post.command("get")
@click.argument("url_or_id")
@click.option("--sub", default=None, help="Subreddit name (required if passing just a post ID).")
@click.option("--comments", "comment_limit", type=int, default=50, help="Number of comments to fetch.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def get(url_or_id, sub, comment_limit, use_json):
    """Get post details and comments.

    Pass a full Reddit URL or a post ID (with --sub).

    Examples:
      post get https://www.reddit.com/r/python/comments/abc123/my_post/
      post get abc123 --sub python
    """
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        subreddit, post_id, slug = _parse_post_url(url_or_id)
        if not subreddit and sub:
            subreddit = sub

        client = RedditClient()
        data = client.post_detail(subreddit, post_id, slug=slug,
                                  comment_limit=comment_limit, depth=50)

        # Reddit returns [post_listing, comments_listing]
        post_listing = data[0] if len(data) > 0 else {}
        comments_listing = data[1] if len(data) > 1 else {}

        post_children = post_listing.get("data", {}).get("children", [])
        post_data = post_children[0] if post_children else {}

        # Extract link_id for fetching collapsed comments
        link_id = post_data.get("data", {}).get("name", "") or f"t3_{post_id}"

        result = format_post_detail(
            post_data, comments_listing,
            more_children_fn=client.more_children,
            link_id=link_id,
            thread_fn=client.comment_thread,
            post_id=post_id,
        )

        if use_json:
            print_json(result)
        else:
            post_detail_display(result)
            if result.get("comments"):
                comment_table(result["comments"][:20], title="Top Comments")
                if len(result["comments"]) > 20:
                    click.echo(f"  ... and {len(result['comments']) - 20} more comments")
