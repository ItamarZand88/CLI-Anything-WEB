"""Posts commands for cli-web-producthunt."""

import click

from ..core.client import ProductHuntClient
from ..utils.helpers import handle_errors
from ..utils.output import print_json, print_table


@click.group()
def posts():
    """Browse Product Hunt posts and leaderboard."""


@posts.command("list")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def list_posts(use_json):
    """List today's posts from the Product Hunt homepage."""
    with handle_errors(json_mode=use_json):
        client = ProductHuntClient()
        results = client.list_posts()

        if use_json:
            print_json(results)
        else:
            if not results:
                click.echo("No posts found.")
                return
            rows = []
            for p in results:
                d = p.to_dict()
                rows.append([
                    d.get("slug", ""),
                    d.get("name", ""),
                    str(d.get("votes_count", "")),
                    str(d.get("comments_count", "")),
                    d.get("tagline", "")[:60],
                ])
            print_table(rows, ["Slug", "Name", "Votes", "Comments", "Tagline"])


@posts.command("get")
@click.argument("slug")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def get_post(slug, use_json):
    """Get details for a specific product by slug."""
    with handle_errors(json_mode=use_json):
        client = ProductHuntClient()
        post = client.get_post(slug=slug)

        if use_json:
            print_json(post)
        else:
            d = post.to_dict()
            click.echo(f"Name:        {d.get('name', '')}")
            click.echo(f"Slug:        {d.get('slug', '')}")
            click.echo(f"Tagline:     {d.get('tagline', '')}")
            click.echo(f"Votes:       {d.get('votes_count', '')}")
            click.echo(f"Comments:    {d.get('comments_count', '')}")
            click.echo(f"URL:         {d.get('url', '')}")
            if d.get("description"):
                click.echo(f"Description: {d['description']}")
            if d.get("topics"):
                click.echo(f"Topics:      {', '.join(d['topics'])}")


@posts.command("leaderboard")
@click.option(
    "--period",
    type=click.Choice(["daily", "weekly", "monthly"], case_sensitive=False),
    default="daily",
    help="Leaderboard period (default: daily).",
)
@click.option("--date", "date_str", default=None, help="Date as YYYY-MM-DD (optional).")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def leaderboard(period, date_str, use_json):
    """Show the Product Hunt leaderboard."""
    year = month = day = None
    if date_str:
        parts = date_str.split("-")
        if len(parts) >= 1:
            year = int(parts[0])
        if len(parts) >= 2:
            month = int(parts[1])
        if len(parts) >= 3:
            day = int(parts[2])

    with handle_errors(json_mode=use_json):
        client = ProductHuntClient()
        results = client.list_leaderboard(
            period=period.lower(), year=year, month=month, day=day
        )

        if use_json:
            print_json(results)
        else:
            if not results:
                click.echo("No posts found on leaderboard.")
                return
            rows = []
            for i, p in enumerate(results, 1):
                d = p.to_dict()
                rank = d.get("rank") or i
                rows.append([
                    str(rank),
                    d.get("name", ""),
                    str(d.get("votes_count", "")),
                    str(d.get("comments_count", "")),
                    d.get("tagline", "")[:50],
                ])
            print_table(rows, ["#", "Name", "Votes", "Comments", "Tagline"])
