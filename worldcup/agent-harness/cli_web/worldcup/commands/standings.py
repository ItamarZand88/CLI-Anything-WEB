"""standings commands for cli-web-worldcup — group tables."""

from __future__ import annotations

import click

from ..core.client import WorldcupClient
from ..core.models import StandingRow
from ..utils.helpers import handle_errors, print_json
from ..utils.output import json_lines, print_table


def _all_rows(client: WorldcupClient) -> list[dict]:
    raw = client.standings()
    rows: list[dict] = []
    for group in raw.get("children", []):
        name = group.get("name", "")
        for entry in (group.get("standings") or {}).get("entries", []):
            rows.append(StandingRow.from_entry(name, entry).to_dict())
    return rows


@click.group("standings")
def standings():
    """Group standings tables."""


@standings.command("list")
@click.option("--group", "group_filter", help="Only this group, e.g. 'A' or 'Group A'")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.option("--jsonl", "jsonl_mode", is_flag=True, help="One JSON object per line.")
@click.pass_context
def list_standings(ctx, group_filter, json_mode, jsonl_mode):
    """Show group standings (points, W/D/L, goal difference)."""
    json_mode = json_mode or (ctx.obj or {}).get("json", False)
    with handle_errors(json_mode):
        with WorldcupClient() as client:
            rows = _all_rows(client)
        if group_filter:
            g = group_filter.lower().removeprefix("group").strip()
            rows = [r for r in rows if r["group"].lower().removeprefix("group").strip() == g]

        if jsonl_mode:
            click.echo(json_lines(rows))
        elif json_mode:
            print_json({"success": True, "data": rows})
        elif not rows:
            click.echo("No standings found.")
        else:
            cols = [
                ("#", "rank"),
                ("Team", "team"),
                ("P", "played"),
                ("W", "wins"),
                ("D", "draws"),
                ("L", "losses"),
                ("GD", "goal_diff"),
                ("Pts", "points"),
            ]
            for name in dict.fromkeys(r["group"] for r in rows):
                click.echo(f"\n{name}")
                print_table([r for r in rows if r["group"] == name], cols)
