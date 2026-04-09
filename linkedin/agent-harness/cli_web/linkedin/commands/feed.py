"""Feed commands for cli-web-linkedin."""
from __future__ import annotations

import click

from ..core.client import LinkedinClient
from ..utils.helpers import handle_errors, print_json


def _resolve_json_mode(ctx: click.Context, json_mode: bool) -> bool:
    """Return True if --json was passed on this command or the parent group."""
    return json_mode or (ctx.obj or {}).get("json", False)


def _extract_posts(data: dict) -> list[dict]:
    """Pull a flat list of post summaries from the feed GraphQL response.

    Feed data lives at data.data.feedDashMainFeedByMainFeed.*elements[].
    The ``*elements`` array contains URN pointers resolved from ``included``.
    """
    # Build included index for pointer resolution
    # Index by both entityUrn and urn (social counts use 'urn' field)
    included_index: dict[str, dict] = {}
    for inc in data.get("included", []):
        for key in ("entityUrn", "urn"):
            u = inc.get(key, "")
            if u:
                included_index[u] = inc

    # Navigate to the feed container (handle double-nested data.data)
    gql = data.get("data", {})
    if "data" in gql and isinstance(gql["data"], dict):
        gql = gql["data"]
    feed_container = gql.get("feedDashMainFeedByMainFeed", {})

    # Resolve elements: try direct elements[], then *elements[] pointers
    feed = feed_container.get("elements", [])
    if not feed:
        ptrs = feed_container.get("*elements", [])
        feed = [included_index[p] for p in ptrs if p in included_index]

    posts: list[dict] = []

    for item in feed:
        entity_urn = item.get("entityUrn", "")

        # Actor (author)
        actor = item.get("actor", {}) or {}
        actor_name = actor.get("name", {})
        author_name = actor_name.get("text", "") if isinstance(actor_name, dict) else str(actor_name or "")
        actor_desc = actor.get("description", {})
        headline = actor_desc.get("text", "") if isinstance(actor_desc, dict) else str(actor_desc or "")

        # Commentary (post text)
        commentary = item.get("commentary", {}) or {}
        text_obj = commentary.get("text", {})
        text = text_obj.get("text", "") if isinstance(text_obj, dict) else str(text_obj or "")

        # Social counts — resolve from included via activity URN
        likes = 0
        comments_count = 0
        social = item.get("socialDetail", {}) or {}
        counts = social.get("totalSocialActivityCounts", {}) or {}
        if counts:
            likes = counts.get("numLikes", 0) or 0
            comments_count = counts.get("numComments", 0) or 0
        else:
            # Counts are factored into included, keyed by activity URN
            import re
            m = re.search(r"urn:li:activity:\d+", entity_urn)
            if m and m.group(0) in included_index:
                sc = included_index[m.group(0)]
                likes = sc.get("numLikes", 0) or 0
                comments_count = sc.get("numComments", 0) or 0

        if not text and not author_name:
            continue

        posts.append({
            "urn": entity_urn,
            "author": author_name,
            "headline": headline,
            "text": text,
            "likes": likes,
            "comments": comments_count,
        })

    return posts


def _print_feed(posts: list[dict]) -> None:
    """Pretty-print feed posts to the terminal."""
    if not posts:
        click.echo("No posts found in your feed.")
        return

    for i, post in enumerate(posts, 1):
        author = post.get("author") or "Unknown"
        headline = post.get("headline") or ""
        text = post.get("text") or ""
        likes = post.get("likes", 0)
        comments_count = post.get("comments", 0)
        urn = post.get("urn") or ""

        # Truncate long text for preview
        preview = text[:200].replace("\n", " ")
        if len(text) > 200:
            preview += "..."

        click.secho(f"[{i}] {author}", fg="cyan", bold=True)
        if headline:
            click.secho(f"    {headline}", fg="bright_black")
        if preview:
            click.echo(f"    {preview}")
        click.echo(
            click.style(f"    Likes: {likes}", fg="green")
            + "  "
            + click.style(f"Comments: {comments_count}", fg="yellow")
        )
        if urn:
            click.secho(f"    URN: {urn}", fg="bright_black")
        click.echo()


@click.command("feed")
@click.option("--count", default=10, help="Number of posts.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def feed(ctx, count, json_mode):
    """View your LinkedIn feed."""
    json_mode = _resolve_json_mode(ctx, json_mode)

    with handle_errors(json_mode=json_mode):
        with LinkedinClient() as client:
            data = client.get_feed(count=count)

        if json_mode:
            print_json(data)
        else:
            posts = _extract_posts(data)
            _print_feed(posts[:count])
