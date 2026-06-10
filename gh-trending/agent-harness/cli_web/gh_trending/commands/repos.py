"""Trending repositories command group."""

from __future__ import annotations

import click
from cli_web.gh_trending.core.client import GitHubClient
from cli_web.gh_trending.utils.helpers import handle_errors, resolve_json_mode
from cli_web.gh_trending.utils.output import print_json_success, print_repos_table


@click.group("repos")
def repos_group():
    """Trending GitHub repositories."""


@repos_group.command("list")
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
@click.option(
    "--spoken-language",
    "-L",
    default="",
    help="Filter by spoken language (ISO 639-1 code, e.g. zh, en).",
)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def repos_list(ctx, language, since, spoken_language, json_mode):
    """List trending GitHub repositories."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = GitHubClient()
        repos = client.get_trending_repos(
            language=language,
            since=since,
            spoken_language_code=spoken_language,
        )
        if json_mode:
            print_json_success([r.to_dict() for r in repos])
        else:
            label_parts = []
            if language:
                label_parts.append(language.capitalize())
            label_parts.append("Trending Repos")
            if since != "daily":
                label_parts.append(f"({since})")
            click.echo(f"\n{'  '.join(label_parts)}\n")
            print_repos_table(repos)
            click.echo(f"\n{len(repos)} repositories\n")
