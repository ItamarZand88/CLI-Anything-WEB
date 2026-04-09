"""Notifications commands for cli-web-linkedin."""
from __future__ import annotations

import click

from ..core.client import LinkedinClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode


@click.command("notifications")
@click.option("--limit", default=20, type=int, help="Max notifications.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def notifications(ctx, limit, json_mode):
    """View your notifications."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        client = LinkedinClient()
        data = client.get_notifications(count=limit)

        if json_mode:
            print_json(data)
            return

        elements = data.get("elements", [])
        if not elements:
            click.echo("  No notifications.")
            return

        for i, el in enumerate(elements[:limit], 1):
            headline = el.get("headline", {})
            text = headline.get("text", "") if isinstance(headline, dict) else str(headline or "")
            template = el.get("template", {})
            entity_name = ""
            if isinstance(template, dict):
                actor = template.get("actorName", {})
                entity_name = actor.get("text", "") if isinstance(actor, dict) else str(actor or "")
            if entity_name:
                click.echo(f"  {i}. {entity_name}: {text[:80]}")
            elif text:
                click.echo(f"  {i}. {text[:80]}")
