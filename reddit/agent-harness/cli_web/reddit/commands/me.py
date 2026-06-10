"""Me commands for cli-web-reddit — view own profile, saved, upvoted, subscriptions, inbox."""

from __future__ import annotations

import click

from ..core.client import RedditClient
from ..core.models import (
    extract_listing_posts,
    extract_listing_posts_and_comments,
    extract_listing_subreddits,
    format_user_info,
)
from ..utils.helpers import handle_errors, print_json, resolve_json_mode
from ..utils.output import comment_table, post_table, subreddit_table, user_detail_display


@click.group("me")
def me():
    """View your profile, saved posts, subscriptions, and inbox (requires login)."""


@me.command("profile")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def profile(use_json):
    """Show your Reddit profile."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.me()
        result = format_user_info(data)
        if use_json:
            print_json(result)
        else:
            user_detail_display(result)


@me.command("saved")
@click.option("--limit", type=int, default=25, help="Number of items.")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def saved(limit, after, use_json):
    """View your saved posts and comments."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.me_saved(limit=limit, after=after)
        posts, comments, next_after = extract_listing_posts_and_comments(data)
        if use_json:
            print_json({"posts": posts, "comments": comments, "after": next_after})
        else:
            if posts:
                post_table(posts, title="Saved Posts")
            if comments:
                comment_table(comments, title="Saved Comments")
            if not posts and not comments:
                click.echo("  No saved items found.")
            if next_after:
                click.echo(f"  Next page: me saved --after {next_after}")


@me.command("upvoted")
@click.option("--limit", type=int, default=25, help="Number of items.")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def upvoted(limit, after, use_json):
    """View your upvoted posts."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.me_upvoted(limit=limit, after=after)
        posts, next_after = extract_listing_posts(data)
        if use_json:
            print_json({"posts": posts, "after": next_after})
        else:
            post_table(posts, title="Upvoted Posts")
            if next_after:
                click.echo(f"  Next page: me upvoted --after {next_after}")


@me.command("subscriptions")
@click.option("--limit", type=int, default=100, help="Number of subreddits.")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def subscriptions(limit, after, use_json):
    """View your subscribed subreddits."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.me_subscriptions(limit=limit, after=after)
        subs, next_after = extract_listing_subreddits(data)
        if use_json:
            print_json({"subreddits": subs, "after": next_after})
        else:
            subreddit_table(subs, title="Subscriptions")
            if next_after:
                click.echo(f"  Next page: me subscriptions --after {next_after}")


@me.command("inbox")
@click.option("--limit", type=int, default=25, help="Number of messages.")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def inbox(limit, after, use_json):
    """View your inbox messages."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.me_inbox(limit=limit, after=after)
        # Messages are t4 (private message) or t1 (comment reply)
        children = data.get("data", {}).get("children", [])
        messages = []
        for c in children:
            d = c.get("data", {})
            messages.append(
                {
                    "id": d.get("id", ""),
                    "type": c.get("kind", ""),
                    "author": d.get("author", ""),
                    "subject": d.get("subject", ""),
                    "body": d.get("body", "")[:200],
                    "subreddit": d.get("subreddit", ""),
                    "new": d.get("new", False),
                }
            )
        next_after = data.get("data", {}).get("after")
        if use_json:
            print_json({"messages": messages, "after": next_after})
        else:
            if not messages:
                click.echo("  Inbox is empty.")
            else:
                for m in messages:
                    new_tag = " [NEW]" if m["new"] else ""
                    click.echo(f"  {m['author']}{new_tag}: {m['subject']}")
                    if m["body"]:
                        click.echo(f"    {m['body'][:100]}")
            if next_after:
                click.echo(f"\n  Next page: me inbox --after {next_after}")
