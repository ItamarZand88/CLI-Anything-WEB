"""Google AI Mode CLI \u2014 search with AI-powered answers and references."""

import sys

try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

import atexit
import shlex

import click

from .commands.search import close_client, search_group
from .utils.repl_skin import ReplSkin

_skin = ReplSkin(app="gai", version="0.1.0")


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.version_option(package_name="cli-web-gai")
@click.pass_context
def cli(ctx, json_mode):
    """Google AI Mode CLI \u2014 AI-powered search with source references.

    Submit questions and get AI-generated answers with links to sources.

    \b
    Quick search:
      cli-web-gai search ask "What is quantum computing?"

    Follow-up:
      cli-web-gai search followup "How is it used in cryptography?"

    Interactive mode:
      cli-web-gai
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode

    if not ctx.invoked_subcommand:
        _run_repl(ctx)


cli.add_command(search_group)


def _print_repl_help():
    """Print REPL help text."""
    _skin.info("Available commands:")
    print("  search ask <query>         Submit a query to AI Mode")
    print("    --lang <en|he|de|...>    Response language (default: en)")
    print("    --headed                 Show browser window")
    print("    --timeout N              Timeout in seconds (default: 30)")
    print("  search followup <query>    Follow-up question in current thread")
    print()
    print("  Shortcuts (REPL only):")
    print("    ask <query>              Same as 'search ask <query>'")
    print("    followup <query>         Same as 'search followup <query>'")
    print()
    print("  help                       Show this help")
    print("  exit / quit                Exit the REPL")


def _run_repl(ctx):
    """Run the interactive REPL loop."""
    _skin.print_banner()
    _print_repl_help()
    print()

    atexit.register(close_client)
    json_mode = ctx.obj.get("json", False)

    while True:
        try:
            line = input(_skin.prompt())

            line = line.strip()
            if not line:
                continue

            if line.lower() in ("exit", "quit", "q"):
                _skin.info("Goodbye!")
                return

            if line.lower() in ("help", "h", "?"):
                _print_repl_help()
                continue

            # Parse arguments
            try:
                args = shlex.split(line)
            except ValueError:
                args = line.split()

            # REPL shortcuts
            if args[0].lower() == "ask":
                args = ["search", "ask"] + args[1:]
            elif args[0].lower() == "followup":
                args = ["search", "followup"] + args[1:]
            elif args[0].lower() not in ("search",):
                # Bare query — treat as search ask
                args = ["search", "ask"] + args

            # Inject --json if global json mode is on
            if json_mode:
                if len(args) >= 2:
                    args.insert(2, "--json")

            try:
                cli.main(args=args, standalone_mode=False)
            except SystemExit:
                continue
            except click.exceptions.UsageError as e:
                click.secho(f"Usage error: {e}", fg="yellow", err=True)
            except Exception as e:
                click.secho(f"Error: {e}", fg="red", err=True)

        except (EOFError, KeyboardInterrupt):
            print()
            _skin.info("Goodbye!")
            return


def main():
    """Entry point for the CLI."""
    try:
        cli()
    finally:
        close_client()


# MCP server mode — exposes every command as an MCP tool over stdio.
# Canonical adapter: cli-web-core/cli_web_core/mcp_server.py (vendored copy).
from cli_web.gai import __version__ as _pkg_version  # noqa: E402
from cli_web.gai.utils.mcp_server import register_mcp_command  # noqa: E402

register_mcp_command(cli, app_name="gai", version=_pkg_version)


if __name__ == "__main__":
    main()
