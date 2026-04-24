"""Issuer-related commands: list, get, search (via BFF JSON)."""
from __future__ import annotations

import click

from ..core.client import CapitoltradesClient
from ..core.exceptions import NotFoundError
from ..core.models import parse_issuers_list, parse_issuer_detail
from ..utils.helpers import handle_errors, print_json


@click.group()
def issuers():
    """Commands for querying issuers (companies, bonds, funds, etc.)."""


@issuers.command("list")
@click.option("--page", type=int, default=1, show_default=True, help="Page number.")
@click.option("--page-size", type=int, default=12, show_default=True, help="Rows per page.")
@click.option("--sector", type=str, default=None, help="Filter by sector.")
@click.pass_context
def list_issuers(ctx, page, page_size, sector):
    """List issuers."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        params: dict = {"page": page, "pageSize": page_size}
        if sector:
            params["sector"] = sector
        with CapitoltradesClient() as client:
            soup = client.get_html("/issuers", params=params)
            rows = parse_issuers_list(soup)
        if json_mode:
            print_json({"success": True, "data": rows, "meta": {"page": page, "page_size": page_size}})
        else:
            if not rows:
                click.echo("No issuers found.")
                return
            for r in rows:
                iid = r.get("issuer_id") or "?"
                name = r.get("name") or "?"
                ticker = r.get("ticker") or "?"
                click.echo(f"  [{iid}] {name:<40} {ticker}")


@issuers.command("get")
@click.argument("issuer_id")
@click.pass_context
def get_issuer(ctx, issuer_id):
    """Get a single issuer by ID (e.g. 435544)."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        with CapitoltradesClient() as client:
            soup = client.get_html(f"/issuers/{issuer_id}")
            data = parse_issuer_detail(soup, issuer_id)
        if not data.get("name"):
            raise NotFoundError(f"Issuer {issuer_id} not found")
        if json_mode:
            print_json({"success": True, "data": data})
        else:
            click.echo(f"Issuer {issuer_id}: {data.get('name')}")
            trades = data.get("recent_trades") or []
            click.echo(f"  Recent trades ({len(trades)}):")
            for t in trades[:10]:
                click.echo(
                    f"    [{t.get('trade_id')}] {t.get('tx_type'):<5} "
                    f"{t.get('politician_name') or t.get('politician_id')}  "
                    f"{t.get('size')}  {t.get('traded')}"
                )


@issuers.command("search")
@click.argument("query")
@click.option("--full/--no-full", default=False, help="Include full price history in output.")
@click.pass_context
def search_issuer(ctx, query, full):
    """Search issuers via the BFF JSON API (returns rich data: price history, stats, sector)."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        with CapitoltradesClient() as client:
            data = client.get_bff_json("/issuers", params={"search": query})

        items = data.get("data", [])
        if not full:
            # Slim down: drop eodPrices to keep JSON output small
            for item in items:
                perf = item.get("performance") or {}
                if "eodPrices" in perf:
                    prices = perf.get("eodPrices") or []
                    if prices:
                        item["performance"] = {
                            **{k: v for k, v in perf.items() if k != "eodPrices"},
                            "latest_price": prices[0],
                            "eod_prices_count": len(prices),
                        }

        if json_mode:
            print_json({"success": True, "data": items, "meta": data.get("meta", {})})
        else:
            paging = data.get("meta", {}).get("paging", {})
            total = paging.get("totalItems", 0)
            click.echo(f"Found {total} issuer(s) matching '{query}':")
            for item in items:
                iid = item.get("_issuerId")
                name = item.get("issuerName") or "?"
                ticker = item.get("issuerTicker") or "?"
                sector = item.get("sector") or "?"
                mcap = (item.get("performance") or {}).get("mcap")
                stats = item.get("stats") or {}
                click.echo(f"  [{iid}] {name}  ({ticker})")
                click.echo(f"      sector={sector}  mcap={mcap}  politicians={stats.get('countPoliticians')}  trades={stats.get('countTrades')}")
