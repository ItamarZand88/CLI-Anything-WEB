"""Topics commands for cli-web-producthunt."""

import click

from ..core.client import ProductHuntClient
from ..utils.helpers import handle_errors
from ..utils.output import print_json, print_table


@click.group()
def topics():
    """Browse Product Hunt topics."""


@topics.command("list")
@click.option("--sort", type=click.Choice(["newest", "name"], case_sensitive=False),
              default="newest", help="Sort order (default: newest).")
@click.option("--limit", default=20, type=int, help="Number of results (default: 20).")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def list_topics(sort, limit, use_json):
    """List topics."""
    sort_map = {"newest": "NEWEST", "name": "NAME"}
    api_sort = sort_map.get(sort.lower(), "NEWEST")

    with handle_errors(json_mode=use_json):
        client = ProductHuntClient()
        results = client.list_topics(sort=api_sort, limit=limit)

        if use_json:
            print_json(results)
        else:
            if not results:
                click.echo("No topics found.")
                return
            rows = []
            for t in results:
                d = t.to_dict()
                rows.append([
                    d.get("slug", ""),
                    d.get("name", ""),
                    str(d.get("posts_count", "")),
                    d.get("description", "")[:50],
                ])
            print_table(rows, ["Slug", "Name", "Posts", "Description"])


@topics.command("get")
@click.argument("slug")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def get_topic(slug, use_json):
    """Get details for a specific topic by slug."""
    with handle_errors(json_mode=use_json):
        client = ProductHuntClient()
        topic = client.get_topic(slug=slug)

        if use_json:
            print_json(topic)
        else:
            d = topic.to_dict()
            click.echo(f"Name:        {d.get('name', '')}")
            click.echo(f"Slug:        {d.get('slug', '')}")
            click.echo(f"Description: {d.get('description', '')}")
            click.echo(f"Posts:       {d.get('posts_count', '')}")
