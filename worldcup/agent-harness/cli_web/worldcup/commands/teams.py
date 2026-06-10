"""teams commands for cli-web-worldcup — the 48 World Cup nations."""

from __future__ import annotations

import click

from ..core.client import WorldcupClient
from ..core.models import Team
from ..utils.helpers import handle_errors, print_json, resolve_team
from ..utils.output import json_lines, print_table


def _all_teams(client: WorldcupClient) -> list[dict]:
    raw = client.teams()
    sports = raw.get("sports") or [{}]
    leagues = sports[0].get("leagues") or [{}]
    return [Team.from_team(t["team"]).to_dict() for t in leagues[0].get("teams", [])]


@click.group("teams")
def teams():
    """World Cup nations."""


@teams.command("list")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.option("--jsonl", "jsonl_mode", is_flag=True, help="One JSON object per line.")
@click.pass_context
def list_teams(ctx, json_mode, jsonl_mode):
    """List all qualified nations."""
    json_mode = json_mode or (ctx.obj or {}).get("json", False)
    with handle_errors(json_mode):
        with WorldcupClient() as client:
            rows = _all_teams(client)
        rows.sort(key=lambda t: t["name"])

        if jsonl_mode:
            click.echo(json_lines(rows))
        elif json_mode:
            print_json({"success": True, "data": rows})
        elif not rows:
            click.echo("No teams found.")
        else:
            print_table(rows, [("ID", "id"), ("Code", "abbreviation"), ("Nation", "name")])


@teams.command("get")
@click.argument("team")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def get_team(ctx, team, json_mode):
    """Show one nation by id, code (MEX), or name."""
    json_mode = json_mode or (ctx.obj or {}).get("json", False)
    with handle_errors(json_mode):
        with WorldcupClient() as client:
            row = resolve_team(team, _all_teams(client))

        if json_mode:
            print_json({"success": True, "data": row})
        else:
            for key, val in row.items():
                if val:
                    click.echo(f"  {key:13} {val}")
