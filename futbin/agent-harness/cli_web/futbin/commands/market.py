"""Market commands for cli-web-futbin."""
import click

from cli_web.futbin.core.client import FutbinClient
from cli_web.futbin.utils.output import print_json, print_table, print_error


@click.group()
def market():
    """EA FC market data and price index."""


@market.command("index")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def market_index(as_json: bool):
    """Show the EA FC market price index."""
    with FutbinClient() as client:
        try:
            items = client.get_market_index()
        except Exception as e:
            print_error(str(e))

    if as_json:
        print_json([i.to_dict() for i in items])
    else:
        if not items:
            click.echo("No market data available.")
            return
        rows = [{"name": i.name, "last": i.last, "change_%": i.change_pct} for i in items]
        print_table(rows, ["name", "last", "change_%"])
