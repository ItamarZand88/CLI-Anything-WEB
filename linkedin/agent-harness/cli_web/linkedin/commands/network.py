"""Network/connections commands for cli-web-linkedin."""
from __future__ import annotations

import click

from ..core.client import LinkedinClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode


@click.group("network")
def network():
    """View connections, invitations, and manage your network."""


@network.command("connections")
@click.option("--limit", default=20, type=int, help="Max results.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def connections(ctx, limit, json_mode):
    """List your connections."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        client = LinkedinClient()
        data = client.get_connections(count=limit)

        if json_mode:
            print_json(data)
            return

        num = data.get("numConnections", 0)
        if num:
            click.echo(f"  You have {num:,} connections.")
        else:
            click.echo("  No connections data available.")


@network.command("invitations")
@click.option("--limit", default=10, type=int, help="Max results.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def invitations(ctx, limit, json_mode):
    """View pending connection invitations."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        client = LinkedinClient()
        data = client.get_invitations(count=limit)

        if json_mode:
            print_json(data)
            return

        elements = data.get("elements", [])
        if not elements:
            click.echo("  No pending invitations.")
            return

        click.echo(f"  {len(elements)} pending invitation(s):\n")
        for inv in elements[:limit]:
            title = inv.get("title", "")
            subtitle = inv.get("subtitle", "")
            click.echo(f"  {title} — {subtitle}")


@network.command("connect")
@click.argument("profile_urn")
@click.option("--message", "-m", default="", help="Connection message.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def connect(ctx, profile_urn, message, json_mode):
    """Send a connection request."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        client = LinkedinClient()
        result = client.send_connection(profile_urn, message=message)
        if json_mode:
            print_json({"success": True, "result": result})
        else:
            click.echo("  Connection request sent.")
