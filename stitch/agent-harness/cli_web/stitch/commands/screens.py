"""Screen commands for cli-web-stitch."""
from pathlib import Path

import click

from ..core.client import StitchClient
from ..utils.helpers import handle_errors, require_project, resolve_partial_id, sanitize_filename
from ..utils.output import (
    format_screen,
    format_screens_table,
    json_success,
    print_json,
)


@click.group("screens")
def screens():
    """Manage screens in the active project."""


@screens.command("list")
@click.option("--project", "project_id", default=None, help="Project ID (uses active if omitted)")
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def screens_list(ctx, project_id, json_mode):
    """List screens in the active project."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        pid = require_project(project_id)
        client = StitchClient()
        items = client.list_screens(pid)

        if json_mode:
            print_json(json_success([
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "width": s.width,
                    "height": s.height,
                    "html_url": s.html_url,
                    "agent_name": s.agent_name,
                }
                for s in items
            ]))
        else:
            if not items:
                click.echo("No screens found.")
            else:
                format_screens_table(items)


@screens.command("get")
@click.argument("screen_id")
@click.option("--project", "project_id", default=None, help="Project ID (uses active if omitted)")
@click.option("--output", "-o", "output_file", default=None,
              help="Save HTML to file")
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def screens_get(ctx, screen_id, project_id, output_file, json_mode):
    """Get screen details and optionally download HTML."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        pid = require_project(project_id)
        client = StitchClient()
        items = client.list_screens(pid)

        screen = resolve_partial_id(screen_id, items, id_attr="id", label_attr="name", kind="screen")

        # Download HTML if requested
        html_saved = None
        if output_file and screen.html_url:
            content = client.download_screen_html(screen.html_url)
            Path(output_file).write_bytes(content)
            html_saved = output_file

        if json_mode:
            data = {
                "id": screen.id,
                "name": screen.name,
                "description": screen.description,
                "resource_name": screen.resource_name,
                "width": screen.width,
                "height": screen.height,
                "html_url": screen.html_url,
                "agent_name": screen.agent_name,
            }
            if html_saved:
                data["saved_to"] = html_saved
            print_json(json_success(data))
        else:
            format_screen(screen, json_mode=False)
            if html_saved:
                click.echo(f"\nHTML saved to: {html_saved}")


@screens.command("download")
@click.argument("screen_id")
@click.option("--project", "project_id", default=None, help="Project ID (uses active if omitted)")
@click.option("--output", "-o", "output_dir", default=".",
              help="Output directory (default: current dir)")
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def screens_download(ctx, screen_id, project_id, output_dir, json_mode):
    """Download a specific screen's HTML file."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        pid = require_project(project_id)
        client = StitchClient()
        items = client.list_screens(pid)

        screen = resolve_partial_id(screen_id, items, id_attr="id", label_attr="name", kind="screen")

        if not screen.html_url:
            raise click.UsageError(f"Screen '{screen.name}' has no HTML file to download")

        filename = sanitize_filename(screen.name) + ".html"
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename

        content = client.download_screen_html(screen.html_url)
        out_path.write_bytes(content)

        if json_mode:
            print_json(json_success({
                "id": screen.id,
                "name": screen.name,
                "file": str(out_path),
                "size": len(content),
            }))
        else:
            click.echo(f"Downloaded: {out_path} ({len(content)} bytes)")
