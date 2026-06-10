"""odds commands for cli-web-worldcup — bookmaker odds via The Odds API.

Requires a free API key from https://the-odds-api.com, set as
CLI_WEB_WORLDCUP_ODDS_API_KEY or passed with --api-key. No betting actions
are performed — this is read-only odds data.
"""

from __future__ import annotations

import click

from ..core.client import WorldcupClient
from ..core.models import OddsMatch
from ..utils.helpers import handle_errors, odds_api_key, print_json
from ..utils.output import json_lines


@click.group("odds")
def odds():
    """Bookmaker odds for World Cup matches (read-only)."""


@odds.command("list")
@click.option(
    "--regions",
    default="us",
    show_default=True,
    help="Comma-separated bookmaker regions (us, uk, eu, au).",
)
@click.option("--markets", default="h2h", show_default=True, help="Markets, e.g. h2h,totals.")
@click.option(
    "--odds-format",
    default="decimal",
    show_default=True,
    type=click.Choice(["decimal", "american"]),
)
@click.option("--api-key", help="Odds API key (else $CLI_WEB_WORLDCUP_ODDS_API_KEY).")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.option("--jsonl", "jsonl_mode", is_flag=True, help="One JSON object per line.")
@click.pass_context
def list_odds(ctx, regions, markets, odds_format, api_key, json_mode, jsonl_mode):
    """List bookmaker head-to-head odds for upcoming matches."""
    json_mode = json_mode or (ctx.obj or {}).get("json", False)
    with handle_errors(json_mode):
        with WorldcupClient(odds_api_key=odds_api_key(api_key)) as client:
            raw = client.odds(regions=regions, markets=markets, odds_format=odds_format)
        rows = [OddsMatch.from_event(ev).to_dict() for ev in raw]

        if jsonl_mode:
            click.echo(json_lines(rows))
        elif json_mode:
            print_json({"success": True, "data": rows})
        elif not rows:
            click.echo("No odds available (no upcoming matches in window).")
        else:
            for m in rows:
                click.echo(f"\n{m['away']} @ {m['home']}  ({m['commence_time']})")
                for b in m["bookmakers"]:
                    prices = "  ".join(f"{k} {v}" for k, v in b["h2h"].items())
                    click.echo(f"  {b['bookmaker']:18} {prices}")
