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

# Force UTF-8 output on Windows to handle Unicode player names (ć, é, ö, etc.)
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

from cli_web.futbin.commands.players import players
from cli_web.futbin.commands.market import market
from cli_web.futbin.commands.sbc import sbc
from cli_web.futbin.commands.evolutions import evolutions
from cli_web.futbin.commands.config_cmd import config
from cli_web.futbin.utils.repl_skin import ReplSkin

VERSION = "0.1.0"
APP_NAME = "futbin"

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
    print()
    print("  Players:")
    print("    players search --name <name>                  Search by name")
    print("    players get <player_id>                       Get player details")
    print("    players list [OPTIONS]                        List with filters")
    print("      --position ST --rating-min 90 --cheapest --page 2")
    print("    players compare <id1> <id2>                   Compare two players")
    print()
    print("  Market:")
    print("    market index                                  Price trends")
    print()
    print("  SBCs:")
    print("    sbc list [--category <cat>]                   List SBCs")
    print("    sbc get <sbc_id>                              Get SBC details")
    print()
    print("  Evolutions:")
    print("    evolutions list [--expiring]                  List evolutions")
    print("    evolutions get <evo_id>                       Get evolution details")
    print()
    print("  Config:")
    print("    config set year 25                            Set default year")
    print("    config set platform pc                        Set default platform")
    print("    config show                                   Show current config")
    print("    config reset                                  Reset to defaults")
    print()
    print("  quit                                          Exit REPL")


# ── Command groups ────────────────────────────────────────────────────────────

cli.add_command(players)
cli.add_command(market)
cli.add_command(sbc)
cli.add_command(evolutions)
cli.add_command(config)


if __name__ == "__main__":
    cli()
