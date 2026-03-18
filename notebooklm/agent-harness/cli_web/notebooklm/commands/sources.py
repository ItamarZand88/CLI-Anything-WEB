"""Source commands: list, add-url, add-text, get, delete."""
import click
from ..core.client import NotebookLMClient
from ..utils.output import (
    print_sources_table, print_source, print_json,
    source_to_dict,
)
from ..utils.helpers import handle_errors, require_notebook, resolve_partial_id


@click.group()
def sources():
    """Manage sources within a notebook."""
    pass


@sources.command("list")
@click.option("--notebook", default=None, help="Notebook ID (or use current context).")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def list_sources(notebook, use_json):
    """List all sources in a notebook."""
    with handle_errors(json_mode=use_json):
        nb_id = require_notebook(notebook)
        client = NotebookLMClient()
        srcs = client.list_sources(nb_id)
        if use_json:
            print_json([source_to_dict(s) for s in srcs])
        else:
            print_sources_table(srcs)


@sources.command("add-url")
@click.option("--notebook", default=None, help="Notebook ID (or use current context).")
@click.option("--url", required=True, help="URL to add as a source.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def add_url(notebook, url, use_json):
    """Add a URL source to a notebook."""
    with handle_errors(json_mode=use_json):
        nb_id = require_notebook(notebook)
        client = NotebookLMClient()
        src = client.add_source_url(nb_id, url)
        if use_json:
            print_json(source_to_dict(src))
        else:
            print_source(src)


@sources.command("add-text")
@click.option("--notebook", default=None, help="Notebook ID (or use current context).")
@click.option("--title", required=True, help="Title of the text source.")
@click.option("--text", required=True, help="Text content to add as a source.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def add_text(notebook, title, text, use_json):
    """Add a text source to a notebook."""
    with handle_errors(json_mode=use_json):
        nb_id = require_notebook(notebook)
        client = NotebookLMClient()
        src = client.add_source_text(nb_id, title, text)
        if use_json:
            print_json(source_to_dict(src))
        else:
            print_source(src)


@sources.command("get")
@click.option("--notebook", default=None, help="Notebook ID (or use current context).")
@click.argument("source_id")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def get_source(notebook, source_id, use_json):
    """Get details of a specific source (supports partial ID)."""
    with handle_errors(json_mode=use_json):
        nb_id = require_notebook(notebook)
        client = NotebookLMClient()
        srcs = client.list_sources(nb_id)
        matched = resolve_partial_id(source_id, srcs, label_attr="name", kind="source")
        src = client.get_source(nb_id, matched.id)
        if use_json:
            print_json(source_to_dict(src))
        else:
            print_source(src)


@sources.command("delete")
@click.option("--notebook", default=None, help="Notebook ID (or use current context).")
@click.argument("source_id")
@click.option("--confirm", is_flag=True, default=False, help="Confirm deletion.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def delete_source(notebook, source_id, confirm, use_json):
    """Delete a source from a notebook (supports partial ID)."""
    if not confirm:
        click.echo("Use --confirm to actually delete")
        return
    with handle_errors(json_mode=use_json):
        nb_id = require_notebook(notebook)
        client = NotebookLMClient()
        srcs = client.list_sources(nb_id)
        matched = resolve_partial_id(source_id, srcs, label_attr="name", kind="source")
        client.delete_source(nb_id, matched.id)
        if use_json:
            print_json({"deleted": matched.id})
        else:
            click.echo(f"Deleted source {matched.id}")
