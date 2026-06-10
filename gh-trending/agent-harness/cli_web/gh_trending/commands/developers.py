"""Trending developers command group."""

from __future__ import annotations

import click
from cli_web.gh_trending.core.client import GitHubClient
from cli_web.gh_trending.utils.helpers import handle_errors, resolve_json_mode
from cli_web.gh_trending.utils.output import print_developers_table, print_json_success


@click.group("developers")
def developers_group():
    """Trending GitHub developers."""


@developers_group.command("list")
@click.option(
    "--language", "-l", default="", help="Filter by programming language (e.g. python, javascript)."
)
@click.option(
    "--since",
    "-s",
    default="daily",
    type=click.Choice(["daily", "weekly", "monthly"], case_sensitive=False),
    show_default=True,
    help="Time range for trending.",
)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def developers_list(ctx, language, since, json_mode):
    """List trending GitHub developers."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = GitHubClient()
        developers = client.get_trending_developers(language=language, since=since)
        if json_mode:
            print_json_success([d.to_dict() for d in developers])
        else:
            label_parts = []
            if language:
                label_parts.append(language.capitalize())
            label_parts.append("Trending Developers")
            if since != "daily":
                label_parts.append(f"({since})")
            click.echo(f"\n{'  '.join(label_parts)}\n")
            print_developers_table(developers)
            click.echo(f"\n{len(developers)} developers\n")
