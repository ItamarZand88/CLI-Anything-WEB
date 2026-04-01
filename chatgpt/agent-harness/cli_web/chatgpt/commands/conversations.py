"""Conversation management commands."""

from __future__ import annotations

import click

from ..core.client import ChatGPTClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode, truncate


@click.group("conversations")
def conversations_group():
    """List and view conversations."""


@conversations_group.command("list")
@click.option("--limit", "-n", default=20, help="Number of conversations to show.")
@click.option("--archived", is_flag=True, help="Show archived conversations.")
@click.option("--starred", is_flag=True, help="Show starred conversations only.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def list_conversations(ctx, limit: int, archived: bool, starred: bool, json_mode: bool) -> None:
    """List recent conversations."""
    json_mode = resolve_json_mode(json_mode)

    with handle_errors(json_mode=json_mode):
        with ChatGPTClient() as client:
            data = client.list_conversations(
                limit=limit, archived=archived, starred=starred
            )

            if json_mode:
                print_json({"success": True, "data": data})
                return

            items = data.get("items", [])
            if not items:
                click.echo("No conversations found.")
                return

            click.echo(f"{'Title':<50} {'Updated':<20} {'ID'}")
            click.echo("-" * 100)
            for conv in items:
                title = truncate(conv.get("title", "Untitled"), 48)
                updated = (conv.get("update_time") or "")[:19]
                cid = conv.get("id", "")
                click.echo(f"{title:<50} {updated:<20} {cid}")


@conversations_group.command("get")
@click.argument("conversation_id")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def get_conversation(ctx, conversation_id: str, json_mode: bool) -> None:
    """View a conversation by ID."""
    json_mode = resolve_json_mode(json_mode)

    with handle_errors(json_mode=json_mode):
        with ChatGPTClient() as client:
            data = client.get_conversation(conversation_id)

            if json_mode:
                print_json({"success": True, "data": data})
                return

            title = data.get("title", "Untitled")
            click.echo(f"Conversation: {title}")
            click.echo(f"ID: {conversation_id}")
            click.echo(f"Created: {data.get('create_time', 'unknown')}")
            click.echo(f"Updated: {data.get('update_time', 'unknown')}")

            mapping = data.get("mapping", {})
            if mapping:
                click.echo(f"\nMessages ({len(mapping)}):")
                for msg_id, node in mapping.items():
                    msg = node.get("message")
                    if not msg:
                        continue
                    role = msg.get("author", {}).get("role", "?")
                    content = msg.get("content", {})
                    parts = content.get("parts", [])
                    text = ""
                    for part in parts:
                        if isinstance(part, str):
                            text += part
                    if text:
                        preview = truncate(text, 80)
                        click.echo(f"  [{role}] {preview}")
