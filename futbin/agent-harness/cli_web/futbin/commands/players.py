"""Player commands: search, get, list, compare, price-history."""
import click
from ..core.client import FutbinClient
from ..utils.output import print_json, print_table, print_players_rich, print_comparison, coins_display, print_price_history
from ..utils.helpers import handle_errors, require_year


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
                click.echo(f"\nStats:")
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
def list_players(position, rating_min, rating_max, version, min_price, max_price,
                 cheapest, min_skills, min_wf, gender, league, nation, club,
                 page, year, platform, use_json):
    """List players with filters and pagination."""
    with handle_errors(json_mode=use_json):
        yr = require_year(year)
        plat = platform or "ps"
        sort = f"{plat}_price" if cheapest else None
        order = "asc" if cheapest else None
        with FutbinClient() as client:
            results, has_next = client.list_players(
                min_price=min_price, max_price=max_price, sort=sort, order=order,
                year=yr, position=position, rating_min=rating_min, rating_max=rating_max,
                version=version, platform=plat, min_skills=min_skills, min_wf=min_wf,
                gender=gender, league=league, nation=nation, club=club, page=page,
            )
        if use_json:
            print_json({"players": [p.to_dict() for p in results], "page": page, "has_next": has_next})
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
    """Compare two players side-by-side."""
    with handle_errors(json_mode=use_json):
        yr = require_year(year)
        with FutbinClient() as client:
            comp = client.compare_players(player1_id, player2_id, year=yr)
        print_comparison(comp, json_mode=use_json)


@players.command("price-history")
@click.argument("player_id", type=int)
@click.option("--year", type=int, default=None, help="Game year.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def price_history(player_id, year, use_json):
    """Show price history and trends for a player."""
    with handle_errors(json_mode=use_json):
        yr = require_year(year)
        with FutbinClient() as client:
            history = client.get_price_history(player_id, year=yr)
        if not history.ps_prices and not history.pc_prices:
            from ..core.exceptions import NotFoundError
            raise NotFoundError(f"No price data for player {player_id}")
        print_price_history(history, json_mode=use_json)
