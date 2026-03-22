"""Design / generation commands for cli-web-stitch."""
import json

import click
from rich.console import Console

from ..core.client import StitchClient
from ..utils.helpers import handle_errors, require_project, retry_on_rate_limit
from ..utils.output import json_success, print_json

_console = Console()


@click.group("design")
def design():
    """AI design generation commands."""


@design.command("generate")
@click.argument("prompt")
@click.option("--project", "project_id", default=None, help="Project ID (uses active if omitted)")
@click.option("--model", type=click.Choice(["flash", "pro", "redesign"]), default="flash",
              help="AI model: flash (fast), pro (thinking), redesign")
@click.option("--device", type=click.Choice(["mobile", "web", "tablet", "agnostic"]), default="mobile",
              help="Device type")
@click.option("--wait/--no-wait", default=True, help="Wait for generation to complete")
@click.option("--retry", "max_retry", type=int, default=3,
              help="Max retries on rate limit")
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def design_generate(ctx, prompt, project_id, model, device, wait, max_retry, json_mode):
    """Generate or modify design with an AI prompt."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        pid = require_project(project_id)
        client = StitchClient()
        # Map device to platform for the API
        platform = device

        if wait:
            def _on_progress(session):
                if not json_mode and session:
                    screens_count = len(session.screens) if session.screens else 0
                    status_label = {1: "starting", 2: "generating", 3: "complete"}.get(session.status or 0, "...")
                    _console.print(f"  [dim]Status: {status_label}, screens: {screens_count}[/]", end="\r")

            def _do_generate():
                return client.generate_and_wait(pid, prompt, platform, model=model, on_progress=_on_progress)

            if not json_mode:
                with _console.status("Generating..."):
                    session = retry_on_rate_limit(_do_generate, max_retries=max_retry)
            else:
                session = retry_on_rate_limit(_do_generate, max_retries=max_retry)

            if json_mode:
                data = {
                    "session_id": session.id if session else None,
                    "status": session.status if session else None,
                    "prompt": prompt,
                    "explanation": session.explanation if session else "",
                    "screens": [
                        {"id": s.id, "name": s.name}
                        for s in (session.screens if session else [])
                    ],
                }
                print_json(json_success(data))
            else:
                if session and session.status is not None and session.status >= 3:
                    _console.print(f"[green]Generation complete![/]")
                    if session.explanation:
                        _console.print(f"[dim]{session.explanation}[/]")
                    _console.print(f"Screens: {len(session.screens)}")
                    for s in session.screens:
                        _console.print(f"  - {s.name or s.id}")
                elif session:
                    _console.print(f"[yellow]Generation status: {session.status}[/]")
                else:
                    _console.print("[red]Generation failed — no session returned[/]")
        else:
            def _do_send():
                return client.send_prompt(pid, prompt, platform, model=model)

            session = retry_on_rate_limit(_do_send, max_retries=max_retry)

            if json_mode:
                print_json(json_success({
                    "session_id": session.id if session else None,
                    "resource_name": session.resource_name if session else None,
                }))
            else:
                if session:
                    _console.print(f"Generation started (session: {session.id})")
                    _console.print("Use 'design history' to check progress.")
                else:
                    _console.print("[red]Failed to start generation[/]")


@design.command("theme")
@click.option("--project", "project_id", default=None, help="Project ID (uses active if omitted)")
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def design_theme(ctx, project_id, json_mode):
    """Show the design system (colors, typography) for a project."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        pid = require_project(project_id)
        client = StitchClient()
        ds = client.get_design_system(pid)

        if ds is None:
            if json_mode:
                print_json(json_success({"design_system": None, "message": "No design system found"}))
            else:
                click.echo("No design system found for this project.")
            return

        if json_mode:
            print_json(json_success(ds))
        else:
            if ds.get("name"):
                _console.print(f"[bold]{ds['name']}[/]")
            if ds.get("primary_color"):
                _console.print(f"Primary: {ds['primary_color']}")
            _console.print()

            colors = ds.get("colors", {})
            if colors:
                _console.print("[bold]Material Design 3 Tokens:[/]")
                # Group by category
                categories = {}
                for name, hex_val in sorted(colors.items()):
                    cat = name.split("_")[0] if "_" in name else name
                    categories.setdefault(cat, []).append((name, hex_val))
                for cat, tokens in sorted(categories.items()):
                    _console.print(f"\n  [dim]{cat}[/]")
                    for name, hex_val in tokens:
                        _console.print(f"    {name}: {hex_val}")

            if ds.get("description"):
                _console.print(f"\n[dim]--- Design System Description ---[/]")
                # Show first few lines
                lines = ds["description"].split("\n")[:20]
                for line in lines:
                    _console.print(f"  {line}")
                if len(ds["description"].split("\n")) > 20:
                    _console.print(f"  ... ({len(ds['description'].split(chr(10)))} lines total)")


@design.command("history")
@click.option("--project", "project_id", default=None, help="Project ID (uses active if omitted)")
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def design_history(ctx, project_id, json_mode):
    """List generation sessions (prompt history)."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        pid = require_project(project_id)
        client = StitchClient()
        sessions = client.list_sessions(pid)

        if json_mode:
            print_json(json_success([
                {
                    "id": s.id,
                    "prompt": s.prompt,
                    "status": s.status,
                    "explanation": s.explanation,
                    "screens": len(s.screens),
                    "timestamp": s.timestamp,
                }
                for s in sessions
            ]))
        else:
            if not sessions:
                click.echo("No generation history.")
            else:
                for s in sessions:
                    status_icon = {None: "?", 1: "...", 2: "done"}.get(s.status, str(s.status))
                    prompt_preview = (s.prompt[:60] + "...") if len(s.prompt) > 60 else s.prompt
                    _console.print(
                        f"  [{status_icon}] {s.id[:12]}  "
                        f"[dim]{prompt_preview}[/]  "
                        f"({len(s.screens)} screens)"
                    )
