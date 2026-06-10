"""Search command for cli-web-youtube."""

from __future__ import annotations

import click

from ..core.client import YouTubeClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode
from ..utils.output import print_videos_table


@click.group("search")
def search_group():
    """Search YouTube videos."""


@search_group.command("videos")
@click.argument("query")
@click.option("--limit", "-l", default=10, type=int, help="Max results (default 10).")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def search_videos(query, limit, use_json):
    """Search for videos by query.

    Example: search videos "python tutorial"
    """
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = YouTubeClient()
        result = client.search(query, limit=limit)
        if use_json:
            print_json(result)
        else:
            click.echo(f'\n  Search: "{query}" ({result["estimated_results"]:,} results)\n')
            print_videos_table(result["videos"])
