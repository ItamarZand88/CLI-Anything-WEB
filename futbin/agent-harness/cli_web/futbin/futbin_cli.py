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
from cli_web.futbin.commands.config_cmd import config
from cli_web.futbin.commands.evolutions import evolutions
from cli_web.futbin.commands.market import market
from cli_web.futbin.commands.players import players
from cli_web.futbin.commands.sbc import sbc
from cli_web.futbin.utils.repl_skin import ReplSkin

VERSION = "0.1.0"
APP_NAME = "futbin"

_skin = ReplSkin(APP_NAME, version=VERSION)


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output as JSON.")
@click.version_option(VERSION, prog_name="cli-web-futbin")
@click.pass_context
def cli(ctx: click.Context, json_mode: bool):
    """
    cli-web-futbin — EA FC Ultimate Team database CLI.

    Search players, check prices, browse SBCs and Evolutions.
    Run without a subcommand to enter interactive REPL mode.
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode

    if ctx.invoked_subcommand is None:
        _run_repl(ctx)


def _run_repl(ctx: click.Context):
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
        if ctx.obj.get("json"):
            args = ["--json"] + args
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
    print("    players compare <id1> <id2>                   Compare two players + value")
    print("    players price-history <player_id>             Price history + trends")
    print("    players versions --name <name>                All versions compared + value score")
    print()
    print("  Market:")
    print("    market index [--rating 83]                     Price index (detail per tier)")
    print("    market popular [--limit 30]                   Trending players")
    print("    market latest [--page N]                      Newly released cards")
    print("    market cheapest [--rating-min 83]             Best value by rating")
    print("      --rating-max 99 --max-price 5000 --platform ps")
    print("    market movers [--fallers] [--rating-min 80]   Price risers/fallers")
    print("    market fodder [--rating-min 83]               SBC fodder prices")
    print("    market analyze <player_id>                    Price analysis + buy/sell signal")
    print("    market scan [--rating-min 84]                 Bulk undervalue detection")
    print("      --rating-max 90 --threshold 10 --limit 20")
    print("    market arbitrage [--rating-min 85]            Cross-platform price gaps")
    print("      --min-gap 5")
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
    print("    config get <key>                              Get a setting value")
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

# MCP server mode — exposes every command as an MCP tool over stdio.
# Canonical adapter: cli-web-core/cli_web_core/mcp_server.py (vendored copy).
from cli_web.futbin.utils.doctor import register_doctor_command  # noqa: E402
from cli_web.futbin.utils.mcp_server import register_mcp_command  # noqa: E402

register_mcp_command(cli, app_name="futbin", version="0.1.0")
register_doctor_command(cli, app_name="futbin", pkg="futbin")


if __name__ == "__main__":
    cli()
