"""Output formatting utilities — JSON and human-readable tables."""
from __future__ import annotations

import json
import sys
from typing import Any


def print_json(data: Any) -> None:
    """Print data as indented JSON to stdout."""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def print_table(rows, columns: list[str] | None = None, *,
                headers: list[str] | None = None, keys: list[str] | None = None) -> None:
    """Print a list of dicts (or objects) as a formatted table.

    Supports two calling conventions:
      - print_table(rows, columns)          — rows are dicts, columns are keys + header labels
      - print_table(rows, headers=..., keys=...) — rows are objects/dicts, keys for access, headers for display
    """
    if not rows:
        print("(no results)")
        return

    # Resolve headers / keys
    if headers is not None and keys is not None:
        display_headers = headers
        access_keys = keys
    elif columns is not None:
        display_headers = columns
        access_keys = columns
    else:
        # Auto-detect from first row
        first = rows[0]
        if isinstance(first, dict):
            access_keys = list(first.keys())
        else:
            access_keys = list(vars(first).keys())
        display_headers = access_keys

    def _get(row, key):
        if isinstance(row, dict):
            return str(row.get(key, ""))
        return str(getattr(row, key, ""))

    # Compute column widths
    widths = {h: len(h) for h in display_headers}
    for row in rows:
        for h, k in zip(display_headers, access_keys):
            widths[h] = max(widths[h], len(_get(row, k)))

    header_line = "  ".join(h.upper().ljust(widths[h]) for h in display_headers)
    sep = "  ".join("-" * widths[h] for h in display_headers)
    print(header_line)
    print(sep)
    for row in rows:
        line = "  ".join(_get(row, k).ljust(widths[h]) for h, k in zip(display_headers, access_keys))
        print(line)


def print_error(msg: str, exit_code: int = 1) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(exit_code)


def coins_display(value: int | None) -> str:
    """Format coin value for display."""
    if value is None:
        return "N/A"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def json_success(data):
    """Format a success response for --json mode."""
    return json.dumps({"success": True, "data": data}, ensure_ascii=False, indent=2, default=str)


def json_error(code: str, message: str, **extra) -> str:
    """Format an error response for --json mode."""
    response = {"error": True, "code": code, "message": message}
    response.update(extra)
    return json.dumps(response, ensure_ascii=False, indent=2)


def print_players_rich(players, title="Players"):
    """Print players as a Rich table."""
    from rich.console import Console
    from rich.table import Table
    console = Console()
    table = Table(title=title)
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Rating", justify="right")
    table.add_column("Version")
    table.add_column("PS Price", justify="right", style="green")
    for p in players:
        table.add_row(
            str(p.id), p.name, p.position, str(p.rating),
            p.version or "", coins_display(p.ps_price) if p.ps_price else "—",
        )
    console.print(table)


def print_comparison(comp, json_mode=False):
    """Print player comparison — Rich table or JSON."""
    if json_mode:
        print_json(comp.to_dict())
        return
    from rich.console import Console
    from rich.table import Table
    console = Console()
    table = Table(title=f"{comp.player1.name} vs {comp.player2.name}")
    table.add_column("Stat")
    table.add_column(comp.player1.name, justify="right")
    table.add_column(comp.player2.name, justify="right")
    table.add_column("Diff", justify="right")
    for stat, vals in comp.stat_diffs.items():
        diff = vals["diff"]
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        style = "green" if diff > 0 else ("red" if diff < 0 else "dim")
        table.add_row(stat.upper(), str(vals["player1"]), str(vals["player2"]),
                      f"[{style}]{diff_str}[/{style}]")
    console.print(table)


def print_sbc_detail(sbc, json_mode=False):
    """Print structured SBC detail."""
    if json_mode:
        print_json(sbc.to_dict())
        return
    print(f"Name:        {sbc.name}")
    print(f"ID:          {sbc.id}")
    if sbc.category:
        print(f"Category:    {sbc.category}")
    if sbc.reward:
        print(f"Reward:      {sbc.reward}")
    if sbc.expires:
        print(f"Expires:     {sbc.expires}")
    if sbc.cost_ps:
        print(f"Cost (PS):   {sbc.cost_ps}")
    if sbc.description:
        print(f"\n{sbc.description}")
    if sbc.requirements:
        print(f"\nRequirements ({len(sbc.requirements)}):")
        for r in sbc.requirements:
            print(f"  - {r.get('text', '')}")


def print_price_history(history, json_mode=False):
    """Print player price history — summary with min/max/current."""
    if json_mode:
        print_json(history.to_dict())
        return
    from datetime import datetime
    print(f"Price History: {history.player_name} (ID: {history.player_id})")
    print()
    for platform, prices in [("PS/Xbox", history.ps_prices), ("PC", history.pc_prices)]:
        if not prices:
            continue
        current = prices[-1][1]
        lowest = min(p[1] for p in prices)
        highest = max(p[1] for p in prices)
        first = prices[0][1]
        change = current - first
        change_pct = (change / first * 100) if first else 0
        # Recent trend (last 7 data points)
        recent = prices[-7:] if len(prices) >= 7 else prices
        recent_change = recent[-1][1] - recent[0][1]
        trend = "rising" if recent_change > 0 else ("falling" if recent_change < 0 else "stable")
        # Format dates
        first_date = datetime.fromtimestamp(prices[0][0] / 1000).strftime("%Y-%m-%d")
        last_date = datetime.fromtimestamp(prices[-1][0] / 1000).strftime("%Y-%m-%d")
        print(f"  {platform}:")
        print(f"    Current:  {coins_display(current)}")
        print(f"    Lowest:   {coins_display(lowest)}")
        print(f"    Highest:  {coins_display(highest)}")
        print(f"    Change:   {coins_display(abs(change))} ({'+'if change >= 0 else '-'}{abs(change_pct):.1f}%)")
        print(f"    Trend:    {trend} (last {len(recent)} days)")
        print(f"    Period:   {first_date} to {last_date} ({len(prices)} data points)")
        print()


def print_evolution_detail(evo, json_mode=False):
    """Print structured evolution detail."""
    if json_mode:
        print_json(evo.to_dict())
        return
    print(f"Name:        {evo.name}")
    print(f"ID:          {evo.id}")
    if evo.category:
        print(f"Category:    {evo.category}")
    if evo.expires:
        print(f"Expires:     {evo.expires}")
    if evo.requirements:
        print(f"\nRequirements ({len(evo.requirements)}):")
        for r in evo.requirements:
            print(f"  - {r.get('text', '')}")
    if evo.upgrades:
        print(f"\nUpgrades ({len(evo.upgrades)}):")
        for u in evo.upgrades:
            print(f"  + {u.get('text', '')}")
