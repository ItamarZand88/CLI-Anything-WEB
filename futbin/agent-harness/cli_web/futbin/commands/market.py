"""Market commands: index, popular, latest, cheapest, analyze, scan, arbitrage."""

import click

from ..core.analysis import compute_platform_gap, compute_price_analysis
from ..core.client import FutbinClient
from ..utils.helpers import handle_errors, require_platform, require_year, resolve_json_mode
from ..utils.output import (
    print_analysis,
    print_arbitrage,
    print_json,
    print_players_rich,
    print_scan_results,
    print_table,
)


@click.group()
def market():
    """FUTBIN market data."""
    pass


@market.command("index")
@click.option(
    "--rating",
    default=None,
    help="Show detail for a rating tier (81, 82, 83, 84, 85, 86, 100, icons).",
)
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def index(rating, use_json):
    """Show market index. Use --rating for detailed view of a specific tier."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        with FutbinClient() as client:
            if rating:
                detail = client.get_market_detail(rating)
                if use_json:
                    print_json(detail.to_dict())
                else:
                    click.echo(f"  {detail.name}")
                    click.echo(f"  Current:  {detail.current}  ({detail.change_pct})")
                    if detail.open_value:
                        click.echo(f"  Open:     {detail.open_value}")
                    if detail.lowest:
                        click.echo(f"  Lowest:   {detail.lowest}")
                    if detail.highest:
                        click.echo(f"  Highest:  {detail.highest}")
            else:
                items = client.get_market_index()
                if use_json:
                    print_json([i.to_dict() for i in items])
                else:
                    if not items:
                        click.echo("No market data available.")
                    else:
                        print_table(
                            items,
                            headers=["Name", "Last", "Change %"],
                            keys=["name", "last", "change_pct"],
                        )


@market.command("popular")
@click.option("--limit", type=int, default=30, help="Number of players to show (max 250).")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def popular(limit, use_json):
    """Show trending/most-viewed players."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        with FutbinClient() as client:
            players = client.get_popular_players(limit=min(limit, 250))
        if use_json:
            print_json([p.to_dict() for p in players])
        else:
            if not players:
                click.echo("No popular players found.")
            else:
                print_players_rich(players, title=f"Popular Players (top {len(players)})")


@market.command("latest")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def latest(page, use_json):
    """Show newly released player cards."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        with FutbinClient() as client:
            players, has_next = client.get_latest_players(page=page)
        if use_json:
            print_json(
                {"players": [p.to_dict() for p in players], "page": page, "has_next": has_next}
            )
        else:
            if not players:
                click.echo("No new players found.")
            else:
                print_players_rich(players, title=f"Latest Players (page {page})")
                if has_next:
                    click.echo(f"  More results — use --page {page + 1}")


@market.command("cheapest")
@click.option("--rating-min", type=int, default=83, help="Minimum rating (default: 83).")
@click.option("--rating-max", type=int, default=99, help="Maximum rating (default: 99).")
@click.option(
    "--min-price",
    type=int,
    default=200,
    help="Minimum price filter (default: 200, excludes extinct).",
)
@click.option("--max-price", type=int, default=None, help="Maximum price filter.")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--platform", type=click.Choice(["ps", "pc"]), default=None, help="Platform.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def cheapest(rating_min, rating_max, min_price, max_price, page, platform, use_json):
    """Find cheapest players by rating — best value for SBCs and trading."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        plat = require_platform(platform)
        sort_field = f"{plat}_price" if plat == "ps" else "pc_price"
        with FutbinClient() as client:
            players, has_next = client.list_players(
                sort=sort_field,
                order="asc",
                rating_min=rating_min,
                rating_max=rating_max,
                min_price=min_price,
                max_price=max_price,
                platform=plat,
                page=page,
            )
        if use_json:
            print_json(
                {"players": [p.to_dict() for p in players], "page": page, "has_next": has_next}
            )
        else:
            if not players:
                click.echo("No players found in that price/rating range.")
            else:
                print_players_rich(
                    players, title=f"Cheapest {rating_min}-{rating_max} Rated (page {page})"
                )
                if has_next:
                    click.echo(f"  More results — use --page {page + 1}")


