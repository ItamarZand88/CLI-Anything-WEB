"""Auth commands for cli-web-producthunt."""

import click

from ..core.auth import get_auth_status
from ..utils.helpers import handle_errors
from ..utils.output import print_json


@click.group("auth")
def auth():
    """Authentication status (no auth required for HTML scraping)."""


@auth.command("status")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def status(use_json):
    """Show current authentication status."""
    with handle_errors(json_mode=use_json):
        info = get_auth_status()

        if use_json:
            print_json(info)
        else:
            for key, value in info.items():
                click.echo(f"{key}: {value}")
