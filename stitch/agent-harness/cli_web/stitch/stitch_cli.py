"""cli-web-stitch — CLI entry point and REPL for Google Stitch AI design tool."""
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

import json
import shlex

import click

from .commands.auth_cmd import auth
from .commands.projects import projects
from .commands.screens import screens
from .commands.design import design
from .utils.helpers import set_context_value, get_context_value, handle_errors


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def cli(ctx, json_mode):
    """cli-web-stitch -- CLI for Google Stitch AI design tool."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode
    if ctx.invoked_subcommand is None:
        _repl(ctx)


cli.add_command(auth)
cli.add_command(projects)
cli.add_command(screens)
cli.add_command(design)


@cli.command("use")
@click.argument("project_id")
@click.option("--json", "use_json", is_flag=True)
def use_project(project_id, use_json):
    """Set active project context."""
    with handle_errors(json_mode=use_json):
        set_context_value("project_id", project_id)
        if use_json:
            print(json.dumps({"success": True, "project_id": project_id}))
        else:
            print(f"Active project set to: {project_id}")


@cli.command("status")
@click.option("--json", "use_json", is_flag=True)
def show_status(use_json):
    """Show current context."""
    with handle_errors(json_mode=use_json):
        project_id = get_context_value("project_id")
        if use_json:
            print(json.dumps({"success": True, "project_id": project_id}))
        else:
            if project_id:
                print(f"Active project: {project_id}")
            else:
                print("No active project. Use: cli-web-stitch use <project-id>")


# ── REPL ──────────────────────────────────────────────────────────────

def _repl(ctx):
    from .utils.repl_skin import ReplSkin

    skin = ReplSkin("stitch", version="0.1.0")
    skin.print_banner()

    json_mode = ctx.obj.get("json", False)

    while True:
        try:
            line = input(skin.prompt()).strip()
            if not line:
                continue

            try:
                parts = shlex.split(line)
            except ValueError as exc:
                print(f"Parse error: {exc}")
                continue

            cmd = parts[0].lower()

            if cmd in ("quit", "exit", "q"):
                skin.print_goodbye()
                break
            if cmd == "help":
                _print_repl_help()
                continue

            repl_args = ["--json"] + parts if json_mode else parts
            try:
                cli.main(args=repl_args, standalone_mode=False)
            except SystemExit:
                pass
            except click.exceptions.UsageError as exc:
                print(f"Error: {exc}")
        except (KeyboardInterrupt, EOFError):
            print()
            skin.print_goodbye()
            break


def _print_repl_help():
    print("Available commands:")
    print("  auth login                    Login via browser")
    print("  auth status                   Check auth status")
    print("  auth import <file>            Import cookies from file")
    print("  use <project-id>              Set active project")
    print("  status                        Show current context")
    print("  projects list                 List all projects")
    print("  projects get <id>             Get project details")
    print("  projects create <prompt>      Create new project")
    print("    --platform app|web          Platform (default: app)")
    print("    --wait / --no-wait          Wait for generation")
    print("  projects rename <id> <name>   Rename a project")
    print("  projects duplicate <id>       Duplicate/clone a project")
    print("  projects delete <id> [-y]     Delete project")
    print("  projects download <id>        Download all project files")
    print("    --output DIR                Output directory")
    print("  screens list                  List screens in project")
    print("  screens get <id>              Get screen details")
    print("    --output FILE               Save HTML to file")
    print("  screens download <id>         Download a screen's HTML")
    print("    --output DIR                Output directory")
    print("  design generate <prompt>      Generate/modify design")
    print("    --model flash|pro|redesign  AI model (default: flash)")
    print("    --device mobile|web|tablet|agnostic  Device type (default: mobile)")
    print("    --wait / --no-wait          Wait for completion")
    print("    --retry N                   Max retries (default: 3)")
    print("  design theme                  Show design system (colors)")
    print("  design history                Generation history")
    print("  help                          Show this help")
    print("  quit                          Exit REPL")
