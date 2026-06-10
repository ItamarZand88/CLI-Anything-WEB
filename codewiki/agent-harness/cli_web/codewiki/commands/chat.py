"""Chat command — ask Gemini about a repository."""

from __future__ import annotations

import click

from ..core.client import CodeWikiClient
from ..utils.helpers import handle_errors
from ..utils.output import print_json

try:
    from rich.console import Console
    from rich.markdown import Markdown

    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False


@click.group("chat")
def chat_group():
    """Ask Gemini questions about a repository."""


@chat_group.command("ask")
@click.argument("question")
@click.option("--repo", required=True, help='Repository slug, e.g. "excalidraw/excalidraw".')
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def ask(question: str, repo: str, as_json: bool) -> None:
    """Ask Gemini about a repository."""
    with handle_errors(json_mode=as_json):
        client = CodeWikiClient()
        try:
            response = client.chat(question=question, repo_slug=repo)
        finally:
            client.close()

        if as_json:
            print_json({"success": True, "data": response.to_dict()})
        else:
            header = f"Gemini — {repo}:"
            click.echo(f"\n{header}\n")
            if _RICH_AVAILABLE:
                Console().print(Markdown(response.answer))
            else:
                click.echo(response.answer)
