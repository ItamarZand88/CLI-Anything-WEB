"""Notebook management commands."""

from __future__ import annotations

import json
from typing import Any

import click

from cli_web.notebooklm.core.client import NotebookLMClient
from cli_web.notebooklm.core.models import Notebook
from cli_web.notebooklm.utils.config import (
    RPC_LIST_NOTEBOOKS,
    RPC_NOTEBOOK_DETAILS,
    RPC_LAST_MODIFIED,
)
from cli_web.notebooklm.utils.output import output_json, output_table, output_error, truncate


def _get_client() -> NotebookLMClient:
    return NotebookLMClient()


def _parse_notebook(raw: Any) -> Notebook:
    """Parse a raw notebook entry from the API response."""
    if not isinstance(raw, list):
        return Notebook(id=str(raw))

    nb_id = raw[0] if len(raw) > 0 else ""
    title = raw[1] if len(raw) > 1 else ""
    emoji = ""
    description = ""
    created_at = ""
    updated_at = ""
    source_count = 0

    # Emoji is typically at index 2
    if len(raw) > 2 and isinstance(raw[2], str):
        emoji = raw[2]

    # Timestamps and other fields vary by response shape
    if len(raw) > 4 and isinstance(raw[4], (int, float)):
        created_at = str(raw[4])
    if len(raw) > 5 and isinstance(raw[5], (int, float)):
        updated_at = str(raw[5])
    if len(raw) > 6 and isinstance(raw[6], (int, float)):
        source_count = int(raw[6])

    return Notebook(
        id=str(nb_id),
        title=str(title),
        emoji=str(emoji),
        description=str(description),
        created_at=str(created_at),
        updated_at=str(updated_at),
        source_count=source_count,
    )


@click.group("notebooks")
def notebooks_group():
    """Manage NotebookLM notebooks."""
    pass


@notebooks_group.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def list_notebooks(as_json: bool):
    """List all notebooks."""
    try:
        client = _get_client()
        data = client.rpc(RPC_LIST_NOTEBOOKS, [None, 1, None, [2]])
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    # data is typically a nested list of notebook entries
    notebooks = []
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, list):
                notebooks.append(_parse_notebook(entry))

    if as_json:
        output_json([nb.to_dict() for nb in notebooks])
        return

    if not notebooks:
        click.echo("No notebooks found.")
        return

    headers = ["ID", "Title", "Emoji", "Sources"]
    rows = [
        [truncate(nb.id, 20), truncate(nb.title, 40), nb.emoji, str(nb.source_count)]
        for nb in notebooks
    ]
    output_table(headers, rows)


@notebooks_group.command("get")
@click.argument("notebook_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def get_notebook(notebook_id: str, as_json: bool):
    """Get details for a specific notebook."""
    try:
        client = _get_client()
        data = client.rpc(
            RPC_NOTEBOOK_DETAILS,
            [notebook_id, None, [2], None, 0],
        )
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    nb = _parse_notebook(data) if isinstance(data, list) else Notebook(id=notebook_id)

    if as_json:
        output_json(nb.to_dict())
        return

    click.echo(f"Notebook: {nb.emoji} {nb.title}")
    click.echo(f"ID:       {nb.id}")
    click.echo(f"Sources:  {nb.source_count}")
    if nb.created_at:
        click.echo(f"Created:  {nb.created_at}")
    if nb.updated_at:
        click.echo(f"Updated:  {nb.updated_at}")


@notebooks_group.command("create")
@click.argument("title")
@click.option("--emoji", default="", help="Emoji for the notebook.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def create_notebook(title: str, emoji: str, as_json: bool):
    """Create a new notebook."""
    try:
        client = _get_client()
        # Create notebook RPC — uses a generic creation payload
        data = client.rpc("UEhJd", [None, title, emoji or None])
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    if as_json:
        output_json(data)
        return

    nb_id = data[0] if isinstance(data, list) and data else "unknown"
    click.echo(f"Created notebook '{title}' (ID: {nb_id})")


@notebooks_group.command("delete")
@click.argument("notebook_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.confirmation_option(prompt="Are you sure you want to delete this notebook?")
def delete_notebook(notebook_id: str, as_json: bool):
    """Delete a notebook."""
    try:
        client = _get_client()
        data = client.rpc("CYfMSe", [notebook_id])
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    if as_json:
        output_json({"deleted": notebook_id, "result": data})
        return

    click.echo(f"Deleted notebook {notebook_id}")


@notebooks_group.command("rename")
@click.argument("notebook_id")
@click.argument("new_title")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def rename_notebook(notebook_id: str, new_title: str, as_json: bool):
    """Rename a notebook."""
    try:
        client = _get_client()
        data = client.rpc("Bk1Jab", [notebook_id, new_title])
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    if as_json:
        output_json({"id": notebook_id, "new_title": new_title, "result": data})
        return

    click.echo(f"Renamed notebook {notebook_id} to '{new_title}'")
