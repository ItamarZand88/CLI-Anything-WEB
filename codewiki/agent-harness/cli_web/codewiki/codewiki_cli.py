"""cli-web-codewiki — CLI for Google Code Wiki.

Browse Gemini-generated documentation for open source repositories,
search for repos, explore wiki sections, and chat with Gemini.
"""

from __future__ import annotations

import shlex
import sys

# Windows UTF-8 fix — must be before any output
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

import click

from .commands.chat import chat_group
from .commands.repos import repos
from .commands.wiki import wiki_group
from .utils.repl_skin import ReplSkin

_skin = ReplSkin("codewiki", version="0.1.0")


@click.group(invoke_without_command=True)
@click.version_option("0.1.0", prog_name="cli-web-codewiki")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    hidden=True,
    help="Output as JSON (pass to subcommands).",
)
@click.pass_context
def cli(ctx: click.Context, as_json: bool) -> None:
    """cli-web-codewiki — Browse AI-generated code documentation."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = as_json
    if ctx.invoked_subcommand is None:
        _run_repl(ctx)


cli.add_command(repos)
cli.add_command(wiki_group, "wiki")
cli.add_command(chat_group, "chat")


def _print_repl_help() -> None:
    """Print REPL help matching actual command surface."""
    _skin.info("Available commands:")
    print()
    print("  repos featured                      List featured repositories")
    print("  repos search <query>                Search repos by name")
    print("    --limit N                           Max results (default 25)")
    print("    --offset N                          Pagination offset")
    print()
    print("  wiki get <org/repo>                 Get full wiki content")
    print("  wiki sections <org/repo>            List wiki sections (TOC)")
    print("  wiki section <org/repo> <title>     Get a specific section")
    print("  wiki download <org/repo>            Download wiki as .md files")
    print("    -o <dir>                            Output directory")
    print()
    print("  chat ask <question> --repo <org/repo>")
    print("                                      Ask Gemini about a repo")
    print()
    print("  All commands support --json for structured output.")
    print()
    print("  help / ?                            Show this help")
    print("  quit / exit / q                     Exit REPL")
    print()


def _run_repl(ctx: click.Context) -> None:
    """Enter interactive REPL mode."""
    _skin.print_banner()
    _skin.info("Type 'help' for available commands, 'quit' to exit.")
    print()

    pt_session = _skin.create_prompt_session()

    while True:
        try:
            line = _skin.get_input(pt_session)
        except (EOFError, KeyboardInterrupt):
            _skin.print_goodbye()
            sys.exit(0)

        if not line:
            continue
        if line in ("quit", "exit", "q"):
            _skin.print_goodbye()
            sys.exit(0)
        if line in ("help", "?"):
            _print_repl_help()
            continue

        try:
            args = shlex.split(line)
        except ValueError as exc:
            _skin.error(f"Parse error: {exc}")
            continue

        # Propagate --json if set at top level
        repl_args = ["--json"] + args if ctx.obj.get("json") else args

        try:
            cli.main(args=repl_args, standalone_mode=False, prog_name="cli-web-codewiki")
        except SystemExit:
            pass
        except click.UsageError as exc:
            _skin.error(str(exc))
        except Exception as exc:
            _skin.error(str(exc))


def main() -> None:
    """Entry point for console_scripts."""
    cli()


# MCP server mode — exposes every command as an MCP tool over stdio.
# Canonical adapter: cli-web-core/cli_web_core/mcp_server.py (vendored copy).
from cli_web.codewiki import __version__ as _pkg_version  # noqa: E402
from cli_web.codewiki.utils.mcp_server import register_mcp_command  # noqa: E402

register_mcp_command(cli, app_name="codewiki", version=_pkg_version)


if __name__ == "__main__":
    main()
