"""Topic commands for cli-web-unsplash."""

from __future__ import annotations

import click

from ..core.client import UnsplashClient
from ..core.models import format_photo_summary, format_topic_summary
from ..utils.helpers import handle_errors, print_json
from ..utils.output import photo_table, topic_table


@click.group("topics")
def topics():
    """Browse photo topics."""


@topics.command("list")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--per-page", type=int, default=20, help="Results per page.")
@click.option("--order-by", type=click.Choice(["featured", "latest", "oldest", "position"]), help="Sort order.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def list_topics(page, per_page, order_by, use_json):
    """List available topics."""
    with handle_errors(json_mode=use_json):
        client = UnsplashClient()
        data = client.list_topics(page=page, per_page=per_page, order_by=order_by)
        results = [format_topic_summary(t) for t in data]
        if use_json:
            print_json(results)
        else:
            topic_table(results)


@topics.command("get")
@click.argument("slug")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def get_topic(slug, use_json):
    """Get topic details by slug."""
    with handle_errors(json_mode=use_json):
        client = UnsplashClient()
        topic = client.get_topic(slug)
        result = format_topic_summary(topic)
        if use_json:
            print_json(result)
        else:
            click.echo(f"\n  Topic: {result['title']}")
            click.echo(f"  Slug: {result['slug']}")
            click.echo(f"  Photos: {result['total_photos']:,}")
            desc = topic.get("description") or "N/A"
            click.echo(f"  Description: {desc[:200]}")
            click.echo(f"  Link: {result['link']}")
            click.echo()


@topics.command("photos")
@click.argument("slug")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--per-page", type=int, default=20, help="Results per page.")
@click.option("--order-by", type=click.Choice(["latest", "oldest", "popular"]), help="Sort order.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def topic_photos(slug, page, per_page, order_by, use_json):
    """List photos in a topic."""
    with handle_errors(json_mode=use_json):
        client = UnsplashClient()
        data = client.get_topic_photos(slug, page=page, per_page=per_page, order_by=order_by)
        results = [format_photo_summary(p) for p in data]
        if use_json:
            print_json(results)
        else:
            photo_table(results, title=f"Topic: {slug}")
