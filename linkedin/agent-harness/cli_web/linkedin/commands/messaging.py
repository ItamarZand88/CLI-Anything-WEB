"""Messaging commands for cli-web-linkedin."""
from __future__ import annotations

import click

from ..core.client import LinkedinClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode


@click.group("messaging")
def messaging():
    """Read and send LinkedIn messages."""


@messaging.command("list")
@click.option("--limit", default=20, type=int, help="Max conversations.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def list_conversations(ctx, limit, json_mode):
    """List your recent conversations."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
            data = client.get_conversations(count=limit)
            my_urn = client.get_my_profile_urn()

        if json_mode:
            print_json(data)
            return

        # Extract conversations from GraphQL response
        gql_data = data.get("data", {})
        for key, val in gql_data.items():
            if isinstance(val, dict) and "elements" in val:
                elements = val["elements"]
                if not elements:
                    click.echo("  No conversations.")
                    return
                click.echo(f"  {len(elements)} conversation(s):\n")
                for i, el in enumerate(elements[:limit], 1):
                    urn = el.get("entityUrn", "")
                    # Extract participant names, filtering out self by URN
                    names = []
                    for p in el.get("conversationParticipants", []):
                        member = (p.get("participantType") or {}).get("member")
                        if not member:
                            continue
                        p_urn = member.get("entityUrn", "")
                        if p_urn == my_urn:
                            continue  # skip self
                        fn = member.get("firstName", {})
                        ln = member.get("lastName", {})
                        first = fn.get("text", "") if isinstance(fn, dict) else str(fn or "")
                        last = ln.get("text", "") if isinstance(ln, dict) else str(ln or "")
                        full = f"{first} {last}".strip()
                        if full:
                            names.append(full)
                    label = ", ".join(names) if names else urn[:50]
                    click.echo(f"  {i}. {label}")
                return

        click.echo("  No conversations found.")


@messaging.command("send")
@click.argument("recipient")
@click.argument("text")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def send_message(ctx, recipient, text, json_mode):
    """Send a message. RECIPIENT can be a conversation URN or profile URN."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
            result = client.send_message(recipient, text)
        if json_mode:
            print_json({"success": True, "result": result})
        else:
            click.echo("  Message sent.")
