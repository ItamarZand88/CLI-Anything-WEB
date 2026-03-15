"""Note management commands."""

from __future__ import annotations

from typing import Any

import click

from cli_web.notebooklm.core.client import NotebookLMClient
from cli_web.notebooklm.core.models import Note
from cli_web.notebooklm.utils.config import RPC_NOTEBOOK_NOTES
from cli_web.notebooklm.utils.output import output_json, output_table, output_error, truncate


def _parse_note(raw: Any, notebook_id: str = "") -> Note:
    """Parse a raw note entry."""
    if not isinstance(raw, list):
        return Note(id=str(raw), notebook_id=notebook_id)

    note_id = raw[0] if len(raw) > 0 else ""
    content = raw[1] if len(raw) > 1 and isinstance(raw[1], str) else ""
    title = raw[2] if len(raw) > 2 and isinstance(raw[2], str) else ""
    created_at = str(raw[3]) if len(raw) > 3 else ""

    return Note(
        id=str(note_id),
        content=content,
        title=title,
        created_at=created_at,
        notebook_id=notebook_id,
    )


@click.group("notes")
def notes_group():
    """Manage notes within a notebook."""
    pass


@notes_group.command("list")
@click.argument("notebook_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def list_notes(notebook_id: str, as_json: bool):
    """List all notes in a notebook."""
    try:
        client = NotebookLMClient()
        data = client.rpc(RPC_NOTEBOOK_NOTES, [None, None, notebook_id])
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    notes = []
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, list):
                notes.append(_parse_note(entry, notebook_id))

    if as_json:
        output_json([n.to_dict() for n in notes])
        return

    if not notes:
        click.echo("No notes found.")
        return

    headers = ["ID", "Title", "Content Preview"]
    rows = [
        [truncate(n.id, 20), truncate(n.title or "(untitled)", 30), truncate(n.content, 50)]
        for n in notes
    ]
    output_table(headers, rows)


@notes_group.command("create")
@click.argument("notebook_id")
@click.argument("content")
@click.option("--title", default="", help="Title for the note.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def create_note(notebook_id: str, content: str, title: str, as_json: bool):
    """Create a new note in a notebook."""
    try:
        client = NotebookLMClient()
        data = client.rpc("WFHnsc", [notebook_id, content, title or None])
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    if as_json:
        output_json(data)
        return

    note_id = data[0] if isinstance(data, list) and data else "unknown"
    click.echo(f"Created note (ID: {note_id}) in notebook {notebook_id}")


@notes_group.command("delete")
@click.argument("notebook_id")
@click.argument("note_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.confirmation_option(prompt="Are you sure you want to delete this note?")
def delete_note(notebook_id: str, note_id: str, as_json: bool):
    """Delete a note from a notebook."""
    try:
        client = NotebookLMClient()
        data = client.rpc("Kxsloe", [notebook_id, note_id])
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    if as_json:
        output_json({"deleted": note_id, "notebook_id": notebook_id, "result": data})
        return

    click.echo(f"Deleted note {note_id} from notebook {notebook_id}")
