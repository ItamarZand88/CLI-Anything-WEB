"""Manage projects/workspaces on Suno."""

import click
from cli_web.suno.core.client import SunoClient
from cli_web.suno.core.models import Project
from cli_web.suno.utils.output import output_result, output_json


@click.group()
def projects():
    """Manage projects/workspaces."""
    pass


@projects.command("list")
@click.option("--page", default=1, help="Page number.", show_default=True)
@click.pass_context
def list_projects(ctx, page):
    """List projects."""
    as_json = ctx.obj.get("json", False)
    client = SunoClient()
    try:
        result = client.list_projects(page)
        raw_projects = result if isinstance(result, list) else result.get("projects", [])
        parsed = [Project.from_dict(p) for p in raw_projects]
        rows = [{"id": p.id, "name": p.name, "clip_count": p.clip_count} for p in parsed]
        output_result(rows, as_json=as_json, columns=["id", "name", "clip_count"])
    finally:
        client.close()


@projects.command("get")
@click.option("--id", "project_id", default="default", help="Project ID.", show_default=True)
@click.pass_context
def get_project(ctx, project_id):
    """Get project with clips."""
    as_json = ctx.obj.get("json", False)
    client = SunoClient()
    try:
        result = client.get_project(project_id)
        output_result(result, as_json=as_json)
    finally:
        client.close()
