"""cli-web-tripadvisor — TripAdvisor search CLI."""

from __future__ import annotations

import shlex
import sys

# Windows UTF-8 fix — reconfigure both stdout and stderr
for _stream in (sys.stdout, sys.stderr):
    if _stream and getattr(_stream, "encoding", None) and _stream.encoding.lower() not in ("utf-8", "utf8"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass

import click

from .commands.locations import locations
from .commands.hotels import hotels
from .commands.restaurants import restaurants
from .commands.attractions import attractions
from .core.exceptions import TripAdvisorError
from .utils.repl_skin import ReplSkin

_skin = ReplSkin("tripadvisor", version="0.1.0")


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output all results as JSON.")
@click.option("--version", is_flag=True, help="Show version and exit.")
@click.pass_context
def cli(ctx, json_mode, version):
    """🌍  cli-web-tripadvisor — Search hotels, restaurants, and attractions.

    Running without a subcommand enters interactive REPL mode.

    Examples:
      cli-web-tripadvisor locations search "Paris"
      cli-web-tripadvisor hotels search "Paris" --geo-id 187147
      cli-web-tripadvisor restaurants search "New York City" --json
      cli-web-tripadvisor attractions search "London" --page 2
      cli-web-tripadvisor hotels get "https://www.tripadvisor.com/Hotel_Review-..."
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode

    if version:
        click.echo("cli-web-tripadvisor 0.1.0")
        return

    if ctx.invoked_subcommand is None:
        _repl(ctx)


cli.add_command(locations)
cli.add_command(hotels)
cli.add_command(restaurants)
cli.add_command(attractions)


def _print_repl_help() -> None:
    """Print REPL help listing all commands and key options."""
    _skin.info("Available commands:")
    print()
    print("  locations search QUERY        Search for destinations by name")
    print("    --max N                       Max results (default: 6)")
    print()
    print("  hotels search LOCATION        Search hotels in a location")
    print("    --geo-id ID                   Use known geo_id (faster, skips lookup)")
    print("    --page N                      Page number (30 hotels per page)")
    print()
    print("  hotels get URL                Get detailed hotel info by TripAdvisor URL")
    print()
    print("  restaurants search LOCATION   Search restaurants in a location")
    print("    --geo-id ID                   Use known geo_id (faster, skips lookup)")
    print("    --page N                      Page number (30 restaurants per page)")
    print()
    print("  restaurants get URL           Get detailed restaurant info by TripAdvisor URL")
    print()
    print("  attractions search LOCATION   Search attractions/things to do")
    print("    --geo-id ID                   Use known geo_id (faster, skips lookup)")
    print("    --page N                      Page number (30 attractions per page)")
    print()
    print("  attractions get URL           Get detailed attraction info by TripAdvisor URL")
    print()
    print("  Global flags:")
    print("    --json                        Output results as JSON")
    print("    Examples: --json hotels search Paris  OR  hotels search Paris --json")
    print()
    print("  Workflow tip:")
    print("    1. locations search 'Paris'     → get geo_id (e.g. 187147)")
    print("    2. hotels search Paris --geo-id 187147  → list hotels with URLs")
    print("    3. hotels get 'URL'             → detailed info for one hotel")
    print()
    print("  help                            Show this help")
    print("  quit / exit                     Exit REPL")
    print()


def _repl(ctx: click.Context) -> None:
    """Interactive REPL loop."""
    _skin.print_banner()
    pt_session = _skin.create_prompt_session()

    while True:
        try:
            line = _skin.get_input(pt_session)
        except (KeyboardInterrupt, EOFError):
            break

        line = line.strip()
        if not line:
            continue
        if line in ("help", "?", "h"):
            _print_repl_help()
            continue
        if line in ("quit", "exit", "q"):
            break

        try:
            args = shlex.split(line)
        except ValueError as exc:
            click.echo(f"Parse error: {exc}", err=True)
            continue

        repl_args = ["--json"] + args if ctx.obj.get("json") else args
        try:
            cli.main(args=repl_args, standalone_mode=False)
        except SystemExit:
            pass
        except Exception as exc:
            if ctx.obj.get("json") and isinstance(exc, TripAdvisorError):
                import json as _json
                click.echo(_json.dumps(exc.to_dict()))
            else:
                click.echo(f"Error: {exc}", err=True)


def main() -> None:
    """Entry point for cli-web-tripadvisor."""
    cli()


if __name__ == "__main__":
    main()
