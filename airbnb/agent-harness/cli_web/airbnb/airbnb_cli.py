"""cli-web-airbnb — Airbnb search and listings CLI."""

from __future__ import annotations

import json as _json
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

from .commands.autocomplete import autocomplete_group
from .commands.listings import listings
from .commands.search import search
from .core.exceptions import AirbnbError
from .utils.repl_skin import ReplSkin

_skin = ReplSkin("airbnb", version="0.1.0")


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output all results as JSON.")
@click.option("--version", is_flag=True, help="Show version and exit.")
@click.pass_context
def cli(ctx, json_mode, version):
    """🏠  cli-web-airbnb — Search Airbnb stays, listings and locations.

    Running without a subcommand enters interactive REPL mode.

    Examples:
      cli-web-airbnb search stays "London, UK"
      cli-web-airbnb search stays "Paris, France" --checkin 2024-06-01 --checkout 2024-06-05 --json
      cli-web-airbnb listings get 770993223449115417
      cli-web-airbnb autocomplete locations "New Yor"
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode

    if version:
        click.echo("cli-web-airbnb 0.1.0")
        return

    if ctx.invoked_subcommand is None:
        _repl(ctx)


cli.add_command(search)
cli.add_command(listings)
cli.add_command(autocomplete_group, name="autocomplete")


def _print_repl_help() -> None:
    """Print REPL help listing all commands and key options."""
    _skin.info("Available commands:")
    print()
    print("  search stays LOCATION     Search for stays in a location")
    print("    --checkin DATE            Check-in date (YYYY-MM-DD)")
    print("    --checkout DATE           Check-out date (YYYY-MM-DD)")
    print("    --adults N                Number of adults (default: 1)")
    print("    --children N              Number of children")
    print("    --infants N               Number of infants")
    print("    --pets N                  Number of pets (0 or 1)")
    print("    --min-price N             Minimum nightly price")
    print("    --max-price N             Maximum nightly price")
    print("    --room-type TYPE          Filter: entire_home|private_room|shared_room|hotel_room")
    print("    --amenity ID              Filter by amenity ID (repeatable: 4=WiFi, 8=Kitchen, 40=AC, 33=Pool)")
    print("    --cursor TOKEN            Pagination cursor for next page")
    print("    --page N                  Page number (note: Airbnb uses cursors, not pages)")
    print("    --locale TEXT             Language locale (default: en)")
    print("    --currency TEXT           Currency code (default: USD)")
    print()
    print("  listings get LISTING_ID   Get details for a specific listing")
    print("    --adults N                Number of adults")
    print("    --checkin DATE            Check-in date")
    print("    --checkout DATE           Check-out date")
    print("    --locale TEXT             Language locale (default: en)")
    print("    --currency TEXT           Currency code (default: USD)")
    print()
    print("  listings reviews LISTING_ID  Get guest reviews for a listing")
    print("    --limit N                 Number of reviews (default: 24)")
    print("    --offset N                Pagination offset (default: 0)")
    print("    --sort ORDER              Sort: BEST_QUALITY|RECENT|RATING_DESC|RATING_ASC")
    print()
    print("  listings availability LISTING_ID  Get 12-month availability calendar")
    print("    --month N                 Starting month 1-12 (default: current)")
    print("    --year N                  Starting year (default: current)")
    print("    --count N                 Number of months to fetch (default: 12)")
    print()
    print("  autocomplete locations QUERY  Suggest locations for a partial query")
    print("    --num-results N           Number of suggestions (default: 5)")
    print()
    print("  Global flags:")
    print("    --json                    Output results as JSON (place before OR after subcommand)")
    print("    Examples: --json search stays \"London\" OR: search stays \"London\" --json")
    print()
    print("  help                        Show this help")
    print("  quit / exit                 Exit REPL")
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
            if ctx.obj.get("json"):
                payload = exc.to_dict() if isinstance(exc, AirbnbError) else {"error": True, "code": "ERROR", "message": str(exc)}
                click.echo(_json.dumps(payload))
            else:
                click.echo(f"Error: {exc}", err=True)


def main() -> None:
    """Entry point for cli-web-airbnb."""
    cli()
