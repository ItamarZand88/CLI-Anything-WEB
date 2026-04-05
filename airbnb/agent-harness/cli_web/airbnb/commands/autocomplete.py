"""Autocomplete command group — location suggestions."""

from __future__ import annotations

import click

from ..core.client import AirbnbClient
from ..core.exceptions import AirbnbError, NetworkError, NotFoundError, RateLimitError, ServerError
from ..utils.helpers import handle_errors, print_json, resolve_json_mode


@click.group(
    "autocomplete",
    invoke_without_command=True,
)
@click.pass_context
def autocomplete_group(ctx: click.Context) -> None:
    """Autocomplete helpers for Airbnb search inputs (locations, etc.)."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@autocomplete_group.command("locations")
@click.argument("query")
@click.option(
    "--num-results",
    "-n",
    default=5,
    show_default=True,
    type=int,
    help="Maximum number of suggestions to return.",
)
@click.option(
    "--locale",
    default="en",
    show_default=True,
    help="Locale for suggestion labels (e.g. en, fr, de).",
)
@click.option(
    "--currency",
    default="USD",
    show_default=True,
    help="Currency code used for price display context (e.g. USD, EUR).",
)
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    default=False,
    help="Output as JSON.",
)
@click.pass_context
def locations(
    ctx: click.Context,
    query: str,
    num_results: int,
    locale: str,
    currency: str,
    json_mode: bool,
) -> None:
    """Suggest locations matching partial QUERY text.

    Returns ranked location suggestions suitable for use as a destination
    in search commands.

    \b
    Examples:
      autocomplete locations "Lond"
      autocomplete locations "New Y" --num-results 10
      autocomplete locations "Paris" --locale fr --currency EUR --json
    """
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode=json_mode):
        with AirbnbClient(locale=locale, currency=currency) as client:
            suggestions = client.autocomplete_locations(
                query=query,
                num_results=num_results,
            )

        if not suggestions:
            if json_mode:
                print_json({"success": True, "query": query, "suggestions": []})
            else:
                click.echo(f"No location suggestions found for '{query}'.")
            return

        if json_mode:
            print_json(
                {
                    "success": True,
                    "query": query,
                    "suggestions": [s.to_dict() for s in suggestions],
                }
            )
        else:
            click.echo(f"\nLocation suggestions for '{query}':\n")
            for i, suggestion in enumerate(suggestions, start=1):
                click.echo(f"  {i}. {suggestion.display}  [place_id: {suggestion.place_id}]")
            click.echo()
