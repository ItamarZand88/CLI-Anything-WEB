"""Property detail commands for cli-web-booking."""

from __future__ import annotations

import click

from ..core.client import BookingClient
from ..utils.helpers import handle_errors, print_json
from ..utils.output import format_property_detail


@click.command("get")
@click.argument("slug")
@click.option("--checkin", default=None, help="Check-in date (YYYY-MM-DD).")
@click.option("--checkout", default=None, help="Check-out date (YYYY-MM-DD).")
@click.option("--adults", type=int, default=2, help="Number of adults.")
@click.option("--rooms", type=int, default=1, help="Number of rooms.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def get_property(slug, checkin, checkout, adults, rooms, use_json):
    """Get detailed information about a property.

    SLUG is the property URL path, e.g. "fr/lesenatparis.html"
    """
    with handle_errors(json_mode=use_json):
        client = BookingClient()
        detail = client.get_property(
            slug=slug,
            checkin=checkin,
            checkout=checkout,
            adults=adults,
            rooms=rooms,
        )

        if use_json:
            print_json({"success": True, "property": detail.to_dict()})
        else:
            click.echo()
            click.echo(format_property_detail(detail))
            click.echo()
