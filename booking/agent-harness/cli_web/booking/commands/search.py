"""Search and autocomplete commands for cli-web-booking."""

from __future__ import annotations

from datetime import date, timedelta

import click

from ..core.client import BookingClient
from ..utils.helpers import handle_errors, print_json
from ..utils.output import format_destination_row, format_property_row


def _default_checkin() -> str:
    """Default check-in: tomorrow."""
    return (date.today() + timedelta(days=1)).isoformat()


def _default_checkout() -> str:
    """Default check-out: 3 days from now."""
    return (date.today() + timedelta(days=3)).isoformat()


@click.group("search")
def search_group():
    """Search for properties on Booking.com."""


@search_group.command("find")
@click.argument("destination")
@click.option("--checkin", default=None, help="Check-in date (YYYY-MM-DD). Default: tomorrow.")
@click.option("--checkout", default=None, help="Check-out date (YYYY-MM-DD). Default: +3 days.")
@click.option("--adults", type=int, default=2, help="Number of adults.")
@click.option("--rooms", type=int, default=1, help="Number of rooms.")
@click.option("--children", type=int, default=0, help="Number of children.")
@click.option("--sort", type=click.Choice(["popularity", "price", "review_score", "distance"]),
              default=None, help="Sort order.")
@click.option("--page", type=int, default=1, help="Results page number.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def search_find(destination, checkin, checkout, adults, rooms, children,
                sort, page, use_json):
    """Search properties by destination and dates."""
    with handle_errors(json_mode=use_json):
        checkin = checkin or _default_checkin()
        checkout = checkout or _default_checkout()

        client = BookingClient()
        offset = (page - 1) * 25
        results = client.search(
            destination=destination,
            checkin=checkin,
            checkout=checkout,
            adults=adults,
            rooms=rooms,
            children=children,
            sort=sort,
            offset=offset,
        )

        if use_json:
            print_json({
                "success": True,
                "destination": destination,
                "checkin": checkin,
                "checkout": checkout,
                "count": len(results),
                "properties": [p.to_dict() for p in results],
            })
        else:
            if not results:
                click.echo("No properties found.")
                return

            click.echo(f"\n  Found {len(results)} properties in {destination}")
            click.echo(f"  {checkin} → {checkout} | {adults} adults, {rooms} room(s)\n")

            from ..utils.repl_skin import ReplSkin
            skin = ReplSkin("booking")
            headers = ["Name", "Score", "Rating", "Reviews", "Price", "Location"]
            rows = [format_property_row(p) for p in results]
            skin.table(headers, rows)
            click.echo()


@click.command("autocomplete")
@click.argument("query")
@click.option("--limit", type=int, default=5, help="Max results.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def autocomplete(query, limit, use_json):
    """Resolve a destination name to IDs."""
    with handle_errors(json_mode=use_json):
        client = BookingClient()
        results = client.autocomplete(query, limit=limit)

        if use_json:
            print_json({
                "success": True,
                "query": query,
                "results": [d.to_dict() for d in results],
            })
        else:
            if not results:
                click.echo("No destinations found.")
                return

            from ..utils.repl_skin import ReplSkin
            skin = ReplSkin("booking")
            headers = ["Name", "Type", "ID", "Full Label"]
            rows = [format_destination_row(d) for d in results]
            skin.table(headers, rows)
