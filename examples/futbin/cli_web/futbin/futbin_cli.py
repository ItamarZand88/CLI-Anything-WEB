"""Main CLI entry point for cli-web-futbin."""

import click

from cli_web.futbin.commands.players import players
from cli_web.futbin.commands.sbc import sbc
from cli_web.futbin.commands.market import market
from cli_web.futbin.commands.evolutions import evolutions
from cli_web.futbin.commands.auth import auth_group


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
@click.version_option(package_name="cli-web-futbin")
@click.pass_context
def cli(ctx, json_mode):
    """FUTBIN — EA FC 26 Ultimate Team database CLI.

    Player stats, prices, SBCs, market index, and evolutions.
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode

    if ctx.invoked_subcommand is None:
        _run_repl(ctx)


def _run_repl(ctx):
    """Start the interactive REPL."""
    from cli_web.futbin.utils.repl_skin import ReplSkin

    skin = ReplSkin("futbin", version="1.0.0")
    skin.print_banner()

    pt_session = skin.create_prompt_session()

    commands_help = {
        "players search <query>": "Search players by name",
        "players list": "List players with filters",
        "players get <id>": "Get player details",
        "players prices <id>": "Get price history",
        "players popular": "Popular players",
        "players latest": "Latest players",
        "sbc list": "List SBCs",
        "sbc cheapest": "Cheapest players by rating",
        "market index": "Market index",
        "evolutions list": "List evolutions",
        "auth status": "Check auth status",
        "help": "Show this help",
        "quit": "Exit REPL",
    }

    while True:
        try:
            line = skin.get_input(pt_session, context="FUTBIN")
        except (EOFError, KeyboardInterrupt):
            skin.print_goodbye()
            break

        if not line:
            continue

        if line in ("quit", "exit", "q"):
            skin.print_goodbye()
            break

        if line == "help":
            skin.help(commands_help)
            continue

        # Parse and dispatch REPL commands
        args = line.split()
        try:
            cli.main(args=args, standalone_mode=False, **ctx.params)
        except click.exceptions.UsageError as e:
            skin.error(str(e))
        except click.exceptions.Abort:
            pass
        except SystemExit:
            pass
        except Exception as e:
            skin.error(f"{type(e).__name__}: {e}")


# Register command groups
cli.add_command(players)
cli.add_command(sbc)
cli.add_command(market)
cli.add_command(evolutions)
cli.add_command(auth_group, "auth")


def main():
    cli()


if __name__ == "__main__":
    main()
