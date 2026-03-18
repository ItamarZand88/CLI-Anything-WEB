"""Market commands: index."""
import click
from ..core.client import FutbinClient
from ..utils.output import print_json, print_table
from ..utils.helpers import handle_errors


@click.group()
def market():
    """FUTBIN market data."""
    pass


@market.command("index")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def index(use_json):
    """Show market index (price trends)."""
    with handle_errors(json_mode=use_json):
        with FutbinClient() as client:
            items = client.get_market_index()
        if use_json:
            print_json([i.to_dict() for i in items])
        else:
            if not items:
                click.echo("No market data available.")
            else:
                print_table(
                    items,
                    headers=["Name", "Last", "Change %"],
                    keys=["name", "last", "change_pct"],
                )
