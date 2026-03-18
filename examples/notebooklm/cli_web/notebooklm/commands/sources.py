import sys

import click

from cli_web.notebooklm.core.client import NotebookLMClient
from cli_web.notebooklm.core.models import parse_source
from cli_web.notebooklm.utils.output import output_json, output_table


@click.group()
def sources():
    """Manage NotebookLM sources."""


@sources.command("list")
@click.option("--notebook-id", required=True, help="Notebook ID.")
@click.pass_context
def list_sources(ctx, notebook_id):
    """List sources for a notebook."""
    json_mode = ctx.obj.get("json", False)
    try:
        client = NotebookLMClient()
        raw_sources = client.list_sources(notebook_id)

        parsed = [parse_source(s) for s in raw_sources]

        if json_mode:
            output_json(parsed)
        else:
            headers = ["ID", "Title", "Type", "Words"]
            rows = [
                [s["id"], s["title"], s["type"], s["word_count"]]
                for s in parsed
            ]
            output_table(headers, rows)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@sources.command("add-text")
@click.option("--notebook-id", required=True, help="Notebook ID.")
@click.option("--title", required=True, help="Title for the text source.")
@click.option("--text", required=True, help="Text content to add. Use '-' to read from stdin.")
@click.pass_context
def add_text_source(ctx, notebook_id, title, text):
    """Add a text source to a notebook."""
    json_mode = ctx.obj.get("json", False)
    if text == "-":
        text = click.get_text_stream("stdin").read()
    try:
        client = NotebookLMClient()
        result = client.add_text_source(notebook_id, title, text)
        source_id = None
        try:
            source_id = result[0][0][0]
        except (IndexError, TypeError):
            pass

        data = {"notebook_id": notebook_id, "title": title, "message": "Source added"}
        if source_id:
            data["source_id"] = source_id

        if json_mode:
            output_json(data)
        else:
            click.echo(f"Added text source: {title}")
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
