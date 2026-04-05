"""Output formatting for cli-web-amazon."""
import json
from typing import Any

import click

try:
    from rich.console import Console
    from rich.table import Table
    from rich import box
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False


def print_json(data: Any) -> None:
    """Print data as pretty JSON."""
    click.echo(json.dumps(data, ensure_ascii=False, indent=2))


def print_search_results(results, title: str = "Search Results") -> None:
    """Print search results as a formatted table."""
    if not results:
        click.echo("No results found.")
        return

    if _RICH_AVAILABLE:
        console = Console()
        table = Table(title=title, box=box.ROUNDED, show_header=True)
        table.add_column("ASIN", style="cyan", no_wrap=True, width=12)
        table.add_column("Title", style="white", max_width=50)
        table.add_column("Price", style="green", no_wrap=True, width=12)
        table.add_column("Rating", style="yellow", no_wrap=True, width=12)

        for r in results:
            table.add_row(
                r.asin,
                r.title[:50] if r.title else "-",
                r.price or "-",
                r.rating[:15] if r.rating else "-",
            )
        console.print(table)
    else:
        click.echo(f"\n{title}")
        click.echo("-" * 80)
        click.echo(f"{'ASIN':<12} {'Price':<12} {'Rating':<15} Title")
        click.echo("-" * 80)
        for r in results:
            click.echo(
                f"{r.asin:<12} {(r.price or '-'):<12} {(r.rating[:14] if r.rating else '-'):<15} "
                f"{r.title[:50] if r.title else '-'}"
            )


def print_product(product) -> None:
    """Print product details."""
    if _RICH_AVAILABLE:
        console = Console()
        console.print(f"\n[bold cyan]{product.asin}[/] — [bold]{product.title[:80]}[/]")
        if product.price:
            console.print(f"  [green]Price:[/]     {product.price}")
        if product.rating:
            console.print(f"  [yellow]Rating:[/]    {product.rating}")
        if product.review_count:
            console.print(f"  [dim]Reviews:[/]   {product.review_count}")
        if product.brand:
            console.print(f"  [dim]Brand:[/]     {product.brand}")
        if product.url:
            console.print(f"  [dim]URL:[/]       {product.url}")
    else:
        click.echo(f"\nASIN:    {product.asin}")
        click.echo(f"Title:   {product.title[:80]}")
        if product.price:
            click.echo(f"Price:   {product.price}")
        if product.rating:
            click.echo(f"Rating:  {product.rating}")
        if product.review_count:
            click.echo(f"Reviews: {product.review_count}")
        if product.brand:
            click.echo(f"Brand:   {product.brand}")
        if product.url:
            click.echo(f"URL:     {product.url}")


def print_bestsellers(items, category: str = "") -> None:
    """Print best sellers table."""
    if not items:
        click.echo("No best sellers found.")
        return

    title = f"Best Sellers — {category}" if category else "Best Sellers"

    if _RICH_AVAILABLE:
        console = Console()
        table = Table(title=title, box=box.ROUNDED)
        table.add_column("Rank", style="bold yellow", width=6)
        table.add_column("ASIN", style="cyan", width=12)
        table.add_column("Price", style="green", width=12)
        table.add_column("Title", style="white", max_width=50)

        for item in items:
            table.add_row(
                f"#{item.rank}",
                item.asin,
                item.price or "-",
                item.title[:50] if item.title else "-",
            )
        console.print(table)
    else:
        click.echo(f"\n{title}")
        click.echo("-" * 80)
        click.echo(f"{'Rank':<6} {'ASIN':<12} {'Price':<12} Title")
        click.echo("-" * 80)
        for item in items:
            click.echo(
                f"#{item.rank:<5} {item.asin:<12} {(item.price or '-'):<12} "
                f"{item.title[:40] if item.title else '-'}"
            )


def print_suggestions(suggestions) -> None:
    """Print autocomplete suggestions."""
    if not suggestions:
        click.echo("No suggestions found.")
        return

    for s in suggestions:
        click.echo(f"  {s.value}")


