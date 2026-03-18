"""Evolution commands: list, get."""
import click
from ..core.client import FutbinClient
from ..utils.output import print_json, print_table, print_evolution_detail
from ..utils.helpers import handle_errors, require_year


@click.group()
def evolutions():
    """Player evolutions."""
    pass


@evolutions.command("list")
@click.option("--category", default=None, help="Filter by category.")
@click.option("--expiring", is_flag=True, default=False, help="Show expiring soon only.")
@click.option("--year", type=int, default=None, help="Game year.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def list_evolutions(category, expiring, year, use_json):
    """List available evolutions."""
    with handle_errors(json_mode=use_json):
        yr = require_year(year)
        with FutbinClient() as client:
            evos = client.list_evolutions(category=category, expiring=expiring, year=yr)
        if use_json:
            print_json([e.to_dict() for e in evos])
        else:
            if not evos:
                click.echo("No evolutions found.")
            else:
                print_table(
                    evos,
                    headers=["ID", "Name", "Category", "Expires"],
                    keys=["id", "name", "category", "expires"],
                )


@evolutions.command("get")
@click.argument("evolution_id")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def get_evolution(evolution_id, use_json):
    """Get structured evolution details (requirements, upgrades)."""
    with handle_errors(json_mode=use_json):
        with FutbinClient() as client:
            detail = client.get_evolution_detail(evolution_id)
        print_evolution_detail(detail, json_mode=use_json)
