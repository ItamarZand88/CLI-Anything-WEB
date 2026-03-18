"""Evolutions commands for cli-web-futbin."""
import click

from cli_web.futbin.core.client import FutbinClient
from cli_web.futbin.utils.output import print_json, print_table, print_error


@click.group()
def evolutions():
    """Player evolutions — list and browse evolution paths."""


@evolutions.command("list")
@click.option("--category", "-c", type=int, default=None,
              help="Category ID filter")
@click.option("--expiring", is_flag=True, help="Show only expiring soon")
@click.option("--year", "-y", default=26, show_default=True, help="Game year")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_evolutions(category, expiring, year, as_json):
    """List available player evolutions."""
    with FutbinClient() as client:
        try:
            evo_list = client.list_evolutions(category=category, expiring=expiring, year=year)
        except Exception as e:
            print_error(str(e))
            return

    if as_json:
        print_json([e.to_dict() for e in evo_list])
    else:
        if not evo_list:
            click.echo("No evolutions found.")
            return
        rows = [
            {
                "id": e.id,
                "name": e.name[:40],
                "category": e.category,
                "expires": e.expires,
                "repeatable": "Yes" if e.repeatable else "No",
            }
            for e in evo_list
        ]
        print_table(rows, ["id", "name", "category", "expires", "repeatable"])


@evolutions.command("get")
@click.option("--id", "evo_id", required=True, type=int, help="Evolution ID")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def get_evolution(evo_id, as_json):
    """Get evolution details and requirements."""
    with FutbinClient() as client:
        try:
            detail = client.get_evolution(evo_id)
        except Exception as e:
            print_error(str(e))
            return

    if as_json:
        print_json(detail)
    else:
        click.echo(f"\nEvolution: {detail['name']}")
        click.echo(f"URL: {detail['url']}")
        click.echo(f"\n--- Details ---")
        click.echo(detail.get("raw_text", "")[:1000])
