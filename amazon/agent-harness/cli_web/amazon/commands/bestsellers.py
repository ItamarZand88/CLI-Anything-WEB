"""Best sellers commands for cli-web-amazon."""
import click
from ..core.client import AmazonClient
from ..utils.helpers import handle_errors, print_json
from ..utils.output import print_bestsellers

COMMON_CATEGORIES = [
    "electronics", "books", "toys-and-games", "music", "video-games",
    "home-garden", "clothing-shoes-jewelry", "sports-outdoors",
    "kitchen", "office-products", "pet-supplies", "beauty",
    "health-household", "automotive", "tools-home-improvement",
]


@click.command("bestsellers")
@click.argument("category", default="electronics")
@click.option("--page", type=int, default=1, show_default=True,
              help="Page number (each page has ~50 items).")
@click.option("--json", "use_json", is_flag=True, default=False,
              help="Output as JSON.")
def bestsellers(category, page, use_json):
    """Browse Amazon Best Sellers by category.

    CATEGORY defaults to 'electronics'. Other common values:
    books, toys-and-games, music, video-games, home-garden,
    clothing-shoes-jewelry, sports-outdoors, kitchen, beauty

    Examples:
      cli-web-amazon bestsellers
      cli-web-amazon bestsellers books
      cli-web-amazon bestsellers electronics --page 2
      cli-web-amazon bestsellers toys-and-games --json
    """
    with handle_errors(json_mode=use_json):
        with AmazonClient() as client:
            items = client.get_bestsellers(category=category, page=page)

        if use_json:
            print_json([i.to_dict() for i in items])
        else:
            if not items:
                click.echo(
                    f"No best sellers found for category '{category}'.\n"
                    f"Try one of: {', '.join(COMMON_CATEGORIES[:5])}"
                )
            else:
                print_bestsellers(items, category=category)
                click.echo(f"\n{len(items)} items. Use --page to see more.")
