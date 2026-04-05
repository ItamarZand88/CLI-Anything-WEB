"""Hotel commands for cli-web-tripadvisor."""

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


@click.group("hotels")
@click.pass_context
def hotels(ctx):
    """Search and browse TripAdvisor hotels."""
    ctx.ensure_object(dict)


@hotels.command("search")
@click.argument("location")
@click.option("--geo-id", default=None, metavar="ID", help="Use known geo_id to skip location lookup.")
@click.option("--page", default=1, type=int, show_default=True, help="Page number (30 hotels per page).")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def search_hotels(ctx, location, geo_id, page, json_mode):
    """Search hotels in LOCATION.

    LOCATION is a destination name like "Paris" or "New York City".
    Use --geo-id to skip the location-lookup step (faster).

    Examples:

      cli-web-tripadvisor hotels search "Paris"

      cli-web-tripadvisor hotels search "Paris" --geo-id 187147

      cli-web-tripadvisor hotels search "Tokyo" --page 2

      cli-web-tripadvisor hotels search "London" --json
    """
    json_mode = resolve_json_mode(json_mode, ctx)

    with handle_errors(json_mode=json_mode):
        with TripAdvisorClient() as client:
            result = client.search_hotels(location, geo_id=geo_id, page=page)

        hotellist = result.get("hotels", [])

        if json_mode:
            print_json({
                "success": True,
                "location": location,
                "geo_id": result.get("geo_id"),
                "page": page,
                "count": len(hotellist),
                "hotels": [h.to_dict() for h in hotellist],
            })
            return

        if not hotellist:
            click.echo(
                f"No hotels found for '{location}' (page {page}). "
                "Try a different location name or --geo-id."
            )
            return

        table = Table(
            title=f"Hotels in {location} — page {page}",
            show_lines=False,
            expand=False,
        )
        table.add_column("ID", style="dim", no_wrap=True, max_width=10)
        table.add_column("Name", max_width=38)
        table.add_column("Rating", justify="right", max_width=14)
        table.add_column("Price", justify="center", max_width=8)
        table.add_column("City", max_width=16)
        table.add_column("Phone", max_width=18)

        for h in hotellist:
            table.add_row(
                h.id,
                truncate(h.name, 38),
                format_rating(h.rating, h.review_count),
                h.price_range or "—",
                h.city or "—",
                h.telephone or "—",
            )

        console.print(table)
        click.echo(f"\nShowing {len(hotellist)} hotel(s) on page {page}.")
        if len(hotellist) >= 30:
            click.echo(f"Next page: hotels search '{location}' --page {page + 1}")
        click.echo("Tip: Use 'hotels get URL' with the hotel URL to see full details.")


@hotels.command("get")
@click.argument("url")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def get_hotel(ctx, url, json_mode):
    """Get detailed information for a hotel by its TripAdvisor URL.

    The URL is the full TripAdvisor hotel URL from a search result,
    e.g. https://www.tripadvisor.com/Hotel_Review-g187147-d229968-Reviews-...

    Examples:

      cli-web-tripadvisor hotels get "https://www.tripadvisor.com/Hotel_Review-g187147-d229968-Reviews-Hotel_Astra_Opera_Astotel-Paris_Ile_de_France.html"

      cli-web-tripadvisor hotels get "https://www.tripadvisor.com/Hotel_Review-..." --json
    """
    json_mode = resolve_json_mode(json_mode, ctx)

    with handle_errors(json_mode=json_mode):
        with TripAdvisorClient() as client:
            hotel = client.get_hotel(url)

        if json_mode:
            print_json({"success": True, "hotel": hotel.to_dict()})
            return

        click.echo(f"\n{'=' * 60}")
        click.echo(f"  {hotel.name}")
        click.echo(f"{'=' * 60}")
        click.echo(f"  ID:          {hotel.id or '—'}")
        click.echo(f"  Rating:      {format_rating(hotel.rating, hotel.review_count)}")
        click.echo(f"  Price range: {hotel.price_range or '—'}")
        click.echo(f"  Address:     {hotel.address or '—'}")
        click.echo(f"  City:        {hotel.city or '—'}")
        click.echo(f"  Country:     {hotel.country or '—'}")
        click.echo(f"  Telephone:   {hotel.telephone or '—'}")
        click.echo(f"  Coordinates: {hotel.latitude or '?'}, {hotel.longitude or '?'}")
        if hotel.amenities:
            click.echo(f"  Amenities:   {', '.join(hotel.amenities[:10])}")
            if len(hotel.amenities) > 10:
                click.echo(f"               ... and {len(hotel.amenities) - 10} more")
        click.echo(f"  URL:         {hotel.url}")
        click.echo()
