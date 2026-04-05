"""cli-web-amazon entry point — Amazon CLI."""
import sys

# Windows UTF-8 fix — must be before any imports that print
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

from .commands.search import search
from .commands.suggest import suggest
from .commands.product import product
from .commands.bestsellers import bestsellers
from .core.exceptions import AmazonError
from .utils.repl_skin import ReplSkin

__version__ = "1.0.0"

_skin = ReplSkin("amazon", version=__version__)


def _print_repl_help():
    """Print REPL command reference."""
    _skin.info("Available commands:")
    print()
    print("  suggest <query>                   Autocomplete suggestions")
    print("  search <query> [OPTIONS]          Search Amazon products")
    print("    --page N                        Page number (default: 1)")
    print("    --dept <department>             Department filter")
    print()
    print("  product get <ASIN>                Product detail by ASIN")
    print()
    print("  bestsellers [<category>]          Best Sellers list")
    print("    category: electronics, books, toys-and-games, music, ...")
    print("    --page N                        Page number")
    print()
    print("  Global options: --json            Output as JSON")
    print()
    print("  help    Show this help")
    print("  quit    Exit REPL")
    print()


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, default=False,
              help="Output all results as JSON.")
@click.version_option(__version__, "--version", "-V")
@click.pass_context
def cli(ctx, json_mode):
    """cli-web-amazon — Browse and search Amazon from your terminal.

    Run without a subcommand to enter interactive REPL mode.

    Examples:
      cli-web-amazon search laptop
      cli-web-amazon product get B0GRZ78683
      cli-web-amazon bestsellers electronics
      cli-web-amazon suggest headphones
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode

    if ctx.invoked_subcommand is None:
        # Enter REPL mode
        _run_repl(ctx, json_mode)


def _run_repl(ctx, json_mode: bool):
    """Run interactive REPL mode."""
    _skin.print_banner()

    if not json_mode:
        _skin.info("Type 'help' for commands, 'quit' to exit.")
        print()

    pt_session = _skin.create_prompt_session()

    while True:
        try:
            line = _skin.get_input(pt_session)
        except (EOFError, KeyboardInterrupt):
            _skin.print_goodbye()
            break

        if not line:
            continue

        cmd = line.strip().lower()
        if cmd in ("quit", "exit", "q"):
            _skin.print_goodbye()
            break
        if cmd in ("help", "?", "h"):
            _print_repl_help()
            continue

        try:
            args = shlex.split(line)
        except ValueError as exc:
            _skin.error(f"Parse error: {exc}")
            continue

        # Preserve --json flag
        repl_args = ["--json"] + args if json_mode else args

        try:
            cli.main(args=repl_args, standalone_mode=False)
        except SystemExit:
            pass
        except click.UsageError as exc:
            _skin.error(str(exc))
        except Exception as exc:
            if json_mode and isinstance(exc, AmazonError):
                import json as _json
                click.echo(_json.dumps(exc.to_dict()))
            else:
                _skin.error(str(exc))


# Register subcommands
cli.add_command(search)
cli.add_command(suggest)
cli.add_command(product)
cli.add_command(bestsellers)



def main():
    """Entry point for cli-web-amazon."""
    cli()


if __name__ == "__main__":
    main()
