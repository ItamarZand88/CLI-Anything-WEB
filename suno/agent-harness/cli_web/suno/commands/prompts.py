"""Manage saved prompts on Suno."""

import click
from cli_web.suno.core.client import SunoClient
from cli_web.suno.utils.output import output_result, output_json


@click.group()
def prompts():
    """Manage saved prompts."""
    pass


@prompts.command("list")
@click.option("--type", "prompt_type", default=None, help="Filter by type (lyrics/tags).")
@click.option("--page", default=0, help="Page number.", show_default=True)
@click.pass_context
def list_prompts(ctx, prompt_type, page):
    """List saved prompts."""
    as_json = ctx.obj.get("json", False)
    client = SunoClient()
    try:
        result = client.list_prompts(prompt_type, page)
        output_result(result, as_json=as_json)
    finally:
        client.close()


@prompts.command()
@click.pass_context
def suggestions(ctx):
    """Get prompt suggestions."""
    as_json = ctx.obj.get("json", False)
    client = SunoClient()
    try:
        result = client.get_prompt_suggestions()
        output_result(result, as_json=as_json)
    finally:
        client.close()
