"""Feed commands for cli-web-reddit — global feeds (hot, new, top, rising, popular)."""

from __future__ import annotations

import click

from ..core.client import RedditClient
from ..core.models import extract_listing_posts
from ..utils.helpers import handle_errors, print_json, resolve_json_mode
from ..utils.output import post_table

TIME_CHOICES = ["hour", "day", "week", "month", "year", "all"]


@click.group("feed")
def feed():
    """Browse global Reddit feeds."""


@feed.command("hot")
@click.option("--limit", type=int, default=25, help="Number of posts (max 100).")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def hot(limit, after, use_json):
    """Hot posts from the front page."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.feed_hot(limit=limit, after=after)
        posts, next_after = extract_listing_posts(data)
        if use_json:
            print_json({"posts": posts, "after": next_after})
        else:
            post_table(posts, title="Hot Posts")
            if next_after:
                click.echo(f"  Next page: feed hot --after {next_after}")


@feed.command("new")
@click.option("--limit", type=int, default=25, help="Number of posts (max 100).")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def new(limit, after, use_json):
    """Newest posts from the front page."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.feed_new(limit=limit, after=after)
        posts, next_after = extract_listing_posts(data)
        if use_json:
            print_json({"posts": posts, "after": next_after})
        else:
            post_table(posts, title="New Posts")
            if next_after:
                click.echo(f"  Next page: feed new --after {next_after}")


@feed.command("top")
@click.option(
    "--time", "time_filter", type=click.Choice(TIME_CHOICES), default="day", help="Time period."
)
@click.option("--limit", type=int, default=25, help="Number of posts (max 100).")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def top(time_filter, limit, after, use_json):
    """Top posts by time period."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.feed_top(limit=limit, after=after, time=time_filter)
        posts, next_after = extract_listing_posts(data)
        if use_json:
            print_json({"posts": posts, "after": next_after})
        else:
            post_table(posts, title=f"Top Posts ({time_filter})")
            if next_after:
                click.echo(f"  Next page: feed top --time {time_filter} --after {next_after}")


@feed.command("rising")
@click.option("--limit", type=int, default=25, help="Number of posts (max 100).")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def rising(limit, after, use_json):
    """Rising posts."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.feed_rising(limit=limit, after=after)
        posts, next_after = extract_listing_posts(data)
        if use_json:
            print_json({"posts": posts, "after": next_after})
        else:
            post_table(posts, title="Rising Posts")
            if next_after:
                click.echo(f"  Next page: feed rising --after {next_after}")


@feed.command("popular")
@click.option("--limit", type=int, default=25, help="Number of posts (max 100).")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def popular(limit, after, use_json):
    """Popular posts from r/popular."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.feed_popular(limit=limit, after=after)
        posts, next_after = extract_listing_posts(data)
        if use_json:
            print_json({"posts": posts, "after": next_after})
        else:
            post_table(posts, title="Popular Posts")
            if next_after:
                click.echo(f"  Next page: feed popular --after {next_after}")
