"""Search commands for cli-web-airbnb."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from ..core.client import AirbnbClient
from ..core.exceptions import AirbnbError, NetworkError, NotFoundError, ParseError, RateLimitError, ServerError
from ..utils.helpers import handle_errors, print_json, resolve_json_mode

console = Console()


@click.group("search", invoke_without_command=True)
@click.pass_context
def search(ctx):
    """Search Airbnb stays by location, dates, and filters."""
    ctx.ensure_object(dict)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@search.command("stays")
@click.argument("location")
@click.option("--checkin", default=None, metavar="DATE", help="Check-in date (YYYY-MM-DD).")
@click.option("--checkout", default=None, metavar="DATE", help="Check-out date (YYYY-MM-DD).")
@click.option("--adults", default=1, type=int, show_default=True, help="Number of adults.")
@click.option("--children", default=0, type=int, help="Number of children.")
@click.option("--infants", default=0, type=int, help="Number of infants.")
@click.option("--pets", default=0, type=int, help="Number of pets (0 or 1).")
@click.option("--min-price", default=None, type=int, metavar="N", help="Minimum price per night.")
@click.option("--max-price", default=None, type=int, metavar="N", help="Maximum price per night.")
@click.option(
    "--room-type",
    "room_types",
    multiple=True,
    type=click.Choice(
        ["entire_home", "private_room", "shared_room", "hotel_room"],
        case_sensitive=False,
    ),
    help="Filter by room type (repeatable).",
)
@click.option(
    "--amenity",
    "amenities",
    multiple=True,
    type=int,
    metavar="ID",
    help="Filter by amenity ID (repeatable). Common: 4=WiFi, 8=Kitchen, 40=AC, 33=Pool.",
)
@click.option("--cursor", default=None, metavar="TOKEN", help="Pagination cursor for next page.")
@click.option("--page", default=None, type=int, metavar="N", help="Page indicator (informational; Airbnb uses cursor-based pagination).")
@click.option("--locale", default="en", show_default=True, help="Language locale code.")
@click.option("--currency", default="USD", show_default=True, help="Currency code.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def search_stays(
    ctx,
    location,
    checkin,
    checkout,
    adults,
    children,
    infants,
    pets,
    min_price,
    max_price,
    room_types,
    amenities,
    cursor,
    page,
    locale,
    currency,
    json_mode,
):
    """Search for stays in LOCATION.

    LOCATION can be a place name like "London, UK" or "Paris, France".
    Spaces and commas are handled automatically.

    Examples:

      cli-web-airbnb search stays "London, UK"

      cli-web-airbnb search stays "Paris, France" --checkin 2024-06-01 --checkout 2024-06-05

      cli-web-airbnb search stays "New York, NY" --adults 2 --max-price 200 --json

      cli-web-airbnb search stays "Tokyo, Japan" --room-type private_room --room-type entire_home

      cli-web-airbnb search stays "Barcelona, Spain" --cursor eyJ...
    """
    json_mode = resolve_json_mode(json_mode, ctx)

    if page is not None and not json_mode:
        click.echo("Note: --page is informational only. Airbnb uses cursor-based pagination. Use --cursor to navigate pages.", err=True)

    # Map CLI room type values to Airbnb API display values
    room_type_map = {
        "entire_home": "Entire home/apt",
        "private_room": "Private room",
        "shared_room": "Shared room",
        "hotel_room": "Hotel room",
    }
    api_room_types = [room_type_map[rt] for rt in room_types] if room_types else None

    with handle_errors(json_mode=json_mode):
        with AirbnbClient(locale=locale, currency=currency) as client:
            result = client.search_stays(
                location=location,
                adults=adults,
                children=children,
                infants=infants,
                pets=pets,
                checkin=checkin,
                checkout=checkout,
                price_min=min_price,
                price_max=max_price,
                room_types=api_room_types,
                amenities=list(amenities) if amenities else None,
                cursor=cursor,
            )

        listings = result.get("listings", [])
        next_cursor = result.get("next_cursor")
        total_count = result.get("total_count")
        location_slug = result.get("location_slug")

        if json_mode:
            print_json({
                "success": True,
                "count": len(listings),
                "next_cursor": next_cursor,
                "total_count": total_count,
                "location_slug": location_slug,
                "listings": [listing.to_dict() for listing in listings],
            })
            return

        if not listings:
            click.echo(f"No stays found for '{location}'.")
            return

        # Build Rich table
        title_parts = [f"Airbnb Stays — {location}"]
        if checkin and checkout:
            title_parts.append(f"{checkin} → {checkout}")
        if total_count is not None:
            title_parts.append(f"{total_count:,} total")

        table = Table(title="  |  ".join(title_parts), show_lines=False, expand=False)
        table.add_column("ID", style="dim", no_wrap=True, max_width=12)
        table.add_column("Name", max_width=42)
        table.add_column("Rating", justify="right", max_width=10)
        table.add_column("Price", justify="right", max_width=14)
        table.add_column("Badges", max_width=22)

        for listing in listings:
            d = listing.to_dict()

            listing_id = str(d.get("id", ""))
            # Show last 8 chars for brevity (Airbnb IDs are long integers)
            short_id = listing_id[-8:] if len(listing_id) > 8 else listing_id

            name = d.get("name") or ""
            # Truncate long names with ellipsis
            if len(name) > 42:
                name = name[:39] + "..."

            rating_val = d.get("rating")
            rating = str(rating_val) if rating_val is not None else "—"

            price_val = d.get("price")
            price = str(price_val) if price_val is not None else "—"

            badges_val = d.get("badges")
            if isinstance(badges_val, list):
                badges = ", ".join(str(b) for b in badges_val) if badges_val else ""
            else:
                badges = str(badges_val) if badges_val else ""

            table.add_row(short_id, name, rating, price, badges)

        console.print(table)
        click.echo(f"\nShowing {len(listings)} listing(s).", nl=False)
        if total_count is not None:
            click.echo(f"  ({total_count:,} total available)", nl=False)
        click.echo()

        if next_cursor:
            click.echo(f"Next page: --cursor '{next_cursor}'")
