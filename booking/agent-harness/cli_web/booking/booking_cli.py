"""cli-web-booking — Agent-native CLI for Booking.com.

Search hotels, get property details, and resolve destinations.
Uses curl_cffi for TLS impersonation to bypass AWS WAF.
"""

import sys

# Force UTF-8 on Windows
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

from . import __version__
from .commands.auth_cmd import auth_group
from .commands.properties import get_property
from .commands.search import autocomplete, search_group

VERSION = __version__


@click.group(invoke_without_command=True)
@click.version_option(VERSION, prog_name="cli-web-booking")
@click.option("--json", "json_mode", is_flag=True, help="JSON output mode.")
@click.pass_context
def cli(ctx: click.Context, json_mode: bool):
    """cli-web-booking — Search Booking.com from the command line."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode
    if ctx.invoked_subcommand is None:
        _run_repl(ctx)


# ── Register commands ───────────────────────────────────────────────

cli.add_command(search_group)
cli.add_command(get_property)
cli.add_command(autocomplete)
cli.add_command(auth_group)


# ── REPL ────────────────────────────────────────────────────────────

def _run_repl(ctx: click.Context | None = None):
    """Interactive REPL mode."""
    from .utils.repl_skin import ReplSkin

    skin = ReplSkin("booking", version=VERSION)
    skin.print_banner()

    session = skin.create_prompt_session()
    json_mode = ctx.obj.get("json", False) if ctx else False

    while True:
        try:
            line = skin.get_input(session)
        except (EOFError, KeyboardInterrupt):
            skin.print_goodbye()
            break

        if not line:
            continue

        lower = line.strip().lower()
        if lower in ("quit", "exit", "q"):
            skin.print_goodbye()
            break
        if lower in ("help", "h", "?"):
            _print_repl_help(skin)
            continue

        try:
            args = shlex.split(line)
        except ValueError as e:
            skin.error(f"Parse error: {e}")
            continue

        # Prepend --json if top-level flag was set
        repl_args = ["--json"] + args if json_mode else args

        try:
            cli.main(args=repl_args, standalone_mode=False)
        except SystemExit:
            pass
        except click.UsageError as e:
            skin.error(str(e))
        except Exception as e:
            skin.error(str(e))


def _print_repl_help(skin):
    """Print REPL help with available commands."""
    skin.info("Available commands:")
    print()
    print("  search find <destination> [OPTIONS]")
    print("    --checkin YYYY-MM-DD     Check-in date (default: tomorrow)")
    print("    --checkout YYYY-MM-DD    Check-out date (default: +3 days)")
    print("    --adults N               Number of adults (default: 2)")
    print("    --rooms N                Number of rooms (default: 1)")
    print("    --sort <popularity|price|review_score|distance>")
    print("    --page N                 Results page")
    print()
    print("  get <slug>                 Property details")
    print("    --checkin/--checkout      Date range for pricing")
    print()
    print("  autocomplete <query>       Resolve destination names")
    print("    --limit N                Max results (default: 5)")
    print()
    print("  auth login                 Open browser for WAF cookies")
    print("  auth status                Check cookie status")
    print("  auth logout                Clear stored cookies")
    print()
    print("  help                       Show this help")
    print("  quit                       Exit REPL")
    print()


if __name__ == "__main__":
    cli()
