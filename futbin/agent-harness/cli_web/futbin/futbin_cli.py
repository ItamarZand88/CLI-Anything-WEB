"""
cli-web-futbin — Agent-native CLI for FUTBIN EA FC Ultimate Team database.

Usage:
    cli-web-futbin                       # Enter REPL mode
    cli-web-futbin players search --name Mbappe
    cli-web-futbin players get --id 40
    cli-web-futbin market index
    cli-web-futbin sbc list
    cli-web-futbin evolutions list
"""
import sys
import click

from cli_web.futbin.commands.players import players
from cli_web.futbin.commands.market import market
from cli_web.futbin.commands.sbc import sbc
from cli_web.futbin.commands.evolutions import evolutions
from cli_web.futbin.core.auth import get_status, login, logout
from cli_web.futbin.utils.repl_skin import ReplSkin

VERSION = "0.1.0"
APP_NAME = "futbin"
APP_URL = "https://www.futbin.com"

_skin = ReplSkin(APP_NAME, version=VERSION)


@click.group(invoke_without_command=True)
@click.version_option(VERSION, prog_name="cli-web-futbin")
@click.pass_context
def cli(ctx: click.Context):
    """
    cli-web-futbin — EA FC Ultimate Team database CLI.

    Search players, check prices, browse SBCs and Evolutions.
    Run without a subcommand to enter interactive REPL mode.
    """
    if ctx.invoked_subcommand is None:
        _run_repl()


def _run_repl():
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

        # Parse and dispatch
        import shlex
        args = shlex.split(line)
        try:
            cli.main(args, standalone_mode=False, prog_name="cli-web-futbin")
        except SystemExit:
            pass
        except click.UsageError as e:
            _skin.error(str(e))
        except Exception as e:
            _skin.error(str(e))


def _print_repl_help():
    _skin.info("Available commands:")
    print("  players search --name <query>                     Search players by name")
    print("  players get --id <id>                             Player details + prices")
    print("  players list [OPTIONS]                            Browse with filters:")
    print("    --position <GK|CB|LB|RB|CM|CAM|CDM|ST|RW|LW>  Filter by position")
    print("    --rating-min <N> --rating-max <N>               Rating range (40-99)")
    print("    --version <gold_rare|toty|fut_birthday|...>     Card type")
    print("    --min-price <N> --max-price <N>                 Price range (coins)")
    print("    --cheapest                                      Sort cheapest first")
    print("    --min-skills <1-5> --min-wf <1-5>              Skill/weak foot stars")
    print("    --sort <ps_price|overall|name> --order asc|desc Sort order")
    print("  market index                                      EA FC market index")
    print("  sbc list [--category <cat>]                       List Squad Building Challenges")
    print("  sbc get --id <id>                                 SBC details")
    print("  evolutions list [--expiring]                      List player evolutions")
    print("  evolutions get --id <id>                          Evolution details")
    print("  auth status                                       Check auth status")
    print("  quit                                              Exit REPL")


# ── Command groups ────────────────────────────────────────────────────────────

cli.add_command(players)
cli.add_command(market)
cli.add_command(sbc)
cli.add_command(evolutions)


# ── Auth commands ─────────────────────────────────────────────────────────────

@cli.group()
def auth():
    """Authentication management (optional — FUTBIN is public)."""


@auth.command("status")
@click.option("--json", "as_json", is_flag=True)
def auth_status(as_json: bool):
    """Show authentication status."""
    from cli_web.futbin.utils.output import print_json
    status = get_status()
    if as_json:
        print_json(status)
    else:
        for k, v in status.items():
            click.echo(f"{k}: {v}")


@auth.command("login")
def auth_login():
    """Log in to FUTBIN (optional — enables personal features)."""
    login(APP_URL)


@auth.command("logout")
def auth_logout():
    """Remove stored credentials."""
    logout()


if __name__ == "__main__":
    cli()
