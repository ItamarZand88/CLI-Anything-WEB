"""Subreddit commands for cli-web-reddit."""

from __future__ import annotations

import click

from ..core.client import RedditClient
from ..core.models import extract_listing_posts, format_subreddit_info
from ..utils.helpers import handle_errors, print_json, resolve_json_mode
from ..utils.output import post_table, subreddit_detail_display

SORT_CHOICES = ["hot", "new", "top", "rising"]
TIME_CHOICES = ["hour", "day", "week", "month", "year", "all"]
SEARCH_SORT_CHOICES = ["relevance", "hot", "top", "new", "comments"]


@click.group("sub")
def sub():
    """Browse subreddits — posts, info, rules, search."""


@sub.command("hot")
@click.argument("name")
@click.option("--limit", type=int, default=25, help="Number of posts (max 100).")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def hot(name, limit, after, use_json):
    """Hot posts in a subreddit."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.sub_posts(name, sort="hot", limit=limit, after=after)
        posts, next_after = extract_listing_posts(data)
        if use_json:
            print_json({"subreddit": name, "posts": posts, "after": next_after})
        else:
            post_table(posts, title=f"r/{name} — Hot")
            if next_after:
                click.echo(f"  Next page: sub hot {name} --after {next_after}")


@sub.command("new")
@click.argument("name")
@click.option("--limit", type=int, default=25, help="Number of posts (max 100).")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def new(name, limit, after, use_json):
    """Newest posts in a subreddit."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.sub_posts(name, sort="new", limit=limit, after=after)
        posts, next_after = extract_listing_posts(data)
        if use_json:
            print_json({"subreddit": name, "posts": posts, "after": next_after})
        else:
            post_table(posts, title=f"r/{name} — New")
            if next_after:
                click.echo(f"  Next page: sub new {name} --after {next_after}")


@sub.command("top")
@click.argument("name")
@click.option(
    "--time", "time_filter", type=click.Choice(TIME_CHOICES), default="day", help="Time period."
)
@click.option("--limit", type=int, default=25, help="Number of posts (max 100).")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def top(name, time_filter, limit, after, use_json):
    """Top posts in a subreddit by time period."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.sub_posts(name, sort="top", limit=limit, after=after, time=time_filter)
        posts, next_after = extract_listing_posts(data)
        if use_json:
            print_json({"subreddit": name, "posts": posts, "after": next_after})
        else:
            post_table(posts, title=f"r/{name} — Top ({time_filter})")
            if next_after:
                click.echo(f"  Next page: sub top {name} --time {time_filter} --after {next_after}")


@sub.command("info")
@click.argument("name")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def info(name, use_json):
    """Get subreddit info and stats."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.sub_info(name)
        result = format_subreddit_info(data)
        if use_json:
            print_json(result)
        else:
            subreddit_detail_display(result)


@sub.command("rules")
@click.argument("name")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def rules(name, use_json):
    """Get subreddit rules."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.sub_rules(name)
        rule_list = data.get("rules", [])
        formatted = [
            {
                "priority": r.get("priority", i),
                "name": r.get("short_name", ""),
                "description": r.get("description", ""),
                "kind": r.get("kind", ""),
            }
            for i, r in enumerate(rule_list)
        ]
        if use_json:
            print_json({"subreddit": name, "rules": formatted})
        else:
            click.echo(f"\n  Rules for r/{name}:")
            for r in formatted:
                click.echo(f"  {r['priority'] + 1}. {r['name']}")
                if r["description"]:
                    desc = r["description"][:150].replace("\n", " ")
                    click.echo(f"     {desc}")
            click.echo()


@sub.command("search")
@click.argument("name")
@click.argument("query")
@click.option(
    "--sort", type=click.Choice(SEARCH_SORT_CHOICES), default="relevance", help="Sort order."
)
@click.option("--limit", type=int, default=25, help="Number of results (max 100).")
@click.option("--after", default=None, help="Pagination cursor.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def search(name, query, sort, limit, after, use_json):
    """Search posts within a subreddit."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        data = client.sub_search(name, query, limit=limit, sort=sort, after=after)
        posts, next_after = extract_listing_posts(data)
        if use_json:
            print_json({"subreddit": name, "query": query, "posts": posts, "after": next_after})
        else:
            click.echo(f"  Search r/{name} for '{query}':")
            post_table(posts, title=f"r/{name} Search: {query}")
            if next_after:
                click.echo(f'  Next page: sub search {name} "{query}" --after {next_after}')


@sub.command("join")
@click.argument("name")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def join(name, use_json):
    """Subscribe to a subreddit (requires login)."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        client.sub_join(name)
        if use_json:
            print_json({"success": True, "action": "subscribe", "subreddit": name})
        else:
            click.echo(f"  Subscribed to r/{name}")


@sub.command("leave")
@click.argument("name")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def leave(name, use_json):
    """Unsubscribe from a subreddit (requires login)."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        client.sub_leave(name)
        if use_json:
            print_json({"success": True, "action": "unsubscribe", "subreddit": name})
        else:
            click.echo(f"  Unsubscribed from r/{name}")
