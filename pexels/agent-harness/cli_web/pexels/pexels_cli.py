"""cli-web-pexels — CLI for Pexels free stock photos and videos."""

import sys

for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass

import shlex

import click
from cli_web.pexels import __version__
from cli_web.pexels.commands.collections import collections
from cli_web.pexels.commands.photos import photos
from cli_web.pexels.commands.users import users
from cli_web.pexels.commands.videos import videos
from cli_web.pexels.core.exceptions import PexelsError
from cli_web.pexels.utils.repl_skin import ReplSkin

_skin = ReplSkin("pexels", version=__version__)


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.version_option(__version__, prog_name="cli-web-pexels")
@click.pass_context
def cli(ctx, json_mode):
    """Pexels — free stock photos and videos from the command line."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode
    if ctx.invoked_subcommand is None:
        _repl(ctx)


cli.add_command(photos)
cli.add_command(videos)
cli.add_command(users)
cli.add_command(collections)


def _repl(ctx):
    """Interactive REPL mode."""
    _skin.print_banner()
    pt_session = _skin.create_prompt_session()

    while True:
        try:
            line = _skin.get_input(pt_session)
        except (EOFError, KeyboardInterrupt):
            _skin.print_goodbye()
            break

        if not line:
            continue

        if line.lower() in ("exit", "quit", "q"):
            _skin.print_goodbye()
            break

        if line.lower() in ("help", "?"):
            _print_repl_help()
            continue

        try:
            args = shlex.split(line)
        except ValueError as e:
            _skin.error(f"Parse error: {e}")
            continue

        if ctx.obj.get("json"):
            args = ["--json"] + args

        try:
            cli.main(args=args, standalone_mode=False)
        except SystemExit:
            pass
        except PexelsError as exc:
            _skin.error(str(exc))
        except click.UsageError as exc:
            _skin.error(str(exc))
        except Exception as exc:
            _skin.error(f"Unexpected error: {exc}")


def _print_repl_help():
    """Print REPL help."""
    _skin.info("Available commands:")
    print()
    print("  photos search <query>          Search photos")
    print("    --orientation <landscape|portrait|square>")
    print("    --size <large|medium|small>   Minimum size")
    print("    --color <hex|name>            Filter by color")
    print("    --page N                      Page number")
    print("  photos get <slug>              Photo details")
    print("  photos download <slug>         Download a photo")
    print("    --size <small|medium|large|original>")
    print("    --output <path>              Output file path")
    print()
    print("  videos search <query>          Search videos")
    print("    --orientation <landscape|portrait|square>")
    print("    --page N                      Page number")
    print("  videos get <slug>              Video details")
    print("  videos download <slug>         Download a video")
    print("    --quality <sd|hd|uhd>        Video quality")
    print("    --output <path>              Output file path")
    print()
    print("  users get <username>           User profile")
    print("  users media <username>         User's photos/videos")
    print("    --page N                      Page number")
    print()
    print("  collections get <slug>         Collection detail + media")
    print("    --page N                      Page number")
    print("  collections discover           Popular & curated collections")
    print()
    print("  help                           Show this help")
    print("  quit                           Exit REPL")
    print()


def main():
    """Entry point for console_scripts."""
    cli()


# MCP server mode — exposes every command as an MCP tool over stdio.
# Canonical adapter: cli-web-core/cli_web_core/mcp_server.py (vendored copy).
from cli_web.pexels import __version__ as _pkg_version  # noqa: E402
from cli_web.pexels.utils.mcp_server import register_mcp_command  # noqa: E402

register_mcp_command(cli, app_name="pexels", version=_pkg_version)


if __name__ == "__main__":
    main()
