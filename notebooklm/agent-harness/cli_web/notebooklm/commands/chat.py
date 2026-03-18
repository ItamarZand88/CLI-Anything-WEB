"""Chat commands: ask a question to a notebook."""
import click
from ..core.client import NotebookLMClient
from ..utils.output import print_json
from ..utils.helpers import handle_errors, require_notebook


@click.group()
def chat():
    """Chat with a notebook."""
    pass


@chat.command("ask")
@click.option("--notebook", default=None, help="Notebook ID (or use current context).")
@click.option("--query", required=True, help="Question to ask the notebook.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def ask(notebook, query, use_json):
    """Ask a question to the notebook."""
    with handle_errors(json_mode=use_json):
        nb_id = require_notebook(notebook)
        client = NotebookLMClient()
        answer = client.ask(nb_id, query)
        if use_json:
            print_json({"notebook_id": nb_id, "query": query, "answer": answer})
        else:
            print(answer)
