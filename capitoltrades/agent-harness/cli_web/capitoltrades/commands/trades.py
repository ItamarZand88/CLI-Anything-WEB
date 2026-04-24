"""Trade-related commands: list, get, stats."""
from __future__ import annotations

import click

from ..core.client import CapitoltradesClient
from ..core.exceptions import NotFoundError
from ..core.models import (
    parse_trades_list,
    parse_trade_detail,
    parse_trades_stats,
)
from ..utils.helpers import handle_errors, print_json


@click.group()
def trades():
    """Commands for querying congressional trades."""


# Map human-readable size brackets to the numeric IDs the site uses in its
# ?tradeSize=<N> query param. Discovered by probing each ID 1-10 against the
# /trades endpoint and inspecting the returned size column.
_SIZE_MAP = {
    "<1K": 1,
    "1K-15K": 2,
    "15K-50K": 3,
    "50K-100K": 4,
    "100K-250K": 5,
    "250K-500K": 6,
    "500K-1M": 7,
    "1M-5M": 8,
    "5M-25M": 9,
    "25M-50M": 10,
}
_SIZE_CHOICES = list(_SIZE_MAP)


def _render_trade_rows(rows: list[dict]) -> None:
    """Shared pretty-printer for trade rows (used by list + by-ticker)."""
    for r in rows:
        pol = r.get("politician_name") or r.get("politician_id") or "?"
        tkr = r.get("ticker") or r.get("issuer_name") or "?"
        size = r.get("size") or "?"
        ttype = r.get("tx_type") or "?"
        traded = r.get("traded") or "?"
        click.echo(f"  [{r.get('trade_id')}] {ttype:<8} {pol:<30} {tkr:<20} {size:<12} {traded}")


@trades.command("list")
@click.option("--page", type=int, default=1, show_default=True, help="Page number (1-indexed).")
@click.option("--page-size", type=int, default=12, show_default=True, help="Rows per page.")
@click.option("--politician", type=str, default=None, help="Filter by politician ID (bioguide, e.g. Y000067).")
@click.option("--issuer", type=str, default=None, help="Filter by issuer internal ID (e.g. 435544).")
@click.option("--party", type=click.Choice(["republican", "democrat", "independent"], case_sensitive=False), default=None, help="Filter by party.")
@click.option("--chamber", type=click.Choice(["house", "senate"], case_sensitive=False), default=None, help="Filter by chamber.")
@click.option("--tx-type", type=click.Choice(["buy", "sell", "exchange"], case_sensitive=False), default=None, help="Filter by transaction type.")
@click.option("--sector", type=str, default=None, help="Filter by sector (e.g. health-care, information-technology).")
@click.option("--size", "size_filter", type=click.Choice(_SIZE_CHOICES, case_sensitive=False), default=None, help="Filter by trade size bracket.")
@click.option("--sort", type=click.Choice(["traded", "pubDate", "filedAfter", "tradeSize"], case_sensitive=False), default=None, help="Sort column (matches the site's sortable headers).")
@click.option("--sort-direction", type=click.Choice(["asc", "desc"], case_sensitive=False), default="desc", show_default=True, help="Sort direction (used with --sort).")
@click.pass_context
def list_trades(
    ctx, page, page_size, politician, issuer, party, chamber, tx_type, sector,
    size_filter, sort, sort_direction,
):
    """List trades with optional filters (matches capitoltrades.com/trades)."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        params: dict = {"page": page, "pageSize": page_size}
        if politician:
            params["politician"] = politician
        if issuer:
            params["issuer"] = issuer
        if party:
            params["party"] = party.lower()
        if chamber:
            params["chamber"] = chamber.lower()
        if tx_type:
            params["txType"] = tx_type.lower()
        if sector:
            params["sector"] = sector
        if size_filter:
            # Normalize to bracket key (strip "–"/"—") then map to the site's numeric ID.
            key = size_filter.replace("–", "-").replace("—", "-").upper()
            if key in _SIZE_MAP:
                params["tradeSize"] = _SIZE_MAP[key]
        if sort:
            params["sortBy"] = sort
            params["sortDirection"] = sort_direction.lower()

        with CapitoltradesClient() as client:
            soup = client.get_html("/trades", params=params)
            rows = parse_trades_list(soup)

        if json_mode:
            print_json({"success": True, "data": rows, "meta": {"page": page, "page_size": page_size, "filters": {k: v for k, v in params.items() if k not in ("page", "pageSize")}}})
        else:
            if not rows:
                click.echo("No trades found.")
                return
            _render_trade_rows(rows)


@trades.command("get")
@click.argument("trade_id")
@click.pass_context
def get_trade(ctx, trade_id):
    """Get a single trade by ID."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        with CapitoltradesClient() as client:
            soup = client.get_html(f"/trades/{trade_id}")
            data = parse_trade_detail(soup, trade_id)
        if not (data.get("tx_type") or data.get("politician_id") or data.get("issuer_id")):
            raise NotFoundError(f"Trade {trade_id} not found")
        if json_mode:
            print_json({"success": True, "data": data})
        else:
            click.echo(f"Trade #{trade_id}")
            click.echo(f"  {data.get('title')}")
            click.echo(f"  Type:       {data.get('tx_type')}  Size: {data.get('size')}  Price: {data.get('price')}  Shares: {data.get('shares')}")
            click.echo(
                f"  Politician: {data.get('politician_name')} ({data.get('politician_id')}) — "
                f"{data.get('politician_party')} / {data.get('politician_chamber')} / {data.get('politician_state')}"
            )
            click.echo(f"  Issuer:     {data.get('issuer_name')} ({data.get('ticker')}) [id={data.get('issuer_id')}]")
            click.echo(f"  Traded:     {data.get('traded')}   Published: {data.get('published')}   Filed on: {data.get('filed_on')}")
            click.echo(f"  Reporting gap: {data.get('reporting_gap')}   Owner: {data.get('owner')}   Asset: {data.get('asset_type')}")
            if data.get("comment"):
                click.echo(f"  Comment:    {data.get('comment')}")
            if data.get("filing_url"):
                click.echo(f"  Filing:     {data.get('filing_url')}")


