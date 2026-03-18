"""Click command group for FUTBIN market operations."""

import click

from cli_web.futbin.core.auth import load_cookies
from cli_web.futbin.core.client import FutbinClient
from cli_web.futbin.utils.output import output_json, output_market_table


@click.group()
def market():
    """FUTBIN market operations."""


@market.command()
@click.option(
    "--rating",
    type=click.IntRange(81, 86),
    default=None,
    help="Filter by player rating (81-86).",
)
@click.pass_context
def index(ctx, rating):
    """Show the FUTBIN market index."""
    use_json = ctx.obj.get("json", False)
    client = FutbinClient(cookies=load_cookies())
    indices = client.get_market_index(rating=rating)
    if use_json:
        output_json(indices)
    else:
        output_market_table(indices)
