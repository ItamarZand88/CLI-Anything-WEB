"""Search command — search HN via Algolia API."""

from __future__ import annotations

import click

from cli_web.hackernews.core.client import HackerNewsClient
from cli_web.hackernews.utils.helpers import handle_errors, resolve_json_mode
from cli_web.hackernews.utils.output import print_json, print_search_results_table


@click.group("search")
def search_group():
    """Search Hacker News stories and comments."""


@search_group.command("stories")
@click.argument("query")
@click.option("-n", "--limit", default=20, show_default=True, help="Number of results.")
@click.option("--page", default=0, help="Page number (0-indexed).")
@click.option("--sort-date", is_flag=True, help="Sort by date instead of relevance.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def search_stories(ctx, query, limit, page, sort_date, json_mode):
    """Search for stories by keyword."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = HackerNewsClient()
        results = client.search(
            query=query,
            tags="story",
            sort_by_date=sort_date,
            hits_per_page=limit,
            page=page,
        )
        if json_mode:
            print_json([r.to_dict() for r in results])
        else:
            sort_label = "by date" if sort_date else "by relevance"
            click.echo(f"\nSearch: '{query}' ({sort_label})\n")
            print_search_results_table(results)
            click.echo(f"\n{len(results)} results\n")


@search_group.command("comments")
@click.argument("query")
@click.option("-n", "--limit", default=20, show_default=True, help="Number of results.")
@click.option("--page", default=0, help="Page number (0-indexed).")
@click.option("--sort-date", is_flag=True, help="Sort by date instead of relevance.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def search_comments(ctx, query, limit, page, sort_date, json_mode):
    """Search for comments by keyword."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = HackerNewsClient()
        results = client.search(
            query=query,
            tags="comment",
            sort_by_date=sort_date,
            hits_per_page=limit,
            page=page,
        )
        if json_mode:
            print_json([r.to_dict() for r in results])
        else:
            sort_label = "by date" if sort_date else "by relevance"
            click.echo(f"\nSearch comments: '{query}' ({sort_label})\n")
            print_search_results_table(results)
            click.echo(f"\n{len(results)} results\n")
