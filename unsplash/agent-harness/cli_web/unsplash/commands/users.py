"""User commands for cli-web-unsplash."""

from __future__ import annotations

import click

from ..core.client import UnsplashClient
from ..core.models import (
    format_collection_summary,
    format_photo_summary,
    format_user_summary,
)
from ..utils.helpers import handle_errors, print_json
from ..utils.output import collection_table, photo_table, user_table


@click.group("users")
def users():
    """Search and view user profiles."""


@users.command("search")
@click.argument("query")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--per-page", type=int, default=20, help="Results per page.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def search(query, page, per_page, use_json):
    """Search users by name or username."""
    with handle_errors(json_mode=use_json):
        client = UnsplashClient()
        data = client.search_users(query, page=page, per_page=per_page)
        results = [format_user_summary(u) for u in data.get("results", [])]
        if use_json:
            print_json({"total": data.get("total", 0), "total_pages": data.get("total_pages", 0), "results": results})
        else:
            click.echo(f"Found {data.get('total', 0):,} users for '{query}' (page {page})")
            user_table(results, title=f"Search: {query}")


@users.command("get")
@click.argument("username")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def get_user(username, use_json):
    """Get user profile by username."""
    with handle_errors(json_mode=use_json):
        client = UnsplashClient()
        user = client.get_user(username)
        result = format_user_summary(user)
        if use_json:
            print_json(result)
        else:
            click.echo(f"\n  User: {result['name']} (@{result['username']})")
            if result["bio"]:
                click.echo(f"  Bio: {result['bio'][:200]}")
            if result["location"]:
                click.echo(f"  Location: {result['location']}")
            click.echo(f"  Photos: {result['total_photos']:,}")
            click.echo(f"  Likes: {result['total_likes']:,}")
            click.echo(f"  Collections: {result['total_collections']:,}")
            click.echo(f"  Link: {result['link']}")
            click.echo()


@users.command("photos")
@click.argument("username")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--per-page", type=int, default=20, help="Results per page.")
@click.option("--order-by", type=click.Choice(["latest", "oldest", "popular", "views", "downloads"]), help="Sort order.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def user_photos(username, page, per_page, order_by, use_json):
    """List photos by a user."""
    with handle_errors(json_mode=use_json):
        client = UnsplashClient()
        data = client.get_user_photos(username, page=page, per_page=per_page, order_by=order_by)
        results = [format_photo_summary(p) for p in data]
        if use_json:
            print_json(results)
        else:
            photo_table(results, title=f"Photos by @{username}")


@users.command("collections")
@click.argument("username")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--per-page", type=int, default=20, help="Results per page.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def user_collections(username, page, per_page, use_json):
    """List collections by a user."""
    with handle_errors(json_mode=use_json):
        client = UnsplashClient()
        data = client.get_user_collections(username, page=page, per_page=per_page)
        results = [format_collection_summary(c) for c in data]
        if use_json:
            print_json(results)
        else:
            collection_table(results, title=f"Collections by @{username}")
