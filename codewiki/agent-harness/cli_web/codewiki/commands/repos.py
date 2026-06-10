"""Repository commands: featured, search."""

from __future__ import annotations

import click

from ..core.client import CodeWikiClient
from ..utils.helpers import handle_errors
from ..utils.output import print_json

_SEP = "\u2500"
_SLUG_W = 34
_STARS_W = 8
_DESC_W = 60


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _format_stars(stars: int) -> str:
    if stars >= 1_000:
        return f"{stars / 1_000:.1f}k"
    return str(stars)


def _print_repo_table(repos) -> None:
    header_slug = "Slug"
    header_stars = "Stars"
    header_desc = "Description"

    click.echo(f"{header_slug:<{_SLUG_W}}  {header_stars:<{_STARS_W}} {header_desc}")
    click.echo(_SEP * (_SLUG_W + 2 + _STARS_W + 1 + _DESC_W))

    for repo in repos:
        slug = _truncate(repo.slug, _SLUG_W)
        stars = _format_stars(repo.stars)
        desc = _truncate(repo.description, _DESC_W)
        click.echo(f"{slug:<{_SLUG_W}}  {stars:<{_STARS_W}} {desc}")


@click.group("repos")
def repos():
    """List and search repositories on Code Wiki."""
    pass


@repos.command("featured")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def featured(as_json: bool) -> None:
    """List featured repositories."""
    with handle_errors(json_mode=as_json):
        client = CodeWikiClient()
        try:
            result = client.featured_repos()
        finally:
            client.close()

        if as_json:
            print_json({"success": True, "data": [repo.to_dict() for repo in result]})
        else:
            if not result:
                click.echo("No featured repositories found.")
            else:
                _print_repo_table(result)


@repos.command("search")
@click.argument("query")
@click.option("--limit", default=25, show_default=True, help="Maximum number of results.")
@click.option("--offset", default=0, show_default=True, help="Result offset for pagination.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def search(query: str, limit: int, offset: int, as_json: bool) -> None:
    """Search repositories by QUERY."""
    with handle_errors(json_mode=as_json):
        client = CodeWikiClient()
        try:
            result = client.search_repos(query, limit=limit, offset=offset)
        finally:
            client.close()

        if as_json:
            print_json({"success": True, "data": [repo.to_dict() for repo in result]})
        else:
            if not result:
                click.echo(f"No repositories found for '{query}'.")
            else:
                _print_repo_table(result)
