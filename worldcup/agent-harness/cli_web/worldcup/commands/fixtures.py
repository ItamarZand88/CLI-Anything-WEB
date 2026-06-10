"""fixtures commands for cli-web-worldcup — World Cup matches."""

from __future__ import annotations

import click

from ..core.client import WorldcupClient
from ..core.exceptions import NotFoundError
from ..core.models import Match
from ..utils.helpers import handle_errors, print_json
from ..utils.output import json_lines, print_table

# Men's World Cup 2026 runs 2026-06-11 .. 2026-07-19.
_TOURNAMENT_RANGE = "20260611-20260719"


@click.group("fixtures")
def fixtures():
    """World Cup matches (nations games)."""


@fixtures.command("list")
@click.option("--dates", help="YYYYMMDD or YYYYMMDD-YYYYMMDD (default: full tournament)")
@click.option("--team", help="Filter by team name or 3-letter code (e.g. MEX)")
@click.option("--limit", type=int, default=0, help="Cap the number of matches (0 = all)")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.option("--jsonl", "jsonl_mode", is_flag=True, help="One JSON object per line.")
@click.pass_context
def list_fixtures(ctx, dates, team, limit, json_mode, jsonl_mode):
    """List World Cup matches, optionally filtered by team or date."""
    json_mode = json_mode or (ctx.obj or {}).get("json", False)
    with handle_errors(json_mode):
        with WorldcupClient() as client:
            raw = client.scoreboard(dates=dates or _TOURNAMENT_RANGE)
        matches = [Match.from_event(ev).to_dict() for ev in raw.get("events", [])]
        if team:
            t = team.lower()
            matches = [m for m in matches if t in m["home"].lower() or t in m["away"].lower()]
        if limit and limit > 0:
            matches = matches[:limit]

        if jsonl_mode:
            click.echo(json_lines(matches))
        elif json_mode:
            print_json({"success": True, "data": matches})
        elif not matches:
            click.echo("No matches found.")
        else:
            print_table(
                matches,
                [("Date", "date"), ("Match", "name"), ("Stage", "stage"), ("Status", "status")],
            )


@fixtures.command("get")
@click.argument("event_id")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def get_fixture(ctx, event_id, json_mode):
    """Show one match's detail (status, venue, odds line)."""
    json_mode = json_mode or (ctx.obj or {}).get("json", False)
    with handle_errors(json_mode):
        with WorldcupClient() as client:
            raw = client.scoreboard(dates=_TOURNAMENT_RANGE)
        events = [ev for ev in raw.get("events", []) if str(ev.get("id")) == str(event_id)]
        if not events:
            raise NotFoundError(f"No match with id {event_id}")
        match = Match.from_event(events[0]).to_dict()

        if json_mode:
            print_json({"success": True, "data": match})
        else:
            for key, val in match.items():
                if val not in (None, ""):
                    click.echo(f"  {key:12} {val}")
