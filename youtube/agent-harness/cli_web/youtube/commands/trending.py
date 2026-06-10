"""Trending command for cli-web-youtube."""

from __future__ import annotations

import click

from ..core.client import YouTubeClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode
from ..utils.output import print_videos_table


@click.group("trending")
def trending_group():
    """Browse trending YouTube videos."""


@trending_group.command("list")
@click.option(
    "--category",
    "-c",
    default="now",
    type=click.Choice(["now", "music", "gaming", "movies"], case_sensitive=False),
    help="Category filter (default: now).",
)
@click.option("--limit", "-l", default=20, type=int, help="Max results (default 20).")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def trending_list(category, limit, use_json):
    """List trending/popular videos.

    Example: trending list --category music --limit 10
    """
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = YouTubeClient()
        videos = client.trending(category=category)
        videos = videos[:limit]
        if use_json:
            print_json({"videos": videos, "count": len(videos), "category": category})
        else:
            click.echo(f"\n  Trending on YouTube — {category.title()} ({len(videos)} videos)\n")
            print_videos_table(videos)
