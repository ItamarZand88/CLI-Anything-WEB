"""Product commands for cli-web-amazon."""
import click
from ..core.client import AmazonClient
from ..utils.helpers import handle_errors, print_json
from ..utils.output import print_product


@click.group("product")
def product():
    """Amazon product operations."""
    pass


@product.command("get")
@click.argument("asin")
@click.option("--json", "use_json", is_flag=True, default=False,
              help="Output as JSON.")
def get_product(asin, use_json):
    """Get product details by ASIN.

    ASIN is Amazon's Standard Identification Number (e.g., B0GRZ78683).

    Examples:
      cli-web-amazon product get B0GRZ78683
      cli-web-amazon product get B087JWTWF9 --json
    """
    with handle_errors(json_mode=use_json):
        asin = asin.upper().strip()
        with AmazonClient() as client:
            p = client.get_product(asin)

        if use_json:
            print_json(p.to_dict())
        else:
            print_product(p)


