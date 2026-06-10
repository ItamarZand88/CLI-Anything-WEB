"""Player commands: search, get, list, compare, price-history, versions."""

import click

from ..core.analysis import compute_coins_per_stat, compute_total_stats, compute_value_score
from ..core.client import FutbinClient
from ..utils.helpers import handle_errors, require_year, resolve_json_mode
from ..utils.output import (
    coins_display,
    print_comparison,
    print_json,
    print_players_rich,
    print_price_history,
    print_versions,
)


@click.group()
def players():
    """Search, list, and compare EA FC players."""
    pass


@players.command("search")
@click.option("--name", required=True, help="Player name to search.")
@click.option("--year", type=int, default=None, help="Game year (default: config or 26).")
@click.option("--evolutions", is_flag=True, default=False, help="Include evolution variants.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def search(name, year, evolutions, use_json):
    """Search players by name."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        yr = require_year(year)
        with FutbinClient() as client:
            results = client.search_players(name, year=yr, evolutions=evolutions)
        if use_json:
            print_json([p.to_dict() for p in results])
        else:
            if not results:
                click.echo("No players found.")
            else:
                print_players_rich(results, title=f"Search: {name}")


@players.command("get")
@click.argument("player_id", type=int)
@click.option("--year", type=int, default=None, help="Game year (default: config or 26).")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def get_player(player_id, year, use_json):
    """Get detailed player info by ID."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        yr = require_year(year)
        with FutbinClient() as client:
            player = client.get_player(player_id, year=yr)
        if not player:
            from ..core.exceptions import NotFoundError

            raise NotFoundError(f"Player {player_id} not found")
        if use_json:
            print_json(player.to_dict())
        else:
            click.echo(f"Name:     {player.name}")
            click.echo(f"ID:       {player.id}")
            click.echo(f"Position: {player.position}")
            click.echo(f"Rating:   {player.rating}")
            click.echo(f"Version:  {player.version}")
            if player.ps_price:
                click.echo(f"PS Price: {coins_display(player.ps_price)}")
            if player.stats:
                click.echo("\nStats:")
                for stat, val in player.stats.items():
                    click.echo(f"  {stat.upper()}: {val}")


@players.command("list")
@click.option("--position", default=None, help="Filter by position (ST, CM, GK, etc.).")
@click.option("--rating-min", type=int, default=None, help="Minimum overall rating.")
@click.option("--rating-max", type=int, default=None, help="Maximum overall rating.")
@click.option("--version", default=None, help="Card version (gold_rare, toty, icons, etc.).")
@click.option("--min-price", type=int, default=None, help="Minimum price.")
@click.option("--max-price", type=int, default=None, help="Maximum price.")
@click.option("--cheapest", is_flag=True, default=False, help="Sort by cheapest first.")
@click.option("--min-skills", type=int, default=None, help="Minimum skill moves (1-5).")
@click.option("--min-wf", type=int, default=None, help="Minimum weak foot (1-5).")
@click.option("--gender", type=click.Choice(["men", "women"]), default=None)
@click.option("--league", default=None, help="League ID.")
@click.option("--nation", default=None, help="Nation ID.")
@click.option("--club", default=None, help="Club ID.")
@click.option("--page", type=int, default=1, help="Page number (default: 1).")
@click.option("--year", type=int, default=None, help="Game year.")
@click.option("--platform", type=click.Choice(["ps", "pc"]), default=None)
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def list_players(
    position,
    rating_min,
    rating_max,
    version,
    min_price,
    max_price,
    cheapest,
    min_skills,
    min_wf,
    gender,
    league,
    nation,
    club,
    page,
    year,
    platform,
    use_json,
):
    """List players with filters and pagination."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        yr = require_year(year)
        plat = platform or "ps"
        sort = f"{plat}_price" if cheapest else None
        order = "asc" if cheapest else None
        with FutbinClient() as client:
            results, has_next = client.list_players(
                min_price=min_price,
                max_price=max_price,
                sort=sort,
                order=order,
                year=yr,
                position=position,
                rating_min=rating_min,
                rating_max=rating_max,
                version=version,
                platform=plat,
                min_skills=min_skills,
                min_wf=min_wf,
                gender=gender,
                league=league,
                nation=nation,
                club=club,
                page=page,
            )
        if use_json:
            print_json(
                {"players": [p.to_dict() for p in results], "page": page, "has_next": has_next}
            )
        else:
            if not results:
                click.echo("No players found.")
            else:
                print_players_rich(results, title=f"Players (page {page})")
                if has_next:
                    click.echo(f"  More results available — use --page {page + 1}")


@players.command("compare")
@click.argument("player1_id", type=int)
@click.argument("player2_id", type=int)
@click.option("--year", type=int, default=None, help="Game year.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def compare(player1_id, player2_id, year, use_json):
    """Compare two players side-by-side with value metrics."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        yr = require_year(year)
        with FutbinClient() as client:
            comp = client.compare_players(player1_id, player2_id, year=yr)

        # Compute value metrics for each player
        p1_total = compute_total_stats(comp.player1.stats)
        p2_total = compute_total_stats(comp.player2.stats)
        p1_cps = compute_coins_per_stat(p1_total, comp.player1.ps_price)
        p2_cps = compute_coins_per_stat(p2_total, comp.player2.ps_price)

        value_winner = None
        if p1_cps is not None and p2_cps is not None:
            value_winner = comp.player1.name if p1_cps < p2_cps else comp.player2.name

        value_data = {
            "player1_total_stats": p1_total,
            "player2_total_stats": p2_total,
            "player1_coins_per_stat": p1_cps,
            "player2_coins_per_stat": p2_cps,
            "value_winner": value_winner,
        }

        print_comparison(comp, json_mode=use_json, value_data=value_data)


@players.command("price-history")
@click.argument("player_id", type=int)
@click.option("--year", type=int, default=None, help="Game year.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def price_history(player_id, year, use_json):
    """Show price history and trends for a player."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        yr = require_year(year)
        with FutbinClient() as client:
            history = client.get_price_history(player_id, year=yr)
        if not history.ps_prices and not history.pc_prices:
            from ..core.exceptions import NotFoundError

            raise NotFoundError(f"No price data for player {player_id}")
        print_price_history(history, json_mode=use_json)


@players.command("versions")
@click.option("--name", required=True, help="Player name to search.")
@click.option("--year", type=int, default=None, help="Game year (default: config or 26).")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def versions(name, year, use_json):
    """All versions of a player compared with value scores."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        yr = require_year(year)
        with FutbinClient() as client:
            search_results = client.search_players(name, year=yr)
            if not search_results:
                from ..core.exceptions import NotFoundError

                raise NotFoundError(f"No players found for '{name}'")

            # Filter to only versions of the same base player
            # Use the top result's name as the reference
            base_name = search_results[0].name.lower()
            same_player = [p for p in search_results if p.name.lower() == base_name]
            # If only one exact match, include close matches (name contained)
            if len(same_player) <= 1:
                same_player = [
                    p
                    for p in search_results
                    if base_name in p.name.lower() or p.name.lower() in base_name
                ]
            candidates = same_player[:10]

            from rich.progress import Progress

            detailed = []
            with Progress() as progress:
                task = progress.add_task(
                    f"Fetching {len(candidates)} versions...", total=len(candidates)
                )
                for p in candidates:
                    try:
                        full = client.get_player(p.id, year=yr)
                        if full:
                            detailed.append(full)
                    except Exception:
                        pass
                    progress.advance(task)

        if not detailed:
            from ..core.exceptions import NotFoundError

            raise NotFoundError(f"Could not load details for '{name}'")

        # Sort by rating descending
        detailed.sort(key=lambda p: p.rating, reverse=True)

        # Compute value scores
        version_data = []
        for p in detailed:
            d = p.to_dict()
            d["value_score"] = compute_value_score(p.stats, p.ps_price)
            d["total_stats"] = compute_total_stats(p.stats)
            version_data.append(d)

        if use_json:
            print_json(version_data)
        else:
            # Use search result name (clean, no version suffix)
            base_display_name = search_results[0].name
            print_versions(detailed, version_data, title=f"All Versions of {base_display_name}")
