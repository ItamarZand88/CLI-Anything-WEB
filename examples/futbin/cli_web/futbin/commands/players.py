"""Click command group for FUTBIN player operations."""

import click

from cli_web.futbin.core.auth import load_cookies
from cli_web.futbin.core.client import FutbinClient
from cli_web.futbin.utils.output import output_json, output_players_table


@click.group()
def players():
    """FUTBIN player operations."""
    pass


@players.command()
@click.option("--query", required=True, help="Search query string.")
@click.option("--year", default="26", help="Game year (default: 26).")
@click.pass_context
def search(ctx, query, year):
    """Search for players by name."""
    json_mode = ctx.obj.get("json", False)
    cookies = load_cookies()
    with FutbinClient(cookies=cookies) as client:
        results = client.search_players(query, year)
    if json_mode:
        output_json(results)
    else:
        output_players_table(results)


@players.command(name="list")
@click.option("--page", default=1, type=int, help="Page number.")
@click.option("--position", default=None, help="Position filter: GK,LB,CB,RB,CAM,CM,CDM,RM,LM,ST,RW,LW (comma-separated).")
@click.option("--sort", default="ps_price", help="Sort: ps_price, pc_price, Player_Rating, futbin_rating, name, popularity.")
@click.option("--order", default="desc", type=click.Choice(["asc", "desc"]), help="Sort order.")
@click.option("--version", default=None, help="Promo/version: TOTY, FUTBirthday, TOTW26, etc.")
@click.option("--league", default=None, help="League ID: 13=PL, 53=LaLiga, 31=SerieA, 19=Bundesliga, 16=Ligue1.")
@click.option("--nation", default=None, help="Nation ID: 52=Argentina, 14=Brazil, 18=France, 7=England, etc.")
@click.option("--club", default=None, help="Club ID (numeric).")
@click.option("--rating-min", default=None, type=int, help="Minimum overall rating.")
@click.option("--rating-max", default=None, type=int, help="Maximum overall rating.")
@click.option("--price-min", default=None, type=int, help="Minimum PS price (use 200+ to skip untradeables).")
@click.option("--price-max", default=None, type=int, help="Maximum PS price.")
@click.option("--accelerate", default=None, type=click.Choice(["explosive", "controlled", "lengthy", "c_explosive", "c_controlled", "c_lengthy"]), help="AcceleRATE type.")
@click.pass_context
def list_cmd(ctx, page, position, sort, order, version, league, nation, club, rating_min, rating_max, price_min, price_max, accelerate):
    """List players with optional filters.

    \b
    Examples:
      cli-web-futbin players list --rating-min 87 --rating-max 87 --price-min 200 --sort ps_price --order asc
      cli-web-futbin players list --league 13 --position ST --sort ps_price --order desc
      cli-web-futbin players list --nation 52 --accelerate explosive
    """
    json_mode = ctx.obj.get("json", False)
    cookies = load_cookies()
    with FutbinClient(cookies=cookies) as client:
        results = client.list_players(
            page=page,
            position=position,
            sort=sort,
            order=order,
            version=version,
            league=league,
            nation=nation,
            club=club,
            rating_min=rating_min,
            rating_max=rating_max,
            price_min=price_min,
            price_max=price_max,
            accelerate=accelerate,
        )
    if json_mode:
        output_json(results)
    else:
        output_players_table(results)


@players.command()
@click.option("--id", "player_id", required=True, type=int, help="Player ID.")
@click.pass_context
def get(ctx, player_id):
    """Get detailed info for a single player."""
    json_mode = ctx.obj.get("json", False)
    cookies = load_cookies()
    with FutbinClient(cookies=cookies) as client:
        result = client.get_player(player_id)
    if json_mode:
        output_json(result)
    else:
        output_players_table([result])


@players.command()
@click.option("--id", "player_id", required=True, type=int, help="Player ID.")
@click.option(
    "--platform",
    default="ps",
    type=click.Choice(["ps", "pc"], case_sensitive=False),
    help="Platform (default: ps).",
)
@click.pass_context
def prices(ctx, player_id, platform):
    """Get price history for a player."""
    json_mode = ctx.obj.get("json", False)
    cookies = load_cookies()
    with FutbinClient(cookies=cookies) as client:
        result = client.get_price_history(player_id, platform=platform)
    if json_mode:
        output_json(result)
    else:
        click.echo(f"Price history for {result.player_name} ({result.platform})")
        click.echo("-" * 40)
        for point in result.prices:
            click.echo(f"  {point.timestamp}  {point.price:,}")


@players.command()
@click.pass_context
def popular(ctx):
    """Get currently popular players."""
    json_mode = ctx.obj.get("json", False)
    cookies = load_cookies()
    with FutbinClient(cookies=cookies) as client:
        results = client.get_popular_players()
    if json_mode:
        output_json(results)
    else:
        output_players_table(results)


@players.command()
@click.pass_context
def latest(ctx):
    """Get latest added players."""
    json_mode = ctx.obj.get("json", False)
    cookies = load_cookies()
    with FutbinClient(cookies=cookies) as client:
        results = client.get_latest_players()
    if json_mode:
        output_json(results)
    else:
        output_players_table(results)
