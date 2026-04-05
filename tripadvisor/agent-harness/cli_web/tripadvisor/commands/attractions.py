"""Attraction commands for cli-web-tripadvisor."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from ..core.client import TripAdvisorClient
from ..utils.helpers import (
    format_rating,
    handle_errors,
    print_json,
    resolve_json_mode,
    truncate,
)

console = Console()


@click.group("attractions")
@click.pass_context
def attractions(ctx):
    """Search and browse TripAdvisor attractions and things to do."""
    ctx.ensure_object(dict)


@attractions.command("search")
@click.argument("location")
@click.option("--geo-id", default=None, metavar="ID", help="Use known geo_id to skip location lookup.")
@click.option("--page", default=1, type=int, show_default=True, help="Page number (30 attractions per page).")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def search_attractions(ctx, location, geo_id, page, json_mode):
    """Search attractions and things to do in LOCATION.

    LOCATION is a destination name like "Paris" or "New York City".
    Use --geo-id to skip the location-lookup step (faster).

    Examples:

      cli-web-tripadvisor attractions search "Paris"

      cli-web-tripadvisor attractions search "Paris" --geo-id 187147

      cli-web-tripadvisor attractions search "London" --page 2

      cli-web-tripadvisor attractions search "Tokyo" --json
    """
    json_mode = resolve_json_mode(json_mode, ctx)

    with handle_errors(json_mode=json_mode):
        with TripAdvisorClient() as client:
            result = client.search_attractions(location, geo_id=geo_id, page=page)

        attrlist = result.get("attractions", [])

        if json_mode:
            print_json({
                "success": True,
                "location": location,
                "geo_id": result.get("geo_id"),
                "page": page,
                "count": len(attrlist),
                "attractions": [a.to_dict() for a in attrlist],
            })
            return

        if not attrlist:
            click.echo(
                f"No attractions found for '{location}' (page {page}). "
                "Try a different location name or --geo-id."
            )
            return

        table = Table(
            title=f"Attractions in {location} — page {page}",
            show_lines=False,
            expand=False,
        )
        table.add_column("ID", style="dim", no_wrap=True, max_width=10)
        table.add_column("Name", max_width=40)
        table.add_column("Rating", justify="right", max_width=14)
        table.add_column("City", max_width=16)
        table.add_column("Phone", max_width=18)

        for a in attrlist:
            table.add_row(
                a.id,
                truncate(a.name, 40),
                format_rating(a.rating, a.review_count),
                a.city or "—",
                a.telephone or "—",
            )

        console.print(table)
        click.echo(f"\nShowing {len(attrlist)} attraction(s) on page {page}.")
        if len(attrlist) >= 30:
            click.echo(f"Next page: attractions search '{location}' --page {page + 1}")
        click.echo("Tip: Use 'attractions get URL' with the attraction URL to see full details.")


@attractions.command("get")
@click.argument("url")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def get_attraction(ctx, url, json_mode):
    """Get detailed information for an attraction by its TripAdvisor URL.

    The URL is the full TripAdvisor attraction URL from a search result,
    e.g. https://www.tripadvisor.com/Attraction_Review-g187147-d188151-Reviews-...

    Examples:

      cli-web-tripadvisor attractions get "https://www.tripadvisor.com/Attraction_Review-g187147-d188151-Reviews-Eiffel_Tower-Paris_Ile_de_France.html"

      cli-web-tripadvisor attractions get "https://www.tripadvisor.com/Attraction_Review-..." --json
    """
    json_mode = resolve_json_mode(json_mode, ctx)

    with handle_errors(json_mode=json_mode):
        with TripAdvisorClient() as client:
            attr = client.get_attraction(url)

        if json_mode:
            print_json({"success": True, "attraction": attr.to_dict()})
            return

        click.echo(f"\n{'=' * 60}")
        click.echo(f"  {attr.name}")
        click.echo(f"{'=' * 60}")
        click.echo(f"  ID:          {attr.id or '—'}")
        click.echo(f"  Rating:      {format_rating(attr.rating, attr.review_count)}")
        click.echo(f"  Address:     {attr.address or '—'}")
        click.echo(f"  City:        {attr.city or '—'}")
        click.echo(f"  Telephone:   {attr.telephone or '—'}")
        click.echo(f"  Coordinates: {attr.latitude or '?'}, {attr.longitude or '?'}")
        if attr.opening_hours:
            click.echo("  Hours:")
            for h in attr.opening_hours[:7]:
                click.echo(f"    {h}")
        if attr.description:
            click.echo(f"  Description: {truncate(attr.description, 200)}")
        click.echo(f"  URL:         {attr.url}")
        click.echo()
