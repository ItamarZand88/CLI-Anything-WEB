"""SBC (Squad Building Challenge) commands for cli-web-futbin."""
import click

from cli_web.futbin.core.client import FutbinClient
from cli_web.futbin.utils.output import print_json, print_table, print_error, coins_display


@click.group()
def sbc():
    """Squad Building Challenges — list and view SBCs."""


@sbc.command("list")
@click.option("--category", "-c", default=None,
              help="Category filter (Players, Upgrades, Challenges, Icons, etc.)")
@click.option("--year", "-y", default=26, show_default=True, help="Game year")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_sbcs(category, year, as_json):
    """List all Squad Building Challenges."""
    with FutbinClient() as client:
        try:
            sbcs = client.list_sbcs(category=category, year=year)
        except Exception as e:
            print_error(str(e))
            return

    if as_json:
        print_json([s.to_dict() for s in sbcs])
    else:
        if not sbcs:
            click.echo("No SBCs found.")
            return
        rows = [
            {
                "id": s.id,
                "name": s.name[:40],
                "cost_ps": coins_display(s.cost_ps),
                "expires": s.expires,
                "repeatable": "Yes" if s.repeatable else "No",
            }
            for s in sbcs
        ]
        print_table(rows, ["id", "name", "cost_ps", "expires", "repeatable"])


@sbc.command("get")
@click.option("--id", "sbc_id", required=True, type=int, help="SBC ID")
@click.option("--year", "-y", default=26, show_default=True, help="Game year")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def get_sbc(sbc_id, year, as_json):
    """Get SBC details and requirements."""
    with FutbinClient() as client:
        try:
            detail = client.get_sbc(sbc_id, year=year)
        except Exception as e:
            print_error(str(e))
            return

    if as_json:
        print_json(detail)
    else:
        click.echo(f"\nSBC: {detail['name']}")
        click.echo(f"URL: {detail['url']}")
        click.echo(f"\n--- Details ---")
        click.echo(detail.get("raw_text", "")[:1000])
