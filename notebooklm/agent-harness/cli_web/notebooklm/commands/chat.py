"""Chat / query commands."""

from __future__ import annotations

from typing import Any

import click

from cli_web.notebooklm.core.client import NotebookLMClient
from cli_web.notebooklm.core.models import ChatMessage, ChatSession
from cli_web.notebooklm.utils.config import RPC_CHAT_SESSIONS
from cli_web.notebooklm.utils.output import output_json, output_error, truncate


@click.group("chat")
def chat_group():
    """Query notebooks and view chat history."""
    pass


@chat_group.command("query")
@click.argument("notebook_id")
@click.argument("question")
@click.option("--source", "source_ids", multiple=True, help="Scope to specific source IDs.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def query(notebook_id: str, question: str, source_ids: tuple[str, ...], as_json: bool):
    """Send a question to a notebook and get a streaming response."""
    try:
        client = NotebookLMClient()
        result = client.query_stream(
            notebook_id=notebook_id,
            query=question,
            source_ids=list(source_ids) if source_ids else None,
        )
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    if as_json:
        output_json({
            "notebook_id": notebook_id,
            "question": question,
            "response": result,
        })
        return

    click.echo(result)


@chat_group.command("history")
@click.argument("notebook_id")
@click.option("--limit", default=20, help="Maximum number of messages to fetch.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def history(notebook_id: str, limit: int, as_json: bool):
    """View chat history for a notebook."""
    try:
        client = NotebookLMClient()
        data = client.rpc(RPC_CHAT_SESSIONS, [[], None, notebook_id, limit])
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    messages = []
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, list) and len(entry) >= 2:
                role = "user" if entry[0] == 1 else "assistant"
                content = entry[1] if isinstance(entry[1], str) else str(entry[1])
                timestamp = str(entry[2]) if len(entry) > 2 else ""
                messages.append(ChatMessage(
                    role=role, content=content, timestamp=timestamp,
                ))

    session = ChatSession(notebook_id=notebook_id, messages=messages)

    if as_json:
        output_json(session.to_dict())
        return

    if not messages:
        click.echo("No chat history found.")
        return

    for msg in messages:
        prefix = "You" if msg.role == "user" else "AI"
        click.echo(f"[{prefix}] {truncate(msg.content, 200)}")
        click.echo()
