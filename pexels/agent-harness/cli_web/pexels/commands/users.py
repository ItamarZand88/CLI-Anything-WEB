"""Users commands for cli-web-pexels."""

import click

from ..core.client import PexelsClient
from ..utils.helpers import handle_errors
from ..utils.output import print_json, print_pagination, print_user_detail


@click.group("users")
@click.pass_context
def users(ctx):
    """Browse user profiles and their media."""
    pass


@users.command("get")
@click.argument("username")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def get(ctx, username, json_mode):
    """Get a user's profile information."""
    json_mode = json_mode or ctx.obj.get("json", False)
    with handle_errors(json_mode):
        client = PexelsClient()
        result = client.get_user(username)
        if json_mode:
            print_json(result)
        else:
            print_user_detail(result["user"])


@users.command("media")
@click.argument("username")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def media(ctx, username, page, json_mode):
    """List a user's uploaded photos and videos."""
    json_mode = json_mode or ctx.obj.get("json", False)
    with handle_errors(json_mode):
        client = PexelsClient()
        result = client.get_user_media(username, page=page)
        if json_mode:
            print_json(result)
        else:
            items = result.get("data", [])
            if not items:
                click.echo(f"  No media found for @{username}.")
                return

            click.echo(f"\n  Media by @{username}")
            click.echo(f"  {'ID':<12} {'Type':<8} {'Title':<35} {'Size':<12}")
            click.echo(f"  {'─' * 12} {'─' * 8} {'─' * 35} {'─' * 12}")
            for item in items:
                title = (item.get("title") or "Untitled")[:34]
                size = f"{item.get('width', '?')}x{item.get('height', '?')}"
                click.echo(
                    f"  {item.get('id', ''):<12} {item.get('type', 'photo'):<8} "
                    f"{title:<35} {size:<12}"
                )
            print_pagination(result.get("pagination", {}))
