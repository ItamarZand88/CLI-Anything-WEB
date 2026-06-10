"""Search commands for cli-web-gai."""

import click

from ..core.client import GAIClient
from ..utils.helpers import handle_errors, print_json
from ..utils.output import print_search_result

_client: GAIClient | None = None


def _get_client(headless: bool = True, lang: str = "en") -> GAIClient:
    """Get or create a persistent client for conversation threading."""
    global _client

    if not _client:
        _client = GAIClient(headless=headless, lang=lang)
    return _client


def close_client():
    """Close the persistent client."""
    global _client

    if _client:
        _client.close()
        _client = None


@click.group("search", invoke_without_command=True)
@click.pass_context
def search_group(ctx):
    """Search Google AI Mode."""

    if not ctx.invoked_subcommand:
        click.echo(ctx.get_help())


@search_group.command("ask")
@click.argument("query", nargs=-1, required=True)
@click.option("--lang", default="en", help="Response language (e.g., en, he, de).")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
@click.option("--headed", is_flag=True, help="Show browser window (for debugging).")
@click.option("--timeout", type=int, default=30, help="Response timeout in seconds.")
def ask(query, lang, use_json, headed, timeout):
    """Submit a query to Google AI Mode.

    Example: cli-web-gai search ask "What is quantum computing?"
    """
    query_str = " ".join(query)
    with handle_errors(json_mode=use_json):
        client = _get_client(headless=not headed, lang=lang)
        client._timeout = timeout * 1000
        result = client.search(query_str)
        if use_json:
            print_json(result.to_dict())
        else:
            print_search_result(result)


@search_group.command("followup")
@click.argument("query", nargs=-1, required=True)
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def followup(query, use_json):
    """Ask a follow-up question in the current conversation.

    Requires a previous 'ask' command in this session.

    Example: cli-web-gai search followup "Tell me more about that"
    """
    query_str = " ".join(query)
    with handle_errors(json_mode=use_json):
        client = _get_client()
        result = client.followup(query_str)
        if use_json:
            print_json(result.to_dict())
        else:
            print_search_result(result)
