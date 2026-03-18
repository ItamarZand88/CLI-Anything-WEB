"""Notebook commands: list, create, get, rename, delete."""
import click
from ..core.client import NotebookLMClient
from ..utils.output import (
    print_notebooks_table, print_notebook, print_json,
    notebook_to_dict,
)
from ..utils.helpers import handle_errors, resolve_partial_id


@click.group()
def notebooks():
    """Manage NotebookLM notebooks."""
    pass


@notebooks.command("list")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def list_notebooks(as_json):
    """List all notebooks."""
    with handle_errors(json_mode=as_json):
        client = NotebookLMClient()
        nbs = client.list_notebooks()
        if as_json:
            print_json([notebook_to_dict(nb) for nb in nbs])
        else:
            print_notebooks_table(nbs)


@notebooks.command("create")
@click.option("--title", required=True, help="Title of the new notebook.")
@click.option("--emoji", default=None, help="Emoji for the notebook.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def create_notebook(title, emoji, as_json):
    """Create a new notebook."""
    with handle_errors(json_mode=as_json):
        client = NotebookLMClient()
        nb = client.create_notebook(title=title, emoji=emoji)
        if as_json:
            print_json(notebook_to_dict(nb))
        else:
            print_notebook(nb)


@notebooks.command("get")
@click.argument("notebook_id")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def get_notebook(notebook_id, as_json):
    """Get details of a notebook (supports partial ID)."""
    with handle_errors(json_mode=as_json):
        client = NotebookLMClient()
        nbs = client.list_notebooks()
        matched = resolve_partial_id(notebook_id, nbs, kind="notebook")
        nb = client.get_notebook(matched.id)
        if as_json:
            print_json(notebook_to_dict(nb))
        else:
            print_notebook(nb)


@notebooks.command("rename")
@click.argument("notebook_id")
@click.option("--title", required=True, help="New title for the notebook.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def rename_notebook(notebook_id, title, as_json):
    """Rename a notebook (supports partial ID)."""
    with handle_errors(json_mode=as_json):
        client = NotebookLMClient()
        nbs = client.list_notebooks()
        matched = resolve_partial_id(notebook_id, nbs, kind="notebook")
        nb = client.rename_notebook(matched.id, title=title)
        if as_json:
            print_json(notebook_to_dict(nb))
        else:
            print_notebook(nb)


@notebooks.command("delete")
@click.argument("notebook_id")
@click.option("--confirm", is_flag=True, default=False, help="Confirm deletion.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def delete_notebook(notebook_id, confirm, as_json):
    """Delete a notebook (supports partial ID)."""
    if not confirm:
        click.echo(
            f"Warning: deletion requires --confirm flag. "
            f"Re-run with --confirm to delete notebook '{notebook_id}'."
        )
        return
    with handle_errors(json_mode=as_json):
        client = NotebookLMClient()
        nbs = client.list_notebooks()
        matched = resolve_partial_id(notebook_id, nbs, kind="notebook")
        client.delete_notebook(matched.id)
        if as_json:
            print_json({"deleted": matched.id})
        else:
            click.echo(f"Deleted notebook {matched.id}")
