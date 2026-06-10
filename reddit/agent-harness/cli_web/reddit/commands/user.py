"""User commands for cli-web-reddit."""

from __future__ import annotations

import click

from ..core.client import RedditClient
from ..core.models import extract_listing_comments, extract_listing_posts, format_user_info
from ..utils.helpers import handle_errors, print_json, resolve_json_mode
from ..utils.output import comment_table, post_table, user_detail_display

SORT_CHOICES = ["hot", "new", "top", "controversial"]
TIME_CHOICES = ["hour", "day", "week", "month", "year", "all"]


@click.group("user")
def user():
    """View user profiles and activity."""


@user.command("info")
@click.argument("username")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def info(username, use_json):
    """Get user profile information."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.user_about(username)
        result = format_user_info(data)
        if use_json:
            print_json(result)
        else:
            user_detail_display(result)


@user.command("posts")
@click.argument("username")
@click.option("--sort", type=click.Choice(SORT_CHOICES), default="new", help="Sort order.")
@click.option(
    "--time",
    "time_filter",
    type=click.Choice(TIME_CHOICES),
    default=None,
    help="Time period (for top sort).",
)
@click.option("--limit", type=int, default=25, help="Number of posts (max 100).")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def posts(username, sort, time_filter, limit, after, use_json):
    """View a user's submitted posts."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.user_posts(username, limit=limit, after=after, sort=sort, time=time_filter)
        results, next_after = extract_listing_posts(data)
        if use_json:
            print_json({"username": username, "posts": results, "after": next_after})
        else:
            post_table(results, title=f"u/{username} — Posts")
            if next_after:
                click.echo(f"  Next page: user posts {username} --after {next_after}")


@user.command("comments")
@click.argument("username")
@click.option("--sort", type=click.Choice(SORT_CHOICES), default="new", help="Sort order.")
@click.option(
    "--time",
    "time_filter",
    type=click.Choice(TIME_CHOICES),
    default=None,
    help="Time period (for top sort).",
)
@click.option("--limit", type=int, default=25, help="Number of comments (max 100).")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def comments(username, sort, time_filter, limit, after, use_json):
    """View a user's comments."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.user_comments(username, limit=limit, after=after, sort=sort, time=time_filter)
        results, next_after = extract_listing_comments(data)
        if use_json:
            print_json({"username": username, "comments": results, "after": next_after})
        else:
            comment_table(results, title=f"u/{username} — Comments")
            if next_after:
                click.echo(f"  Next page: user comments {username} --after {next_after}")
