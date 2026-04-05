"""Search commands for cli-web-amazon."""
import click
from ..core.client import AmazonClient
from ..utils.helpers import handle_errors, print_json
from ..utils.output import print_search_results


@click.command("search")
@click.argument("query")
@click.option("--page", type=int, default=1, show_default=True,
              help="Page number of results.")
@click.option("--dept", "--department", "department", default=None,
              help="Department filter (e.g., 'electronics', 'books').")
@click.option("--json", "use_json", is_flag=True, default=False,
              help="Output as JSON.")
def search(query, page, department, use_json):
    """Search Amazon products by keyword.

    Returns product cards with ASIN, title, price, and rating.

    Examples:
      cli-web-amazon search laptop
      cli-web-amazon search "wireless headphones" --page 2
      cli-web-amazon search camera --dept electronics
    """
    with handle_errors(json_mode=use_json):
        with AmazonClient() as client:
            results = client.search(query, page=page, department=department)

        if use_json:
            print_json([r.to_dict() for r in results])
        else:
            if not results:
                click.echo(f"No results found for '{query}'.")
            else:
                title = f"Search: {query}"
                if page > 1:
                    title += f" (page {page})"
                print_search_results(results, title=title)
                click.echo(f"\n{len(results)} results. Use --page to see more.")
