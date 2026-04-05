"""Listings commands for cli-web-airbnb."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table
from rich import box

import datetime

from ..core.client import AirbnbClient
from ..core.exceptions import (
    AirbnbError,
    NetworkError,
    NotFoundError,
    ParseError,
    RateLimitError,
    ServerError,
)
from ..utils.helpers import handle_errors, print_json, resolve_json_mode

console = Console()


def _render_listing_table(listing) -> None:
    """Render a Listing object as a rich detail table."""
    d = listing.to_dict()

    # Header
    console.print()
    console.print(f"[bold cyan]{d.get('name', 'Listing')}[/bold cyan]")
    if d.get("url"):
        console.print(f"[dim]{d['url']}[/dim]")
    console.print()

    # Main info table
    table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    table.add_column("Field", style="bold", min_width=18)
    table.add_column("Value")

    def _add(label: str, value) -> None:
        if value is not None and value != "" and value != []:
            table.add_row(label, str(value))

    _add("ID", d.get("id"))
    _add("Room Type", d.get("room_type"))
    _add("Location", d.get("location"))
    _add("Host", d.get("host_name"))
    _add("Rating", _fmt_rating(d.get("rating"), d.get("review_count")))
    _add("Price", _fmt_price(d.get("price"), d.get("price_qualifier")))
    _add("Bedrooms", d.get("bedrooms"))
    _add("Bathrooms", d.get("bathrooms"))
    _add("Max Guests", d.get("max_guests"))
    _add("Latitude", d.get("latitude"))
    _add("Longitude", d.get("longitude"))

    badges = d.get("badges")
    if badges:
        if isinstance(badges, list):
            _add("Badges", ", ".join(str(b) for b in badges))
        else:
            _add("Badges", badges)

    console.print(table)

    description = d.get("description")
    if description:
        console.print("[bold]Description[/bold]")
        # Wrap long descriptions
        console.print(description[:800] + ("..." if len(description) > 800 else ""))
        console.print()

    amenities = d.get("amenities")
    if amenities:
        console.print("[bold]Amenities[/bold]")
        if isinstance(amenities, list):
            # Print in columns of up to 3
            for i in range(0, len(amenities), 3):
                row = amenities[i : i + 3]
                console.print("  " + "   |   ".join(str(a) for a in row))
        else:
            console.print(str(amenities))
        console.print()


def _fmt_rating(rating, review_count) -> str | None:
    if rating is None:
        return None
    parts = [str(rating)]
    if review_count is not None:
        parts.append(f"({review_count} reviews)")
    return " ".join(parts)


def _fmt_price(price, qualifier) -> str | None:
    if price is None:
        return None
    if qualifier:
        return f"{price} {qualifier}"
    return str(price)


# ---------------------------------------------------------------------------
# Command group
# ---------------------------------------------------------------------------


@click.group("listings", invoke_without_command=True)
@click.pass_context
def listings(ctx):
    """Browse Airbnb listings."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ---------------------------------------------------------------------------
# listings get
# ---------------------------------------------------------------------------


