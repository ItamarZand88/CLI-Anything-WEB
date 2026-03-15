"""Source management commands."""

from __future__ import annotations

from typing import Any

import click

from cli_web.notebooklm.core.client import NotebookLMClient
from cli_web.notebooklm.core.models import Source
from cli_web.notebooklm.utils.output import output_json, output_table, output_error, truncate


SOURCE_TYPE_MAP = {
    0: "unknown",
    1: "paste",
    2: "pdf",
    3: "url",
    4: "youtube",
    5: "google_doc",
}


def _parse_source(raw: Any, notebook_id: str = "") -> Source:
    """Parse a raw source entry."""
    if not isinstance(raw, list):
        return Source(id=str(raw), notebook_id=notebook_id)

    src_id = raw[0] if len(raw) > 0 else ""
    title = raw[1] if len(raw) > 1 else ""
    src_type_num = raw[2] if len(raw) > 2 and isinstance(raw[2], int) else 0
    word_count = raw[3] if len(raw) > 3 and isinstance(raw[3], int) else 0
    created_at = str(raw[4]) if len(raw) > 4 else ""

    return Source(
        id=str(src_id),
        title=str(title),
        source_type=SOURCE_TYPE_MAP.get(src_type_num, "unknown"),
        word_count=word_count,
        created_at=created_at,
        notebook_id=notebook_id,
    )


@click.group("sources")
def sources_group():
    """Manage sources within a notebook."""
    pass


@sources_group.command("list")
@click.argument("notebook_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def list_sources(notebook_id: str, as_json: bool):
    """List all sources in a notebook."""
    try:
        client = NotebookLMClient()
        data = client.rpc("e3bVqc", [None, None, notebook_id])
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    sources = []
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, list):
                sources.append(_parse_source(entry, notebook_id))

    if as_json:
        output_json([s.to_dict() for s in sources])
        return

    if not sources:
        click.echo("No sources found.")
        return

    headers = ["ID", "Title", "Type", "Words"]
    rows = [
        [truncate(s.id, 20), truncate(s.title, 40), s.source_type, str(s.word_count)]
        for s in sources
    ]
    output_table(headers, rows)


@sources_group.command("add")
@click.argument("notebook_id")
@click.argument("text")
@click.option("--title", default="Pasted text", help="Title for the source.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def add_source(notebook_id: str, text: str, title: str, as_json: bool):
    """Add a paste text source to a notebook."""
    try:
        client = NotebookLMClient()
        data = client.rpc("bRWmue", [notebook_id, [[text, title]]])
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    if as_json:
        output_json(data)
        return

    click.echo(f"Added source '{title}' to notebook {notebook_id}")


@sources_group.command("get")
@click.argument("notebook_id")
@click.argument("source_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def get_source(notebook_id: str, source_id: str, as_json: bool):
    """Get details of a specific source."""
    try:
        client = NotebookLMClient()
        data = client.rpc("e3bVqc", [None, None, notebook_id])
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    # Find the matching source
    source = None
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, list) and len(entry) > 0 and str(entry[0]) == source_id:
                source = _parse_source(entry, notebook_id)
                break

    if source is None:
        output_error(f"Source {source_id} not found in notebook {notebook_id}")
        raise SystemExit(1)

    if as_json:
        output_json(source.to_dict())
        return

    click.echo(f"Source: {source.title}")
    click.echo(f"ID:     {source.id}")
    click.echo(f"Type:   {source.source_type}")
    click.echo(f"Words:  {source.word_count}")


@sources_group.command("delete")
@click.argument("notebook_id")
@click.argument("source_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.confirmation_option(prompt="Are you sure you want to delete this source?")
def delete_source(notebook_id: str, source_id: str, as_json: bool):
    """Delete a source from a notebook."""
    try:
        client = NotebookLMClient()
        data = client.rpc("UZ2cxc", [notebook_id, [source_id]])
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    if as_json:
        output_json({"deleted": source_id, "notebook_id": notebook_id, "result": data})
        return

    click.echo(f"Deleted source {source_id} from notebook {notebook_id}")
