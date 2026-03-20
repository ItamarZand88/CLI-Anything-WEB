"""Output formatting for cli-web-unsplash."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

console = Console()


def photo_table(photos: list[dict], title: str = "Photos") -> None:
    """Print a Rich table of photo summaries."""
    table = Table(title=title, show_lines=False)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Description", max_width=40)
    table.add_column("Size", justify="right")
    table.add_column("Likes", justify="right", style="red")
    table.add_column("Author", style="green")

    for p in photos:
        table.add_row(
            p.get("id", ""),
            _trunc(p.get("description", ""), 40),
            f"{p.get('width', 0)}x{p.get('height', 0)}",
            str(p.get("likes", 0)),
            p.get("author", ""),
        )
    console.print(table)


def user_table(users: list[dict], title: str = "Users") -> None:
    """Print a Rich table of user summaries."""
    table = Table(title=title, show_lines=False)
    table.add_column("Username", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Photos", justify="right")
    table.add_column("Likes", justify="right", style="red")
    table.add_column("Location")

    for u in users:
        table.add_row(
            u.get("username", ""),
            u.get("name", ""),
            str(u.get("total_photos", 0)),
            str(u.get("total_likes", 0)),
            _trunc(u.get("location", ""), 25),
        )
    console.print(table)


def collection_table(collections: list[dict], title: str = "Collections") -> None:
    """Print a Rich table of collection summaries."""
    table = Table(title=title, show_lines=False)
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="green", max_width=35)
    table.add_column("Photos", justify="right")
    table.add_column("Author")

    for c in collections:
        table.add_row(
            str(c.get("id", "")),
            _trunc(c.get("title", ""), 35),
            str(c.get("total_photos", 0)),
            c.get("author", ""),
        )
    console.print(table)


def topic_table(topics: list[dict], title: str = "Topics") -> None:
    """Print a Rich table of topic summaries."""
    table = Table(title=title, show_lines=False)
    table.add_column("Slug", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Photos", justify="right")
    table.add_column("Featured", justify="center")

    for t in topics:
        table.add_row(
            t.get("slug", ""),
            t.get("title", ""),
            str(t.get("total_photos", 0)),
            "Yes" if t.get("featured") else "",
        )
    console.print(table)


def photo_detail_display(detail: dict) -> None:
    """Print detailed photo information in human-readable format."""
    click.echo(f"\n  Photo: {detail.get('id')}")
    click.echo(f"  Description: {detail.get('description') or 'N/A'}")
    click.echo(f"  Size: {detail.get('width')}x{detail.get('height')}")
    click.echo(f"  Color: {detail.get('color')}")
    click.echo(f"  Likes: {detail.get('likes')}  Views: {detail.get('views')}  Downloads: {detail.get('downloads')}")
    author = detail.get("author", {})
    click.echo(f"  Author: {author.get('name')} (@{author.get('username')})")

    exif = detail.get("exif", {})
    if exif.get("camera"):
        click.echo(f"  Camera: {exif['camera']}")
        parts = []
        if exif.get("aperture"):
            parts.append(f"f/{exif['aperture']}")
        if exif.get("exposure"):
            parts.append(f"{exif['exposure']}s")
        if exif.get("focal_length"):
            parts.append(f"{exif['focal_length']}mm")
        if exif.get("iso"):
            parts.append(f"ISO {exif['iso']}")
        if parts:
            click.echo(f"  Settings: {', '.join(parts)}")

    loc = detail.get("location", {})
    if loc.get("name"):
        click.echo(f"  Location: {loc['name']}")

    tags = detail.get("tags", [])
    if tags:
        click.echo(f"  Tags: {', '.join(tags[:10])}")

    click.echo(f"  Link: {detail.get('link')}")
    click.echo()


def _trunc(text: str | None, length: int) -> str:
    if not text:
        return ""
    return text[:length] + "..." if len(text) > length else text