@trades.command("by-ticker")
@click.argument("ticker")
@click.option("--page", type=int, default=1, show_default=True, help="Page number.")
@click.option("--page-size", type=int, default=12, show_default=True, help="Rows per page.")
@click.option("--party", type=click.Choice(["republican", "democrat", "independent"], case_sensitive=False), default=None)
@click.option("--tx-type", type=click.Choice(["buy", "sell", "exchange"], case_sensitive=False), default=None)
@click.pass_context
def by_ticker(ctx, ticker, page, page_size, party, tx_type):
    """Find trades for a ticker symbol (e.g. NVDA) — resolves via BFF issuer search."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        with CapitoltradesClient() as client:
            # Step 1: resolve ticker -> issuer_id via BFF
            search_res = client.get_bff_json("/issuers", params={"search": ticker})
            issuers = search_res.get("data", [])
            # Prefer exact ticker match (e.g. "NVDA" → "NVDA:US")
            wanted = ticker.upper().rstrip(":US")
            match = None
            for item in issuers:
                tkr = (item.get("issuerTicker") or "").upper()
                if tkr.startswith(wanted + ":") or tkr == wanted:
                    match = item
                    break
            if match is None and issuers:
                match = issuers[0]  # fall back to best fuzzy match
            if match is None:
                raise NotFoundError(f"No issuer matching ticker '{ticker}'")

            issuer_id = str(match["_issuerId"])

            # Step 2: fetch trades for this issuer
            params: dict = {"page": page, "pageSize": page_size, "issuer": issuer_id}
            if party:
                params["party"] = party.lower()
            if tx_type:
                params["txType"] = tx_type.lower()
            soup = client.get_html("/trades", params=params)
            rows = parse_trades_list(soup)

        if json_mode:
            print_json({
                "success": True,
                "data": rows,
                "meta": {
                    "page": page,
                    "page_size": page_size,
                    "resolved_issuer": {
                        "issuer_id": issuer_id,
                        "name": match.get("issuerName"),
                        "ticker": match.get("issuerTicker"),
                        "sector": match.get("sector"),
                    },
                },
            })
        else:
            click.echo(f"Trades for {match.get('issuerName')} ({match.get('issuerTicker')}) [id={issuer_id}]")
            if not rows:
                click.echo("  No trades found.")
                return
            _render_trade_rows(rows)


@trades.command("stats")
@click.pass_context
def stats_cmd(ctx):
    """Show aggregate stats from the trades overview page."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        with CapitoltradesClient() as client:
            soup = client.get_html("/trades")
            stats = parse_trades_stats(soup)
        if json_mode:
            print_json({"success": True, "data": stats})
        else:
            click.echo("Capitol Trades — Overview stats:")
            for k, v in stats.items():
                click.echo(f"  {k.capitalize()}: {v}")