@listings.command("get")
@click.argument("listing_id")
@click.option(
    "--adults",
    type=int,
    default=1,
    show_default=True,
    help="Number of adult guests.",
)
@click.option(
    "--checkin",
    default=None,
    metavar="DATE",
    help="Check-in date (YYYY-MM-DD).",
)
@click.option(
    "--checkout",
    default=None,
    metavar="DATE",
    help="Check-out date (YYYY-MM-DD).",
)
@click.option(
    "--locale",
    default="en",
    show_default=True,
    help="Locale for the request (e.g. en, fr, de).",
)
@click.option(
    "--currency",
    default="USD",
    show_default=True,
    help="Currency for prices (e.g. USD, EUR, GBP).",
)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def listings_get(ctx, listing_id, adults, checkin, checkout, locale, currency, json_mode):
    """Get full details for a listing by ID."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode=json_mode):
        with AirbnbClient(locale=locale, currency=currency) as client:
            listing = client.get_listing(
                listing_id=listing_id,
                adults=adults,
                checkin=checkin,
                checkout=checkout,
            )
        if json_mode:
            print_json({"success": True, **listing.to_dict()})
        else:
            _render_listing_table(listing)


# ---------------------------------------------------------------------------
# listings reviews
# ---------------------------------------------------------------------------


@listings.command("reviews")
@click.argument("listing_id")
@click.option("--limit", type=int, default=24, show_default=True, help="Number of reviews to fetch.")
@click.option("--offset", type=int, default=0, show_default=True, help="Pagination offset.")
@click.option(
    "--sort",
    type=click.Choice(["BEST_QUALITY", "RECENT", "RATING_DESC", "RATING_ASC"], case_sensitive=False),
    default="BEST_QUALITY",
    show_default=True,
    help="Sort order for reviews.",
)
@click.option("--locale", default="en", show_default=True, help="Locale (e.g. en, fr).")
@click.option("--currency", default="USD", show_default=True, help="Currency code.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def listings_reviews(ctx, listing_id, limit, offset, sort, locale, currency, json_mode):
    """Get guest reviews for a listing by ID."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode=json_mode):
        with AirbnbClient(locale=locale, currency=currency) as client:
            result = client.get_reviews(
                listing_id=listing_id,
                limit=limit,
                offset=offset,
                sort=sort.upper(),
            )
        reviews = result["reviews"]
        total = result.get("total_count")
        if json_mode:
            print_json({
                "success": True,
                "listing_id": listing_id,
                "total_count": total,
                "offset": offset,
                "count": len(reviews),
                "reviews": [r.to_dict() for r in reviews],
            })
        else:
            console.print(f"\n[bold cyan]Reviews for listing {listing_id}[/bold cyan]")
            if total is not None:
                console.print(f"[dim]{len(reviews)} of {total} reviews (offset {offset})[/dim]\n")
            for rev in reviews:
                d = rev.to_dict()
                rating_str = f"★ {d['rating']}" if d.get("rating") else ""
                console.print(
                    f"[bold]{d.get('reviewer') or 'Guest'}[/bold] "
                    f"[dim]{d.get('reviewer_location') or ''}[/dim]  "
                    f"{rating_str}  [dim]{d.get('date') or ''}[/dim]"
                )
                if d.get("comment"):
                    console.print(f"  {d['comment'][:300]}")
                if d.get("host_response"):
                    console.print(f"  [dim italic]Host: {d['host_response'][:200]}[/dim italic]")
                console.print()


# ---------------------------------------------------------------------------
# listings availability
# ---------------------------------------------------------------------------


@listings.command("availability")
@click.argument("listing_id")
@click.option("--month", type=int, default=None, help="Starting month 1-12 (default: current month).")
@click.option("--year", type=int, default=None, help="Starting year (default: current year).")
@click.option("--count", type=int, default=12, show_default=True, help="Number of months to fetch.")
@click.option("--available-only", is_flag=True, help="Only show available days.")
@click.option("--locale", default="en", show_default=True, help="Locale (e.g. en, fr).")
@click.option("--currency", default="USD", show_default=True, help="Currency code.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def listings_availability(ctx, listing_id, month, year, count, available_only, locale, currency, json_mode):
    """Get availability calendar for a listing by ID."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode=json_mode):
        with AirbnbClient(locale=locale, currency=currency) as client:
            months = client.get_availability(
                listing_id=listing_id,
                month=month,
                year=year,
                count=count,
            )
        if json_mode:
            print_json({
                "success": True,
                "listing_id": listing_id,
                "months": [m.to_dict() for m in months],
            })
        else:
            console.print(f"\n[bold cyan]Availability for listing {listing_id}[/bold cyan]\n")
            for mon in months:
                d = mon.to_dict()
                days = d["days"]
                if available_only:
                    days = [day for day in days if day.get("available") or day.get("checkin")]
                avail_count = sum(1 for day in d["days"] if day.get("available"))
                console.print(
                    f"[bold]{d['year']}-{d['month']:02d}[/bold]  "
                    f"[green]{avail_count} available days[/green]"
                )
                for day in days:
                    if day.get("available") or day.get("checkin") or not available_only:
                        status = (
                            "[green]✓[/green]" if day.get("available")
                            else ("[yellow]→[/yellow]" if day.get("checkin") else "[red]✗[/red]")
                        )
                        price_str = f"  {day['price']}" if day.get("price") else ""
                        console.print(f"  {status} {day['date']}{price_str}")
                console.print()


