"""Collections commands for cli-web-producthunt."""

import click

from ..core.client import ProductHuntClient
from ..utils.helpers import handle_errors
from ..utils.output import print_json, print_table


@click.group("collections")
def collections():
    """Browse Product Hunt collections."""


@collections.command("list")
@click.option("--limit", default=20, type=int, help="Number of results (default: 20).")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def list_collections(limit, use_json):
    """List collections."""
    with handle_errors(json_mode=use_json):
        client = ProductHuntClient()
        results = client.list_collections(limit=limit)

        if use_json:
            print_json(results)
        else:
            if not results:
                click.echo("No collections found.")
                return
            rows = []
            for c in results:
                d = c.to_dict()
                rows.append([
                    d.get("slug", ""),
                    d.get("name", ""),
                    str(d.get("posts_count", "")),
                    d.get("description", "")[:50],
                ])
            print_table(rows, ["Slug", "Name", "Posts", "Description"])


@collections.command("get")
@click.argument("slug")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def get_collection(slug, use_json):
    """Get details for a specific collection by slug."""
    with handle_errors(json_mode=use_json):
        client = ProductHuntClient()
        collection = client.get_collection(slug=slug)

        if use_json:
            print_json(collection)
        else:
            d = collection.to_dict()
            click.echo(f"Name:        {d.get('name', '')}")
            click.echo(f"Slug:        {d.get('slug', '')}")
            click.echo(f"Description: {d.get('description', '')}")
            click.echo(f"Posts:       {d.get('posts_count', '')}")
