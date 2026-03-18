import click

from cli_web.futbin.core.auth import load_cookies
from cli_web.futbin.core.client import FutbinClient
from cli_web.futbin.utils.output import output_json, output_sbcs_table, output_table


@click.group()
def sbc():
    """FUTBIN SBC operations."""


@sbc.command("list")
@click.option(
    "--category",
    type=click.Choice(
        ["Players", "Upgrades", "Challenges", "Icons", "Expiring-soon"],
        case_sensitive=False,
    ),
    default=None,
    help="Filter SBCs by category.",
)
@click.pass_context
def list_sbcs(ctx, category):
    """List available SBCs, optionally filtered by category."""
    client = FutbinClient(cookies=load_cookies())
    sbcs = client.list_sbcs(category=category)
    if ctx.obj.get("json", False):
        output_json(sbcs)
    else:
        output_sbcs_table(sbcs)


@sbc.command("cheapest")
@click.pass_context
def cheapest(ctx):
    """Show the cheapest players by rating."""
    client = FutbinClient(cookies=load_cookies())
    data = client.get_cheapest_by_rating()
    if ctx.obj.get("json", False):
        output_json(data)
    else:
        headers = ["Rating", "Price", "Player"]
        rows = [[d["rating"], d["price"], d["player"]] for d in data]
        output_table(headers, rows)


@sbc.command("best")
@click.pass_context
def best(ctx):
    """Show all SBCs across every category."""
    client = FutbinClient(cookies=load_cookies())
    sbcs = client.list_sbcs()
    if ctx.obj.get("json", False):
        output_json(sbcs)
    else:
        output_sbcs_table(sbcs)
