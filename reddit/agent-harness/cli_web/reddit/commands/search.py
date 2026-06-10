"""Search commands for cli-web-reddit."""

from __future__ import annotations

import click

from ..core.client import RedditClient
from ..core.models import extract_listing_posts, extract_listing_subreddits
from ..utils.helpers import handle_errors, print_json, resolve_json_mode
from ..utils.output import post_table, subreddit_table

SORT_CHOICES = ["relevance", "hot", "top", "new", "comments"]
TIME_CHOICES = ["hour", "day", "week", "month", "year", "all"]


@click.group("search")
def search():
    """Search Reddit posts and subreddits."""


@search.command("posts")
@click.argument("query")
@click.option("--sort", type=click.Choice(SORT_CHOICES), default="relevance", help="Sort order.")
@click.option(
    "--time",
    "time_filter",
    type=click.Choice(TIME_CHOICES),
    default=None,
    help="Time period (for top sort).",
)
@click.option("--limit", type=int, default=25, help="Number of results (max 100).")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def posts(query, sort, time_filter, limit, after, use_json):
    """Search posts across all of Reddit."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.search_posts(query, limit=limit, sort=sort, time=time_filter, after=after)
        results, next_after = extract_listing_posts(data)
        if use_json:
            print_json({"query": query, "posts": results, "after": next_after})
        else:
            post_table(results, title=f"Search: {query}")
            if next_after:
                click.echo(f'  Next page: search posts "{query}" --after {next_after}')


@search.command("subs")
@click.argument("query")
@click.option("--limit", type=int, default=25, help="Number of results (max 100).")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def subs(query, limit, after, use_json):
    """Search for subreddits by name/description."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.search_subreddits(query, limit=limit, after=after)
        results, next_after = extract_listing_subreddits(data)
        if use_json:
            print_json({"query": query, "subreddits": results, "after": next_after})
        else:
            subreddit_table(results, title=f"Subreddits: {query}")
            if next_after:
                click.echo(f'  Next page: search subs "{query}" --after {next_after}')
