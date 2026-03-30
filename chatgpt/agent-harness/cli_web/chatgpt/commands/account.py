"""Account and model commands."""

from __future__ import annotations

import click

from ..core.client import ChatGPTClient
from ..utils.helpers import handle_errors, print_json


@click.command("me")
@click.pass_context
def me(ctx) -> None:
    """Show current user info."""
    json_mode = ctx.obj.get("json", False) if ctx.obj else False

    with handle_errors(json_mode=json_mode):
        with ChatGPTClient() as client:
            data = client.get_me()

            if json_mode:
                print_json({"success": True, "data": data})
                return

            click.echo(f"Name:  {data.get('name', 'Unknown')}")
            click.echo(f"Email: {data.get('email', 'Unknown')}")
            click.echo(f"ID:    {data.get('id', 'Unknown')}")
            orgs = data.get("orgs", {}).get("data", [])
            if orgs:
                org = orgs[0]
                click.echo(f"Org:   {org.get('title', 'Unknown')}")


@click.command("models")
@click.pass_context
def models(ctx) -> None:
    """List available models."""
    json_mode = ctx.obj.get("json", False) if ctx.obj else False

    with handle_errors(json_mode=json_mode):
        with ChatGPTClient() as client:
            model_list = client.get_models()

            if json_mode:
                print_json({"success": True, "data": model_list})
                return

            click.echo(f"{'Slug':<30} {'Title':<30} {'Tags'}")
            click.echo("-" * 80)
            for m in model_list:
                slug = m.get("slug", "?")
                title = m.get("title", "?")
                tags = ", ".join(m.get("tags", []))
                click.echo(f"{slug:<30} {title:<30} {tags}")
