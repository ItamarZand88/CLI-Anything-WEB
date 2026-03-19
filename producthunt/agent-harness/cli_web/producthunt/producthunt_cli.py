"""
cli-web-producthunt -- Agent-native CLI for Product Hunt (HTML scraping).

Usage:
    cli-web-producthunt                           # Enter REPL mode
    cli-web-producthunt posts list
    cli-web-producthunt posts get some-product
    cli-web-producthunt posts leaderboard --period weekly
    cli-web-producthunt users get rrhoover
    cli-web-producthunt auth status
"""
import sys

# Force UTF-8 output on Windows to handle Unicode characters
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

import shlex

import click

from cli_web.producthunt.commands.posts import posts
from cli_web.producthunt.commands.users import users
from cli_web.producthunt.commands.auth_cmd import auth
from cli_web.producthunt.utils.repl_skin import ReplSkin

VERSION = "2.0.0"
APP_NAME = "producthunt"

_skin = ReplSkin(APP_NAME, version=VERSION)


@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Force JSON output in REPL mode.")
@click.version_option(VERSION, prog_name="cli-web-producthunt")
@click.pass_context
def cli(ctx, use_json):
    """
    cli-web-producthunt -- Product Hunt CLI powered by HTML scraping.

    Browse posts, leaderboard, and users.
    No API key required -- uses curl_cffi with Chrome TLS impersonation.
    Run without a subcommand to enter interactive REPL mode.
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = use_json
    if ctx.invoked_subcommand is None:
        _run_repl(use_json)


def _run_repl(json_mode: bool = False):
    """Interactive REPL mode."""
    _skin.print_banner()
    _skin.info("Type 'help' for available commands, 'quit' to exit.")

    while True:
        try:
            line = input(_skin.prompt()).strip()
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

        # Propagate --json flag from parent into REPL commands
        args = shlex.split(line)
        if json_mode and "--json" not in args:
            args.append("--json")

        try:
            cli.main(args, standalone_mode=False, prog_name="cli-web-producthunt")
        except SystemExit:
            pass
        except click.UsageError as exc:
            _skin.error(str(exc))
        except Exception as exc:
            _skin.error(str(exc))


def _print_repl_help():
    _skin.info("Available commands:")
    print()
    print("  Posts:")
    print("    posts list [--json]")
    print("    posts get <slug> [--json]")
    print("    posts leaderboard [--period daily|weekly|monthly] [--date YYYY-MM-DD] [--json]")
    print()
    print("  Users:")
    print("    users get <username> [--json]")
    print()
    print("  Auth:")
    print("    auth status [--json]")
    print()
    print("  REPL:")
    print("    help                              Show this help")
    print("    quit                              Exit REPL")
    print()


# -- Register command groups -----------------------------------------------

cli.add_command(posts)
cli.add_command(users)
cli.add_command(auth)


def main():
    cli()


if __name__ == "__main__":
    main()
