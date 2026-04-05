"""Location search commands for cli-web-tripadvisor."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from ..core.client import TripAdvisorClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode, truncate

console = Console()


@click.group("locations")
@click.pass_context
def locations(ctx):
    """Search TripAdvisor destinations and locations."""
    ctx.ensure_object(dict)


@locations.command("search")
@click.argument("query")
@click.option("--max", "max_results", default=6, type=int, show_default=True, help="Maximum number of results.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def search_locations(ctx, query, max_results, json_mode):
    """Search for destinations matching QUERY.

    Returns locations with their geo_id, which can be passed to
    hotels/restaurants/attractions search via --geo-id.

    Examples:

      cli-web-tripadvisor locations search "Paris"

      cli-web-tripadvisor locations search "New York" --max 10

      cli-web-tripadvisor locations search "Tokyo" --json
    """
    json_mode = resolve_json_mode(json_mode, ctx)

    with handle_errors(json_mode=json_mode):
        with TripAdvisorClient() as client:
            results = client.search_locations(query, max_results=max_results)

        if json_mode:
            print_json({
                "success": True,
                "query": query,
                "count": len(results),
                "locations": [loc.to_dict() for loc in results],
            })
            return

        if not results:
            click.echo(f"No locations found for '{query}'.")
            return

        table = Table(
            title=f"TripAdvisor Locations — {query}",
            show_lines=False,
            expand=False,
        )
        table.add_column("Geo ID", style="dim", no_wrap=True, max_width=10)
        table.add_column("Type", max_width=12)
        table.add_column("Name", max_width=50)
        table.add_column("Region", max_width=30)

        for loc in results:
            table.add_row(
                loc.geo_id,
                loc.type,
                loc.name,
                loc.geo_name or loc.parent_name or "",
            )

        console.print(table)
        click.echo(f"\nFound {len(results)} location(s) for '{query}'.")
        click.echo("Tip: Use --geo-id GEO_ID with hotels/restaurants/attractions search for faster results.")
