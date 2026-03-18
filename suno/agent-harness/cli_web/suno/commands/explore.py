"""Discover trending content on Suno."""

import click
from cli_web.suno.core.client import SunoClient
from cli_web.suno.utils.output import output_result, output_json


@click.group()
def explore():
    """Discover trending content."""
    pass


@explore.command()
@click.option("--cursor", default=None, help="Pagination cursor for next page.")
@click.pass_context
def feed(ctx, cursor):
    """Get homepage/trending feed."""
    as_json = ctx.obj.get("json", False)
    client = SunoClient()
    try:
        result = client.get_homepage(cursor)
        output_result(result, as_json=as_json)
    finally:
        client.close()


@explore.command()
@click.option("--tags", default=None, help="Comma-separated tags to seed recommendations.")
@click.pass_context
def tags(ctx, tags):
    """Get recommended tags."""
    as_json = ctx.obj.get("json", False)
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    client = SunoClient()
    try:
        result = client.recommend_tags(tag_list)
        output_result(result, as_json=as_json)
    finally:
        client.close()
