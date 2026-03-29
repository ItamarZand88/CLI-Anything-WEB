"""Market commands: index, popular, latest, cheapest."""
import click
from ..core.client import FutbinClient
from ..utils.output import print_json, print_table, print_players_rich
from ..utils.helpers import handle_errors, require_platform


@click.group()
def market():
    """FUTBIN market data."""
    pass


@market.command("index")
@click.option("--rating", default=None, help="Show detail for a rating tier (81, 82, 83, 84, 85, 86, 100, icons).")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def index(rating, use_json):
    """Show market index. Use --rating for detailed view of a specific tier."""
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
    with handle_errors(json_mode=use_json):
        with FutbinClient() as client:
            players, has_next = client.get_latest_players(page=page)
        if use_json:
            print_json({"players": [p.to_dict() for p in players], "page": page, "has_next": has_next})
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
@click.option("--min-price", type=int, default=200, help="Minimum price filter (default: 200, excludes extinct).")
@click.option("--max-price", type=int, default=None, help="Maximum price filter.")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--platform", type=click.Choice(["ps", "pc"]), default=None, help="Platform.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def cheapest(rating_min, rating_max, min_price, max_price, page, platform, use_json):
    """Find cheapest players by rating — best value for SBCs and trading."""
    with handle_errors(json_mode=use_json):
        plat = require_platform(platform)
        sort_field = f"{plat}_price" if plat == "ps" else "pc_price"
        with FutbinClient() as client:
            players, has_next = client.list_players(
                sort=sort_field, order="asc",
                rating_min=rating_min, rating_max=rating_max,
                min_price=min_price, max_price=max_price,
                platform=plat, page=page,
            )
        if use_json:
            print_json({"players": [p.to_dict() for p in players], "page": page, "has_next": has_next})
        else:
            if not players:
                click.echo("No players found in that price/rating range.")
            else:
                print_players_rich(players, title=f"Cheapest {rating_min}-{rating_max} Rated (page {page})")
                if has_next:
                    click.echo(f"  More results — use --page {page + 1}")


@market.command("fodder")
@click.option("--rating-min", type=int, default=None, help="Minimum rating to show (default: all).")
@click.option("--rating-max", type=int, default=None, help="Maximum rating to show.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def fodder(rating_min, rating_max, use_json):
    """SBC fodder prices — cheapest players at each rating tier (81-99)."""
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
                from ..utils.output import coins_display
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
@click.option("--fallers", is_flag=True, default=False, help="Show biggest price fallers instead of risers.")
@click.option("--rating-min", type=int, default=80, help="Minimum rating (default: 80).")
@click.option("--min-price", type=int, default=1000, help="Minimum price filter (default: 1000).")
@click.option("--max-price", type=int, default=15000000, help="Maximum price filter.")
@click.option("--platform", type=click.Choice(["ps", "pc"]), default=None, help="Platform.")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def movers(fallers, rating_min, min_price, max_price, platform, page, use_json):
    """Show biggest price movers — risers (default) or fallers."""
    with handle_errors(json_mode=use_json):
        plat = require_platform(platform)
        direction = "fallers" if fallers else "risers"
        with FutbinClient() as client:
            players, has_next = client.get_market_movers(
                direction=direction, platform=plat, page=page,
                rating_min=rating_min, min_price=min_price,
                max_price=max_price,
            )
        if use_json:
            print_json({"players": [p.to_dict() for p in players], "page": page, "has_next": has_next, "direction": direction})
        else:
            if not players:
                click.echo(f"No {direction} found.")
            else:
                label = "Biggest Risers" if direction == "risers" else "Biggest Fallers"
                print_players_rich(players, title=f"{label} (page {page})")
                if has_next:
                    click.echo(f"  More results — use --page {page + 1}")
