"""Restaurant commands for cli-web-tripadvisor."""

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


@click.group("restaurants")
@click.pass_context
def restaurants(ctx):
    """Search and browse TripAdvisor restaurants."""
    ctx.ensure_object(dict)


@restaurants.command("search")
@click.argument("location")
@click.option("--geo-id", default=None, metavar="ID", help="Use known geo_id to skip location lookup.")
@click.option("--page", default=1, type=int, show_default=True, help="Page number (30 restaurants per page).")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def search_restaurants(ctx, location, geo_id, page, json_mode):
    """Search restaurants in LOCATION.

    LOCATION is a destination name like "Paris" or "New York City".
    Use --geo-id to skip the location-lookup step (faster).

    Examples:

      cli-web-tripadvisor restaurants search "Paris"

      cli-web-tripadvisor restaurants search "Paris" --geo-id 187147

      cli-web-tripadvisor restaurants search "Barcelona" --page 2

      cli-web-tripadvisor restaurants search "Rome" --json
    """
    json_mode = resolve_json_mode(json_mode, ctx)

    with handle_errors(json_mode=json_mode):
        with TripAdvisorClient() as client:
            result = client.search_restaurants(location, geo_id=geo_id, page=page)

        restlist = result.get("restaurants", [])

        if json_mode:
            print_json({
                "success": True,
                "location": location,
                "geo_id": result.get("geo_id"),
                "page": page,
                "count": len(restlist),
                "restaurants": [r.to_dict() for r in restlist],
            })
            return

        if not restlist:
            click.echo(
                f"No restaurants found for '{location}' (page {page}). "
                "Try a different location name or --geo-id."
            )
            return

        table = Table(
            title=f"Restaurants in {location} — page {page}",
            show_lines=False,
            expand=False,
        )
        table.add_column("ID", style="dim", no_wrap=True, max_width=10)
        table.add_column("Name", max_width=36)
        table.add_column("Rating", justify="right", max_width=14)
        table.add_column("Price", justify="center", max_width=8)
        table.add_column("Cuisines", max_width=22)
        table.add_column("Phone", max_width=18)

        for r in restlist:
            cuisines = ", ".join(r.cuisines[:2]) if r.cuisines else "—"
            table.add_row(
                r.id,
                truncate(r.name, 36),
                format_rating(r.rating, r.review_count),
                r.price_range or "—",
                cuisines,
                r.telephone or "—",
            )

        console.print(table)
        click.echo(f"\nShowing {len(restlist)} restaurant(s) on page {page}.")
        if len(restlist) >= 30:
            click.echo(f"Next page: restaurants search '{location}' --page {page + 1}")
        click.echo("Tip: Use 'restaurants get URL' with the restaurant URL to see full details.")


@restaurants.command("get")
@click.argument("url")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def get_restaurant(ctx, url, json_mode):
    """Get detailed information for a restaurant by its TripAdvisor URL.

    The URL is the full TripAdvisor restaurant URL from a search result,
    e.g. https://www.tripadvisor.com/Restaurant_Review-g187147-d1035679-Reviews-...

    Examples:

      cli-web-tripadvisor restaurants get "https://www.tripadvisor.com/Restaurant_Review-g187147-d1035679-Reviews-Da_Franco-Paris_Ile_de_France.html"

      cli-web-tripadvisor restaurants get "https://www.tripadvisor.com/Restaurant_Review-..." --json
    """
    json_mode = resolve_json_mode(json_mode, ctx)

    with handle_errors(json_mode=json_mode):
        with TripAdvisorClient() as client:
            rest = client.get_restaurant(url)

        if json_mode:
            print_json({"success": True, "restaurant": rest.to_dict()})
            return

        click.echo(f"\n{'=' * 60}")
        click.echo(f"  {rest.name}")
        click.echo(f"{'=' * 60}")
        click.echo(f"  ID:          {rest.id or '—'}")
        click.echo(f"  Rating:      {format_rating(rest.rating, rest.review_count)}")
        click.echo(f"  Price range: {rest.price_range or '—'}")
        if rest.cuisines:
            click.echo(f"  Cuisines:    {', '.join(rest.cuisines)}")
        click.echo(f"  Address:     {rest.address or '—'}")
        click.echo(f"  City:        {rest.city or '—'}")
        click.echo(f"  Telephone:   {rest.telephone or '—'}")
        click.echo(f"  Coordinates: {rest.latitude or '?'}, {rest.longitude or '?'}")
        if rest.opening_hours:
            click.echo("  Hours:")
            for h in rest.opening_hours[:7]:
                click.echo(f"    {h}")
        click.echo(f"  URL:         {rest.url}")
        click.echo()
