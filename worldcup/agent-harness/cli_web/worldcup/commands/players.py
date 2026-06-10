"""players commands for cli-web-worldcup — national-team squads."""

from __future__ import annotations

import click

from ..core.client import WorldcupClient
from ..core.models import Player
from ..utils.helpers import handle_errors, print_json, resolve_team
from ..utils.output import json_lines, print_table
from .teams import _all_teams


@click.group("players")
def players():
    """National-team squads (rosters)."""


@players.command("roster")
@click.argument("team")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.option("--jsonl", "jsonl_mode", is_flag=True, help="One JSON object per line.")
@click.pass_context
def roster(ctx, team, json_mode, jsonl_mode):
    """List a nation's squad. TEAM is an id, code (MEX), or name."""
    json_mode = json_mode or (ctx.obj or {}).get("json", False)
    with handle_errors(json_mode):
        with WorldcupClient() as client:
            resolved = resolve_team(team, _all_teams(client))
            raw = client.roster(resolved["id"])
        rows = [Player.from_athlete(a).to_dict() for a in raw.get("athletes", [])]

        if jsonl_mode:
            click.echo(json_lines(rows))
        elif json_mode:
            print_json({"success": True, "data": rows, "team": resolved["name"]})
        elif not rows:
            click.echo(f"No squad listed for {resolved['name']} yet.")
        else:
            click.echo(f"{resolved['name']} — {len(rows)} players")
            print_table(
                rows,
                [("#", "jersey"), ("Pos", "position"), ("Player", "name"), ("Age", "age")],
            )
