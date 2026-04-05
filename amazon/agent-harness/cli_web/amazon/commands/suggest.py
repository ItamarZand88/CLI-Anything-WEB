"""Autocomplete suggestion commands for cli-web-amazon."""
import click
from ..core.client import AmazonClient
from ..utils.helpers import handle_errors, print_json
from ..utils.output import print_suggestions


@click.command("suggest")
@click.argument("query")
@click.option("--limit", type=int, default=11, show_default=True,
              help="Maximum number of suggestions to return.")
@click.option("--json", "use_json", is_flag=True, default=False,
              help="Output as JSON.")
def suggest(query, limit, use_json):
    """Get autocomplete suggestions for a search query.

    Example: cli-web-amazon suggest laptop
    """
    with handle_errors(json_mode=use_json):
        with AmazonClient() as client:
            results = client.get_suggestions(query, limit=limit)

        if use_json:
            print_json([s.to_dict() for s in results])
        else:
            if not results:
                click.echo(f"No suggestions for '{query}'.")
            else:
                click.echo(f"Suggestions for '{query}':")
                print_suggestions(results)
