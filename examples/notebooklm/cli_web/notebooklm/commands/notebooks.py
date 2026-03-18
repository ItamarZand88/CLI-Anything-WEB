import sys

import click

from cli_web.notebooklm.core.client import NotebookLMClient
from cli_web.notebooklm.core.models import parse_notebook
from cli_web.notebooklm.utils.output import output_json, output_table


@click.group()
def notebooks():
    """Manage NotebookLM notebooks."""


@notebooks.command("list")
@click.option("--shared", is_flag=True, default=False, help="List shared notebooks instead of owned.")
@click.pass_context
def list_notebooks(ctx, shared):
    """List all notebooks."""
    json_mode = ctx.obj.get("json", False)
    try:
        client = NotebookLMClient()
        if shared:
            raw_notebooks = client.list_shared_notebooks()
        else:
            raw_notebooks = client.list_notebooks()

        parsed = [parse_notebook(nb) for nb in raw_notebooks]

        if json_mode:
            output_json(parsed)
        else:
            headers = ["ID", "Emoji", "Title", "Sources", "Modified"]
            rows = [
                [n["id"], n["emoji"], n["title"], n["source_count"], n["last_modified"]]
                for n in parsed
            ]
            output_table(headers, rows)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@notebooks.command("get")
@click.option("--id", "notebook_id", required=True, help="Notebook ID.")
@click.pass_context
def get_notebook(ctx, notebook_id):
    """Get notebook details."""
    json_mode = ctx.obj.get("json", False)
    try:
        client = NotebookLMClient()
        raw = client.get_notebook(notebook_id)
        parsed = parse_notebook(raw)

        if json_mode:
            output_json(parsed)
        else:
            headers = list(parsed.keys())
            rows = [list(parsed.values())]
            output_table(headers, rows)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@notebooks.command("create")
@click.option("--title", default=None, help="Notebook title (currently unused, notebook created as Untitled).")
@click.pass_context
def create_notebook(ctx, title):
    """Create a new notebook."""
    json_mode = ctx.obj.get("json", False)
    try:
        client = NotebookLMClient()
        result = client.create_notebook()
        notebook_id = result[2]

        if json_mode:
            output_json({"id": notebook_id, "message": "Notebook created"})
        else:
            click.echo(f"Created notebook: {notebook_id}")
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@notebooks.command("delete")
@click.option("--id", "notebook_id", required=True, help="Notebook ID to delete.")
@click.pass_context
def delete_notebook(ctx, notebook_id):
    """Delete a notebook."""
    json_mode = ctx.obj.get("json", False)
    try:
        client = NotebookLMClient()
        client.delete_notebook(notebook_id)

        if json_mode:
            output_json({"id": notebook_id, "message": "Notebook deleted"})
        else:
            click.echo(f"Deleted notebook: {notebook_id}")
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
