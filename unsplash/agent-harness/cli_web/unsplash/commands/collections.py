"""Collection commands for cli-web-unsplash."""

from __future__ import annotations

import click

from ..core.client import UnsplashClient
from ..core.models import format_collection_summary, format_photo_summary
from ..utils.helpers import handle_errors, print_json
from ..utils.output import collection_table, photo_table


@click.group("collections")
def collections():
    """Search and browse photo collections."""


@collections.command("search")
@click.argument("query")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--per-page", type=int, default=20, help="Results per page.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def search(query, page, per_page, use_json):
    """Search collections by keyword."""
    with handle_errors(json_mode=use_json):
        client = UnsplashClient()
        data = client.search_collections(query, page=page, per_page=per_page)
        results = [format_collection_summary(c) for c in data.get("results", [])]
        if use_json:
            print_json({"total": data.get("total", 0), "total_pages": data.get("total_pages", 0), "results": results})
        else:
            click.echo(f"Found {data.get('total', 0):,} collections for '{query}' (page {page})")
            collection_table(results, title=f"Search: {query}")


@collections.command("get")
@click.argument("collection_id")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def get_collection(collection_id, use_json):
    """Get collection details by ID."""
    with handle_errors(json_mode=use_json):
        client = UnsplashClient()
        coll = client.get_collection(collection_id)
        result = format_collection_summary(coll)
        if use_json:
            print_json(result)
        else:
            click.echo(f"\n  Collection: {result['title']}")
            click.echo(f"  ID: {result['id']}")
            click.echo(f"  Photos: {result['total_photos']:,}")
            click.echo(f"  Author: {result['author']}")
            desc = coll.get("description") or "N/A"
            click.echo(f"  Description: {desc[:200]}")
            click.echo(f"  Link: {result['link']}")
            click.echo()


@collections.command("photos")
@click.argument("collection_id")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--per-page", type=int, default=20, help="Results per page.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def collection_photos(collection_id, page, per_page, use_json):
    """List photos in a collection."""
    with handle_errors(json_mode=use_json):
        client = UnsplashClient()
        data = client.get_collection_photos(collection_id, page=page, per_page=per_page)
        results = [format_photo_summary(p) for p in data]
        if use_json:
            print_json(results)
        else:
            photo_table(results, title=f"Collection {collection_id}")
