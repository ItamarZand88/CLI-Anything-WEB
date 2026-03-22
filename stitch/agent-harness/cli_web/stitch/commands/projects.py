"""Project commands for cli-web-stitch."""
import json
from pathlib import Path

import click
from rich.console import Console

from ..core.client import StitchClient
from ..utils.helpers import handle_errors, sanitize_filename, set_context_value
from ..utils.output import (
    format_project,
    format_projects_table,
    json_success,
    print_json,
)

_console = Console()


@click.group("projects")
def projects():
    """Manage Stitch projects."""


@projects.command("list")
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def projects_list(ctx, json_mode):
    """List all projects."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        client = StitchClient()
        items = client.list_projects()
        if json_mode:
            print_json(json_success([
                {
                    "id": p.id,
                    "resource_name": p.resource_name,
                    "title": p.title,
                    "created_at": p.created_at,
                    "modified_at": p.modified_at,
                    "status": p.status,
                }
                for p in items
            ]))
        else:
            if not items:
                click.echo("No projects found.")
            else:
                format_projects_table(items)


@projects.command("get")
@click.argument("project_id")
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def projects_get(ctx, project_id, json_mode):
    """Get project details."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        client = StitchClient()
        project = client.get_project(project_id)
        if project is None:
            raise click.UsageError(f"Project not found: {project_id}")
        format_project(project, json_mode=json_mode)


@projects.command("create")
@click.argument("prompt")
@click.option("--platform", type=click.Choice(["app", "web"]), default="app",
              help="Platform: app (mobile) or web")
@click.option("--wait/--no-wait", default=True, help="Wait for generation to complete")
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def projects_create(ctx, prompt, platform, wait, json_mode):
    """Create a new project and generate design from prompt."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        client = StitchClient()

        if not json_mode:
            _console.print("[dim]Creating project and generating design...[/]")

        if wait:
            if not json_mode:
                with _console.status("Generating design..."):
                    project = client.create_project_and_generate(
                        prompt, platform,
                    )
            else:
                project = client.create_project_and_generate(prompt, platform)

            if project is None:
                raise click.UsageError("Failed to create project")

            set_context_value("project_id", project.id)
            if json_mode:
                print_json(json_success({
                    "project": {
                        "id": project.id,
                        "resource_name": project.resource_name,
                        "title": project.title,
                    },
                    "prompt": prompt,
                }))
            else:
                title = project.title or "(untitled)"
                url = f"https://stitch.withgoogle.com/projects/{project.id}"
                _console.print(f"\n[green bold]{title}[/] created!")
                _console.print(f"  [link={url}]{url}[/link]")
                _console.print(f"  [dim]Active project set.[/]")
        else:
            # No-wait: create project and fire prompt without polling
            project = client.create_project()
            if project is None:
                raise click.UsageError("Failed to create project")
            session = client.send_prompt(project.id, prompt, platform)
            set_context_value("project_id", project.id)
            if json_mode:
                print_json(json_success({
                    "project": {"id": project.id, "resource_name": project.resource_name},
                    "session": {"id": session.id if session else None},
                }))
            else:
                format_project(project, json_mode=False)
                _console.print(f"\nProject created: {project.id}")
                _console.print(f"Active project set to: {project.id}")
                _console.print("Use 'design history' to check progress.")


@projects.command("delete")
@click.argument("project_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def projects_delete(ctx, project_id, yes, json_mode):
    """Delete a project."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        if not yes and not json_mode:
            click.confirm(f"Delete project {project_id}? This cannot be undone", abort=True)
        client = StitchClient()
        client.delete_project(project_id)
        if json_mode:
            print_json(json_success({"deleted": project_id}))
        else:
            click.echo(f"Deleted project: {project_id}")


@projects.command("rename")
@click.argument("project_id")
@click.argument("new_name")
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def projects_rename(ctx, project_id, new_name, json_mode):
    """Rename a project."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        client = StitchClient()
        project = client.rename_project(project_id, new_name)
        if project is None:
            raise click.UsageError(f"Failed to rename project: {project_id}")
        if json_mode:
            print_json(json_success({
                "id": project.id,
                "title": project.title,
                "resource_name": project.resource_name,
            }))
        else:
            click.echo(f"Renamed project {project.id} to: {project.title}")


@projects.command("duplicate")
@click.argument("project_id")
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def projects_duplicate(ctx, project_id, json_mode):
    """Duplicate/clone a project."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        client = StitchClient()
        new_id = client.duplicate_project(project_id)
        if new_id is None:
            raise click.UsageError(f"Failed to duplicate project: {project_id}")
        if json_mode:
            print_json(json_success({
                "source_id": project_id,
                "new_id": new_id,
                "new_resource_name": f"projects/{new_id}",
            }))
        else:
            click.echo(f"Duplicated project {project_id} → {new_id}")


@projects.command("download")
@click.argument("project_id")
@click.option("--output", "-o", "output_dir", default=".",
              help="Output directory for files")
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def projects_download(ctx, project_id, output_dir, json_mode):
    """Download project files (screen HTMLs + export)."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        client = StitchClient()
        screens = client.list_screens(project_id)

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        downloaded = []
        for screen in screens:
            if not screen.html_url:
                continue
            filename = sanitize_filename(screen.name or screen.id) + ".html"
            filepath = out_path / filename

            if not json_mode:
                _console.print(f"[dim]Downloading {filename}...[/]")

            content = client.download_screen_html(screen.html_url)
            filepath.write_bytes(content)
            downloaded.append({"screen_id": screen.id, "name": screen.name, "file": str(filepath)})

        # Trigger ZIP export
        try:
            client.export_project(project_id)
            export_triggered = True
        except Exception:
            export_triggered = False

        if json_mode:
            print_json(json_success({
                "project_id": project_id,
                "files": downloaded,
                "export_triggered": export_triggered,
            }))
        else:
            click.echo(f"Downloaded {len(downloaded)} screen(s) to {out_path}")
            if export_triggered:
                click.echo("ZIP export triggered (check Stitch UI for download link).")
