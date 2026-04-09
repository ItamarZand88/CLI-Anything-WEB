"""Network/connections commands for cli-web-linkedin."""
from __future__ import annotations

import click

from ..core.client import LinkedinClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode


def _get_text(obj, *keys) -> str:
    """Safely drill into nested dicts and return a string."""
    current = obj
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return ""
    if isinstance(current, dict):
        return current.get("text", str(current))
    return str(current) if current else ""


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
        with LinkedinClient() as client:
            data = client.get_connections(count=limit)
            summary = client.get_connection_count()

        if json_mode:
            print_json(data)
            return

        # Show total count
        num = summary.get("numConnections", 0)
        if num:
            click.echo(f"  You have {num:,} connections.\n")

        # Extract profiles from included array
        profiles = []
        for inc in data.get("included", []):
            t = inc.get("$type", "")
            if "Profile" in t and "firstName" in inc:
                first = inc.get("firstName", "")
                last = inc.get("lastName", "")
                headline = inc.get("headline", "")
                profiles.append((f"{first} {last}".strip(), headline))

        if not profiles:
            click.echo("  No connections found.")
            return

        for i, (name, headline) in enumerate(profiles[:limit], 1):
            click.echo(f"  {i}. {name}")
            if headline:
                click.secho(f"     {headline}", fg="bright_black")


@network.command("invitations")
@click.option("--limit", default=10, type=int, help="Max results.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def invitations(ctx, limit, json_mode):
    """View pending connection invitations."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
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
            urn = inv.get("entityUrn", "")
            click.echo(f"  {title} — {subtitle}")
            if urn:
                click.secho(f"    URN: {urn}", fg="bright_black")


@network.command("accept")
@click.argument("invitation_urn")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def accept(ctx, invitation_urn, json_mode):
    """Accept a connection invitation by URN."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
            client.accept_invitation(invitation_urn)
        if json_mode:
            print_json({"success": True, "accepted": invitation_urn})
        else:
            click.echo("  Invitation accepted.")


@network.command("decline")
@click.argument("invitation_urn")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def decline(ctx, invitation_urn, json_mode):
    """Decline a connection invitation by URN."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
            client.decline_invitation(invitation_urn)
        if json_mode:
            print_json({"success": True, "declined": invitation_urn})
        else:
            click.echo("  Invitation declined.")


@network.command("connect")
@click.argument("profile_urn")
@click.option("--message", "-m", default="", help="Connection message.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def connect(ctx, profile_urn, message, json_mode):
    """Send a connection request."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
            result = client.send_connection(profile_urn, message=message)
        if json_mode:
            print_json({"success": True, "result": result})
        else:
            click.echo("  Connection request sent.")
