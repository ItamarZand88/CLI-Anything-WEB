"""Output formatting utilities — JSON and human-readable tables."""

from __future__ import annotations

import json
import sys
from typing import Any


def print_json(data: Any) -> None:
    """Print data as indented JSON to stdout."""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def print_table(
    rows,
    columns: list[str] | None = None,
    *,
    headers: list[str] | None = None,
    keys: list[str] | None = None,
) -> None:
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
        for h, k in zip(display_headers, access_keys, strict=False):
            widths[h] = max(widths[h], len(_get(row, k)))

    header_line = "  ".join(h.upper().ljust(widths[h]) for h in display_headers)
    sep = "  ".join("-" * widths[h] for h in display_headers)
    print(header_line)
    print(sep)
    for row in rows:
        line = "  ".join(
            _get(row, k).ljust(widths[h])
            for h, k in zip(display_headers, access_keys, strict=False)
        )
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
            str(p.id),
            p.name,
            p.position,
            str(p.rating),
            p.version or "",
            coins_display(p.ps_price) if p.ps_price else "—",
        )
    console.print(table)


def print_comparison(comp, json_mode=False, value_data=None):
    """Print player comparison — Rich table or JSON."""
    if json_mode:
        data = comp.to_dict()
        if value_data:
            data["value"] = value_data
        print_json(data)
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
        table.add_row(
            stat.upper(),
            str(vals["player1"]),
            str(vals["player2"]),
            f"[{style}]{diff_str}[/{style}]",
        )
    # Value metrics row
    if value_data:
        table.add_section()
        p1_cps = value_data.get("player1_coins_per_stat")
        p2_cps = value_data.get("player2_coins_per_stat")
        p1_str = f"{p1_cps:.0f}" if p1_cps is not None else "N/A"
        p2_str = f"{p2_cps:.0f}" if p2_cps is not None else "N/A"
        winner = value_data.get("value_winner", "")
        winner_str = f"[green]{winner}[/green]" if winner else "—"
        table.add_row(
            "TOTAL STATS",
            str(value_data["player1_total_stats"]),
            str(value_data["player2_total_stats"]),
            "",
        )
        table.add_row("COINS/STAT", p1_str, p2_str, winner_str)
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
        print(
            f"    Change:   {coins_display(abs(change))} ({'+' if change >= 0 else '-'}{abs(change_pct):.1f}%)"
        )
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


def _signal_style(signal: str) -> str:
    """Return Rich markup color for a signal string."""
    if signal == "BUY":
        return "green"
    if signal == "SELL":
        return "red"
    return "yellow"


def print_analysis(player, ps_analysis, pc_analysis, gap):
    """Print price analysis for a player using Rich."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    console.print(
        f"\n[bold]{player.name}[/bold]  (ID: {player.id})  {player.position}  {player.rating} OVR"
    )

    for label, analysis in [("PS/Xbox", ps_analysis), ("PC", pc_analysis)]:
        if not analysis:
            continue
        signal = analysis["signal"]
        style = _signal_style(signal)

        table = Table(title=f"{label} Analysis", show_header=True)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Current Price", coins_display(analysis["current"]))
        table.add_row("Historic Min", coins_display(analysis["min"]))
        table.add_row("Historic Max", coins_display(analysis["max"]))
        table.add_row("30d Average", coins_display(analysis["avg_30d"]))
        table.add_row("Price Position", f"{analysis['price_position_pct']}%")
        vs_pct = analysis["vs_avg_30d_pct"]
        vs_style = "green" if vs_pct < 0 else ("red" if vs_pct > 0 else "dim")
        table.add_row("vs 30d Avg", f"[{vs_style}]{vs_pct:+.1f}%[/{vs_style}]")
        table.add_row("7d Trend", f"{analysis['trend_7d']:+.1f}%")
        table.add_row("30d Trend", f"{analysis['trend_30d']:+.1f}%")
        table.add_row("Volatility (30d)", f"{analysis['volatility_30d']}%")
        table.add_row("Signal", f"[bold {style}]{signal}[/bold {style}]")

        console.print(table)

    if gap.get("gap_pct", 0) > 0:
        console.print(
            f"\n  Platform gap: {gap['gap_pct']}% ({coins_display(gap['gap_coins'])} coins) — cheaper on {gap['cheaper_on'].upper()}"
        )
    console.print()


def print_scan_results(results, threshold, platform):
    """Print bulk scan results using Rich."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    # Filter by threshold
    flagged = [r for r in results if r["vs_avg_30d_pct"] <= -threshold]
    flagged.sort(key=lambda x: x["vs_avg_30d_pct"])

    if not flagged:
        console.print(
            f"\nNo players found below -{threshold}% of 30d average on {platform.upper()}."
        )
        if results:
            console.print(
                f"  (Analyzed {len(results)} players. Closest: {results[0]['vs_avg_30d_pct']:+.1f}%)"
            )
        return

    table = Table(
        title=f"Undervalued Players on {platform.upper()} (below -{threshold}% of 30d avg)"
    )
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Rating", justify="right")
    table.add_column("Price", justify="right", style="green")
    table.add_column("30d Avg", justify="right")
    table.add_column("vs Avg", justify="right")
    table.add_column("7d Trend", justify="right")
    table.add_column("Signal")

    for r in flagged:
        signal = r["signal"]
        style = _signal_style(signal)
        table.add_row(
            str(r["id"]),
            r["name"],
            r["position"],
            str(r["rating"]),
            coins_display(r["current_price"]),
            coins_display(r["avg_30d"]),
            f"[green]{r['vs_avg_30d_pct']:+.1f}%[/green]",
            f"{r['trend_7d']:+.1f}%",
            f"[{style}]{signal}[/{style}]",
        )

    console.print(table)
    console.print(f"\n  {len(flagged)} of {len(results)} players below threshold")


