import click

from cli_web.futbin.core.auth import load_cookies
from cli_web.futbin.core.client import FutbinClient
from cli_web.futbin.utils.output import output_json, output_table


@click.group()
def evolutions():
    """FUTBIN evolution operations."""


@evolutions.command("list")
@click.option("--category", default=None, help="Filter evolutions by category.")
@click.option("--expiring", is_flag=True, help="Show only expiring evolutions.")
@click.pass_context
def list_evolutions(ctx, category, expiring):
    """List available evolutions."""
    client = FutbinClient(cookies=load_cookies())
    items = client.list_evolutions(category=category, expiring=expiring)

    if ctx.obj.get("json", False):
        output_json([vars(e) for e in items])
    else:
        rows = [[e.name, e.category, e.expires] for e in items]
        output_table(["Name", "Category", "Expires"], rows)