@market.command("fodder")
@click.option("--rating-min", type=int, default=None, help="Minimum rating to show (default: all).")
@click.option("--rating-max", type=int, default=None, help="Maximum rating to show.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def fodder(rating_min, rating_max, use_json):
    """SBC fodder prices — cheapest players at each rating tier (81-99)."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        with FutbinClient() as client:
            tiers = client.get_sbc_fodder()
        # Filter tiers
        if rating_min:
            tiers = [t for t in tiers if t.rating >= rating_min]
        if rating_max:
            tiers = [t for t in tiers if t.rating <= rating_max]
        if use_json:
            print_json([t.to_dict() for t in tiers])
        else:
            if not tiers:
                click.echo("No fodder data found.")
            else:
                from rich.console import Console
                from rich.table import Table

                console = Console()
                table = Table(title="SBC Fodder Prices")
                table.add_column("Rating", justify="right", style="bold")
                table.add_column("Cheapest", style="green")
                table.add_column("Player", style="cyan")
                table.add_column("Pos")
                table.add_column("2nd", style="dim")
                table.add_column("3rd", style="dim")
                for tier in tiers:
                    p = tier.players
                    table.add_row(
                        str(tier.rating),
                        p[0].price if p else "—",
                        p[0].name if p else "—",
                        p[0].position if p else "",
                        p[1].price if len(p) > 1 else "",
                        p[2].price if len(p) > 2 else "",
                    )
                console.print(table)


@market.command("movers")
@click.option(
    "--fallers", is_flag=True, default=False, help="Show biggest price fallers instead of risers."
)
@click.option("--rating-min", type=int, default=80, help="Minimum rating (default: 80).")
@click.option("--min-price", type=int, default=1000, help="Minimum price filter (default: 1000).")
@click.option("--max-price", type=int, default=15000000, help="Maximum price filter.")
@click.option("--platform", type=click.Choice(["ps", "pc"]), default=None, help="Platform.")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def movers(fallers, rating_min, min_price, max_price, platform, page, use_json):
    """Show biggest price movers — risers (default) or fallers."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        plat = require_platform(platform)
        direction = "fallers" if fallers else "risers"
        with FutbinClient() as client:
            players, has_next = client.get_market_movers(
                direction=direction,
                platform=plat,
                page=page,
                rating_min=rating_min,
                min_price=min_price,
                max_price=max_price,
            )
        if use_json:
            print_json(
                {
                    "players": [p.to_dict() for p in players],
                    "page": page,
                    "has_next": has_next,
                    "direction": direction,
                }
            )
        else:
            if not players:
                click.echo(f"No {direction} found.")
            else:
                label = "Biggest Risers" if direction == "risers" else "Biggest Fallers"
                print_players_rich(players, title=f"{label} (page {page})")
                if has_next:
                    click.echo(f"  More results — use --page {page + 1}")


@market.command("analyze")
@click.argument("player_id", type=int)
@click.option("--year", type=int, default=None, help="Game year (default: config or 26).")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def analyze(player_id, year, use_json):
    """Price analysis with buy/sell signal for a player."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        yr = require_year(year)
        with FutbinClient() as client:
            player = client.get_player(player_id, year=yr)
            if not player:
                from ..core.exceptions import NotFoundError

                raise NotFoundError(f"Player {player_id} not found")
            history = client.get_price_history(player_id, year=yr)

        ps_analysis = {}
        pc_analysis = {}
        if history.ps_prices and player.ps_price:
            ps_analysis = compute_price_analysis(history.ps_prices, player.ps_price)
        if history.pc_prices and player.xbox_price:
            pc_analysis = compute_price_analysis(history.pc_prices, player.xbox_price)

        gap = compute_platform_gap(player.ps_price, player.xbox_price)

        result = {
            "player": player.to_dict(),
            "analysis": {
                "ps": ps_analysis,
                "pc": pc_analysis,
                "platform_gap_pct": gap["gap_pct"],
            },
        }

        if use_json:
            print_json(result)
        else:
            print_analysis(player, ps_analysis, pc_analysis, gap)


@market.command("scan")
@click.option("--rating-min", type=int, default=84, help="Minimum rating (default: 84).")
@click.option("--rating-max", type=int, default=90, help="Maximum rating (default: 90).")
@click.option("--platform", type=click.Choice(["ps", "pc"]), default=None, help="Platform.")
@click.option("--limit", type=int, default=20, help="Number of players to analyze (default: 20).")
@click.option(
    "--threshold", type=float, default=10, help="Min % below 30d avg to flag (default: 10)."
)
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def scan(rating_min, rating_max, platform, limit, threshold, use_json):
    """Bulk undervalue/overvalue detection — scan cheapest players for deals."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        plat = require_platform(platform)
        sort_field = f"{plat}_price" if plat == "ps" else "pc_price"

        with FutbinClient() as client:
            players, _ = client.list_players(
                sort=sort_field,
                order="asc",
                rating_min=rating_min,
                rating_max=rating_max,
                min_price=200,
                platform=plat,
            )
            candidates = players[:limit]

            if not candidates:
                if use_json:
                    print_json([])
                else:
                    click.echo("No players found in that rating range.")
                return

            from rich.progress import Progress

            results = []
            with Progress() as progress:
                task = progress.add_task("Analyzing players...", total=len(candidates))
                for p in candidates:
                    try:
                        history = client.get_price_history(p.id, year=p.year)
                    except Exception:
                        progress.advance(task)
                        continue

                    prices = history.ps_prices if plat == "ps" else history.pc_prices
                    current = p.ps_price if plat == "ps" else p.xbox_price
                    if not prices or not current:
                        progress.advance(task)
                        continue

                    analysis = compute_price_analysis(prices, current)
                    if not analysis:
                        progress.advance(task)
                        continue

                    results.append(
                        {
                            "id": p.id,
                            "name": p.name,
                            "position": p.position,
                            "rating": p.rating,
                            "version": p.version,
                            "current_price": current,
                            "avg_30d": analysis["avg_30d"],
                            "vs_avg_30d_pct": analysis["vs_avg_30d_pct"],
                            "trend_7d": analysis["trend_7d"],
                            "signal": analysis["signal"],
                        }
                    )
                    progress.advance(task)

        if use_json:
            print_json(results)
        else:
            print_scan_results(results, threshold, plat)


@market.command("arbitrage")
@click.option("--rating-min", type=int, default=85, help="Minimum rating (default: 85).")
@click.option("--rating-max", type=int, default=92, help="Maximum rating (default: 92).")
@click.option("--min-gap", type=float, default=5, help="Minimum gap %% to show (default: 5).")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def arbitrage(rating_min, rating_max, min_gap, page, use_json):
    """Cross-platform price gaps — find arbitrage opportunities between PS and PC."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        with FutbinClient() as client:
            players, has_next = client.list_players(
                sort="ps_price",
                order="asc",
                rating_min=rating_min,
                rating_max=rating_max,
                min_price=200,
                platform="ps",
                page=page,
            )

        results = []
        for p in players:
            gap = compute_platform_gap(p.ps_price, p.xbox_price)
            if gap["gap_pct"] < min_gap:
                continue
            results.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "position": p.position,
                    "rating": p.rating,
                    "version": p.version,
                    "ps_price": p.ps_price,
                    "pc_price": p.xbox_price,
                    "gap_pct": gap["gap_pct"],
                    "gap_coins": gap["gap_coins"],
                    "cheaper_on": gap["cheaper_on"],
                }
            )

        # Sort by gap descending
        results.sort(key=lambda x: x["gap_pct"], reverse=True)

        if use_json:
            print_json({"players": results, "page": page, "has_next": has_next})
        else:
            print_arbitrage(results, page, has_next)