def print_arbitrage(results, page, has_next):
    """Print cross-platform arbitrage results using Rich."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    if not results:
        console.print("\nNo significant cross-platform price gaps found.")
        return

    table = Table(title=f"Cross-Platform Arbitrage Opportunities (page {page})")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Rating", justify="right")
    table.add_column("PS Price", justify="right", style="green")
    table.add_column("PC Price", justify="right", style="blue")
    table.add_column("Gap %", justify="right", style="yellow")
    table.add_column("Gap Coins", justify="right")
    table.add_column("Cheaper On")

    for r in results:
        cheaper_style = "green" if r["cheaper_on"] == "ps" else "blue"
        table.add_row(
            str(r["id"]),
            r["name"],
            r["position"],
            str(r["rating"]),
            coins_display(r["ps_price"]),
            coins_display(r["pc_price"]),
            f"{r['gap_pct']:.1f}%",
            coins_display(r["gap_coins"]),
            f"[{cheaper_style}]{r['cheaper_on'].upper()}[/{cheaper_style}]",
        )

    console.print(table)
    if has_next:
        console.print(f"  More results — use --page {page + 1}")


def print_versions(players, version_data, title=None):
    """Print all versions of a player compared using Rich."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    if not players:
        console.print("No versions found.")
        return

    table = Table(title=title or f"All Versions ({len(players)} cards)")
    table.add_column("ID", style="dim")
    table.add_column("Version", style="bold")
    table.add_column("Rating", justify="right")
    table.add_column("Pos", style="cyan")
    table.add_column("PAC", justify="right")
    table.add_column("SHO", justify="right")
    table.add_column("PAS", justify="right")
    table.add_column("DRI", justify="right")
    table.add_column("DEF", justify="right")
    table.add_column("PHY", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("PS Price", justify="right", style="green")
    table.add_column("Value", justify="right", style="yellow")

    for p, vd in zip(players, version_data, strict=False):
        stats = p.stats or {}
        vs = vd.get("value_score")
        vs_str = f"{vs}" if vs is not None else "N/A"
        ver = p.version or vd.get("version") or "Base"
        table.add_row(
            str(p.id),
            ver,
            str(p.rating),
            p.position,
            str(stats.get("pac", "")),
            str(stats.get("sho", "")),
            str(stats.get("pas", "")),
            str(stats.get("dri", "")),
            str(stats.get("def", "")),
            str(stats.get("phy", "")),
            str(vd.get("total_stats", "")),
            coins_display(p.ps_price) if p.ps_price else "—",
            vs_str,
        )

    console.print(table)
    console.print("\n  Value Score = total_stats / (price / 1000). Higher = better value per coin.")
