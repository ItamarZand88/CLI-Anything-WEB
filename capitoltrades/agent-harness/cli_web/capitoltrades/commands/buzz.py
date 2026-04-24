"""Buzz-related commands: list, get.

/buzz contains third-party news snippets (Twitter, external articles)
curated by Capitol Trades about companies and politicians.
"""
from __future__ import annotations

import click

from ..core.client import CapitoltradesClient
from ..core.exceptions import NotFoundError
from ..core.models import parse_buzz_detail, parse_buzz_list
from ..utils.helpers import handle_errors, print_json


@click.group()
def buzz():
    """Commands for querying third-party stock-market news snippets."""


@buzz.command("list")
@click.option("--page", type=int, default=1, show_default=True, help="Page number.")
@click.option("--page-size", type=int, default=12, show_default=True, help="Rows per page.")
@click.pass_context
def list_buzz(ctx, page, page_size):
    """List buzz items (curated news snippets)."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        with CapitoltradesClient() as client:
            soup = client.get_html("/buzz", params={"page": page, "pageSize": page_size})
            rows = parse_buzz_list(soup)
        if json_mode:
            print_json({"success": True, "data": rows, "meta": {"page": page, "page_size": page_size}})
        else:
            if not rows:
                click.echo("No buzz items found.")
                return
            for r in rows:
                click.echo(f"  [{r.get('published') or '?'}] {r.get('title')}")
                click.echo(f"    {r.get('url')}")


@buzz.command("get")
@click.argument("slug")
@click.pass_context
def get_buzz(ctx, slug):
    """Get a single buzz item by slug."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        with CapitoltradesClient() as client:
            soup = client.get_html(f"/buzz/{slug}")
            data = parse_buzz_detail(soup, slug)
        body = (data.get("body") or "").strip()
        title = (data.get("title") or "").strip()
        is_homepage = "Capitol Hill" in title and "Loading" in body[:50]
        if not body or is_homepage or body == "Loading ...":
            raise NotFoundError(f"Buzz item '{slug}' not found")
        if json_mode:
            print_json({"success": True, "data": data})
        else:
            click.echo(f"# {data.get('title')}")
            if data.get("published"):
                click.echo(f"Published: {data['published']}")
            click.echo()
            click.echo(data.get("body") or "(empty body)")
