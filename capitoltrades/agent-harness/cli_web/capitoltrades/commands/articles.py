"""Article-related commands: list, get."""
from __future__ import annotations

import click

from ..core.client import CapitoltradesClient
from ..core.exceptions import NotFoundError
from ..core.models import parse_articles_list, parse_article_detail
from ..utils.helpers import handle_errors, print_json


@click.group()
def articles():
    """Commands for querying Capitol Trades insight articles."""


@articles.command("list")
@click.option("--page", type=int, default=1, show_default=True, help="Page number.")
@click.option("--page-size", type=int, default=12, show_default=True, help="Rows per page.")
@click.pass_context
def list_articles(ctx, page, page_size):
    """List articles/insights."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        with CapitoltradesClient() as client:
            soup = client.get_html("/articles", params={"page": page, "pageSize": page_size})
            rows = parse_articles_list(soup)
        if json_mode:
            print_json({"success": True, "data": rows, "meta": {"page": page, "page_size": page_size}})
        else:
            if not rows:
                click.echo("No articles found.")
                return
            for r in rows:
                click.echo(f"  [{r.get('published') or '?'}] {r.get('title')}")
                click.echo(f"    {r.get('url')}")


@articles.command("get")
@click.argument("slug")
@click.pass_context
def get_article(ctx, slug):
    """Get a single article by slug."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        with CapitoltradesClient() as client:
            soup = client.get_html(f"/articles/{slug}")
            data = parse_article_detail(soup, slug)
        # Site returns the homepage for unknown slugs (no 404)
        body = (data.get("body") or "").strip()
        title = (data.get("title") or "").strip()
        is_homepage = "Capitol Hill" in title and "Loading" in body[:50]
        if not body or is_homepage or body == "Loading ...":
            raise NotFoundError(f"Article '{slug}' not found")
        if json_mode:
            print_json({"success": True, "data": data})
        else:
            click.echo(f"# {data.get('title')}")
            if data.get("published"):
                click.echo(f"Published: {data['published']}")
            click.echo()
            click.echo(data.get("body") or "(empty body)")
