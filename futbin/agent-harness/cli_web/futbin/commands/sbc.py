"""SBC commands: list, get."""
import click
from ..core.client import FutbinClient
from ..utils.output import print_json, print_table, print_sbc_detail
from ..utils.helpers import handle_errors, require_year


@click.group()
def sbc():
    """Squad Building Challenges."""
    pass


@sbc.command("list")
@click.option("--category", default=None, help="Filter by SBC category.")
@click.option("--year", type=int, default=None, help="Game year.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def list_sbcs(category, year, use_json):
    """List available SBCs."""
    with handle_errors(json_mode=use_json):
        yr = require_year(year)
        with FutbinClient() as client:
            sbcs = client.list_sbcs(category=category, year=yr)
        if use_json:
            print_json([s.to_dict() for s in sbcs])
        else:
            if not sbcs:
                click.echo("No SBCs found.")
            else:
                print_table(
                    sbcs,
                    headers=["ID", "Name", "Category", "Reward", "Expires"],
                    keys=["id", "name", "category", "reward", "expires"],
                )


@sbc.command("get")
@click.argument("sbc_id")
@click.option("--year", type=int, default=None, help="Game year.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def get_sbc(sbc_id, year, use_json):
    """Get structured SBC details (requirements, rewards)."""
    with handle_errors(json_mode=use_json):
        yr = require_year(year)
        with FutbinClient() as client:
            detail = client.get_sbc_detail(sbc_id, year=yr)
        print_sbc_detail(detail, json_mode=use_json)
