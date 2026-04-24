"""Politician-related commands: list, get."""
from __future__ import annotations

import click

from ..core.client import CapitoltradesClient
from ..core.exceptions import NotFoundError
from ..core.models import parse_politicians_list, parse_politician_detail
from ..utils.helpers import handle_errors, print_json


@click.group()
def politicians():
    """Commands for querying US politicians tracked on Capitol Trades."""


@politicians.command("list")
@click.option("--page", type=int, default=1, show_default=True, help="Page number.")
@click.option("--page-size", type=int, default=12, show_default=True, help="Rows per page.")
@click.option("--party", type=click.Choice(["republican", "democrat", "independent"], case_sensitive=False), default=None, help="Filter by party.")
@click.option("--chamber", type=click.Choice(["house", "senate"], case_sensitive=False), default=None, help="Filter by chamber.")
@click.option("--state", type=str, default=None, help="Filter by state code (e.g. CA).")
@click.pass_context
def list_politicians(ctx, page, page_size, party, chamber, state):
    """List politicians with optional filters."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        params: dict = {"page": page, "pageSize": page_size}
        if party:
            params["party"] = party.lower()
        if chamber:
            params["chamber"] = chamber.lower()
        if state:
            params["state"] = state.upper()

        with CapitoltradesClient() as client:
            soup = client.get_html("/politicians", params=params)
            rows = parse_politicians_list(soup)

        if json_mode:
            print_json({"success": True, "data": rows, "meta": {"page": page, "page_size": page_size}})
        else:
            if not rows:
                click.echo("No politicians found.")
                return
            for r in rows:
                name = r.get("name") or "?"
                pid = r.get("politician_id") or "?"
                party = r.get("party") or "?"
                state = r.get("state") or "?"
                trades = r.get("trades_count") or "?"
                click.echo(f"  [{pid}] {name:<35} {party:<12} {state:<20} trades={trades}")


@politicians.command("top")
@click.option("--by", "sort_by", type=click.Choice(["trades", "volume"], case_sensitive=False), default="trades", show_default=True, help="Ranking metric.")
@click.option("--page-size", type=int, default=10, show_default=True, help="Number of politicians to show.")
@click.option("--party", type=click.Choice(["republican", "democrat", "independent"], case_sensitive=False), default=None)
@click.option("--chamber", type=click.Choice(["house", "senate"], case_sensitive=False), default=None)
@click.pass_context
def top_politicians(ctx, sort_by, page_size, party, chamber):
    """Show the top politicians by trade count or volume (leaderboard)."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        sort_key = "tradeCount" if sort_by.lower() == "trades" else "volume"
        params: dict = {
            "page": 1,
            "pageSize": page_size,
            "sortBy": sort_key,
            "sortDirection": "desc",
        }
        if party:
            params["party"] = party.lower()
        if chamber:
            params["chamber"] = chamber.lower()

        with CapitoltradesClient() as client:
            soup = client.get_html("/politicians", params=params)
            rows = parse_politicians_list(soup)

        if json_mode:
            print_json({
                "success": True,
                "data": rows,
                "meta": {"sort_by": sort_by, "page_size": page_size},
            })
        else:
            if not rows:
                click.echo("No politicians found.")
                return
            click.echo(f"Top {len(rows)} politicians by {sort_by}:")
            for i, r in enumerate(rows, 1):
                name = r.get("name") or "?"
                pid = r.get("politician_id") or "?"
                trades = r.get("trades_count")
                vol = r.get("volume") or "?"
                click.echo(f"  {i:>2}. [{pid}] {name:<35} trades={trades}  volume={vol}")


@politicians.command("get")
@click.argument("politician_id")
@click.pass_context
def get_politician(ctx, politician_id):
    """Get a single politician by bioguide ID (e.g. Y000067)."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        with CapitoltradesClient() as client:
            soup = client.get_html(f"/politicians/{politician_id}")
            data = parse_politician_detail(soup, politician_id)
        if not data.get("name"):
            raise NotFoundError(f"Politician {politician_id} not found")
        if json_mode:
            print_json({"success": True, "data": data})
        else:
            click.echo(f"Politician {politician_id}: {data.get('name')}")
            stats = data.get("stats") or {}
            if stats:
                click.echo("  Stats:")
                for k, v in stats.items():
                    click.echo(f"    {k}: {v}")
            trades = data.get("recent_trades") or []
            click.echo(f"  Recent trades ({len(trades)}):")
            for t in trades[:10]:
                click.echo(
                    f"    [{t.get('trade_id')}] {t.get('tx_type'):<5} {t.get('ticker') or t.get('issuer_name')} "
                    f"{t.get('size')}  {t.get('traded')}"
                )
