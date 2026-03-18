"""Player commands for cli-web-futbin."""
import click

from cli_web.futbin.core.client import FutbinClient
from cli_web.futbin.utils.output import print_json, print_table, print_error, coins_display


@click.group()
def players():
    """Search and browse EA FC players."""


@players.command("search")
@click.option("--name", "-n", required=True, help="Player name to search for")
@click.option("--year", "-y", default=26, show_default=True, help="Game year (26, 25, 24...)")
@click.option("--evolutions", is_flag=True, default=False, help="Include evolution versions")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def search(name: str, year: int, evolutions: bool, as_json: bool):
    """Search for players by name."""
    with FutbinClient() as client:
        try:
            results = client.search_players(name, year=year, evolutions=evolutions)
        except Exception as e:
            print_error(str(e))

    if not results:
        if as_json:
            print_json([])
        else:
            click.echo(f"No players found for '{name}'")
        return

    if as_json:
        print_json([p.to_dict() for p in results])
    else:
        rows = [
            {
                "id": p.id,
                "name": p.name,
                "rating": p.rating,
                "position": p.position,
                "version": p.version,
                "club": p.club,
                "nation": p.nation,
            }
            for p in results
        ]
        print_table(rows, ["id", "name", "rating", "position", "version", "club", "nation"])


@players.command("get")
@click.option("--id", "player_id", required=True, type=int, help="Player ID")
@click.option("--year", "-y", default=26, show_default=True, help="Game year")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def get_player(player_id: int, year: int, as_json: bool):
    """Get detailed player information including prices and stats."""
    with FutbinClient() as client:
        try:
            player = client.get_player(player_id, year=year)
        except Exception as e:
            print_error(str(e))

    if not player:
        print_error(f"Player {player_id} not found")

    if as_json:
        print_json(player.to_dict())
    else:
        click.echo(f"\n{player.name} ({player.position}) — {player.version}")
        click.echo(f"Rating:   {player.rating}")
        click.echo(f"Club:     {player.club}")
        click.echo(f"Nation:   {player.nation}")
        click.echo(f"PS Price: {coins_display(player.ps_price)}")
        click.echo(f"XB Price: {coins_display(player.xbox_price)}")
        if player.stats:
            click.echo(f"\nStats:")
            for k, v in player.stats.items():
                click.echo(f"  {k.upper()}: {v}")
        click.echo(f"\nURL: https://www.futbin.com{player.url}")


@players.command("list")
@click.option("--name", "-n", default=None, help="Filter by name")
@click.option("--position", "-p", default=None,
              help="Position filter: GK, CB, LB, RB, CAM, CM, CDM, RM, LM, ST, RW, LW")
@click.option("--rating-min", type=click.IntRange(40, 99), default=None,
              help="Minimum overall rating (40-99)")
@click.option("--rating-max", type=click.IntRange(40, 99), default=None,
              help="Maximum overall rating (40-99)")
@click.option("--version", default=None,
              help="Card version (e.g. gold_rare, gold_if, toty, fut_birthday, icons, heroes)")
@click.option("--min-price", type=int, default=None, help="Minimum price (in coins)")
@click.option("--max-price", type=int, default=None, help="Maximum price (in coins)")
@click.option("--platform", default="ps", show_default=True,
              type=click.Choice(["ps", "pc"]), help="Platform for price filters")
@click.option("--cheapest", is_flag=True,
              help="Sort by cheapest price ascending (shorthand for --sort ps_price --order asc)")
@click.option("--sort", default="ps_price", show_default=True,
              help="Sort field: ps_price, pc_price, overall (rating), name")
@click.option("--order", default="desc", show_default=True,
              type=click.Choice(["asc", "desc"]))
@click.option("--min-skills", type=click.IntRange(1, 5), default=None,
              help="Minimum skill moves stars (1-5)")
@click.option("--min-wf", type=click.IntRange(1, 5), default=None,
              help="Minimum weak foot stars (1-5)")
@click.option("--gender", default=None, type=click.Choice(["men", "women"]),
              help="Gender filter")
@click.option("--league", type=int, default=None, help="League ID")
@click.option("--nation", type=int, default=None, help="Nation ID")
@click.option("--club", type=int, default=None, help="Club ID")
@click.option("--year", "-y", default=26, show_default=True, help="Game year")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_players(
    name, position, rating_min, rating_max, version,
    min_price, max_price, platform, cheapest,
    sort, order, min_skills, min_wf, gender,
    league, nation, club, year, as_json,
):
    """List players from the FUTBIN database with optional filters.

    \b
    Examples:
      # Cheapest gold rare strikers
      cli-web-futbin players list --position ST --version gold_rare --cheapest
      # Top rated CAMs rated 85+
      cli-web-futbin players list --position CAM --rating-min 85 --sort overall --order desc
      # TOTY players under 500K
      cli-web-futbin players list --version toty --max-price 500000 --cheapest
      # 5-star skill players
      cli-web-futbin players list --min-skills 5 --sort overall --order desc
    """
    if cheapest:
        sort = "ps_price" if platform == "ps" else "pc_price"
        order = "asc"

    with FutbinClient() as client:
        try:
            results = client.list_players(
                name=name,
                min_price=min_price,
                max_price=max_price,
                sort=sort,
                order=order,
                year=year,
                position=position,
                rating_min=rating_min,
                rating_max=rating_max,
                version=version,
                platform=platform,
                min_skills=min_skills,
                min_wf=min_wf,
                gender=gender,
                league=league,
                nation=nation,
                club=club,
            )
        except Exception as e:
            print_error(str(e))
            return

    if as_json:
        print_json([p.to_dict() for p in results])
    else:
        if not results:
            click.echo("No players found.")
            return
        rows = [
            {
                "id": p.id,
                "name": p.name,
                "pos": p.position,
                "rating": p.rating,
                "ps_price": coins_display(p.ps_price),
                "xbox_price": coins_display(p.xbox_price),
            }
            for p in results
        ]
        print_table(rows, ["id", "name", "pos", "rating", "ps_price", "xbox_price"])
