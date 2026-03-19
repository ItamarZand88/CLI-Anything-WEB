"""Users commands for cli-web-producthunt."""

import click

from ..core.client import ProductHuntClient
from ..utils.helpers import handle_errors
from ..utils.output import print_json


@click.group()
def users():
    """Look up Product Hunt users."""


@users.command("get")
@click.argument("username")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def get_user(username, use_json):
    """Get details for a user by username."""
    with handle_errors(json_mode=use_json):
        client = ProductHuntClient()
        user = client.get_user(username=username)

        if use_json:
            print_json(user)
        else:
            d = user.to_dict()
            click.echo(f"Username:    {d.get('username', '')}")
            click.echo(f"Name:        {d.get('name', '')}")
            click.echo(f"Headline:    {d.get('headline', '')}")
            click.echo(f"Followers:   {d.get('followers_count', 0)}")
            if d.get("website_url"):
                click.echo(f"Website:     {d['website_url']}")
