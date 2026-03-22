"""Photo commands for cli-web-unsplash."""

from __future__ import annotations

from pathlib import Path

import click
from curl_cffi import requests as curl_requests

from ..core.client import UnsplashClient
from ..core.models import format_photo_detail, format_photo_summary
from ..utils.helpers import handle_errors, print_json
from ..utils.output import photo_detail_display, photo_table


@click.group("photos")
def photos():
    """Search, view, and explore photos."""


@photos.command("search")
@click.argument("query")
@click.option("--orientation", type=click.Choice(["landscape", "portrait", "squarish"]), help="Filter by orientation.")
@click.option("--color", help="Filter by color (e.g., red, blue, green, black_and_white).")
@click.option("--order-by", type=click.Choice(["relevant", "latest"]), default="relevant", help="Sort order.")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--per-page", type=int, default=20, help="Results per page (max 30).")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def search(query, orientation, color, order_by, page, per_page, use_json):
    """Search photos by keyword."""
    with handle_errors(json_mode=use_json):
        client = UnsplashClient()
        data = client.search_photos(
            query, page=page, per_page=per_page,
            orientation=orientation, color=color, order_by=order_by,
        )
        results = [format_photo_summary(p) for p in data.get("results", [])]
        if use_json:
            print_json({"total": data.get("total", 0), "total_pages": data.get("total_pages", 0), "results": results})
        else:
            click.echo(f"Found {data.get('total', 0):,} photos for '{query}' (page {page})")
            photo_table(results, title=f"Search: {query}")


@photos.command("get")
@click.argument("photo_id")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def get(photo_id, use_json):
    """Get photo details by ID or slug."""
    with handle_errors(json_mode=use_json):
        client = UnsplashClient()
        photo = client.get_photo(photo_id)
        detail = format_photo_detail(photo)
        if use_json:
            print_json(detail)
        else:
            photo_detail_display(detail)


@photos.command("random")
@click.option("--query", help="Filter random photos by keyword.")
@click.option("--orientation", type=click.Choice(["landscape", "portrait", "squarish"]), help="Filter by orientation.")
@click.option("--count", type=int, default=1, help="Number of random photos (max 30).")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def random(query, orientation, count, use_json):
    """Get random photo(s)."""
    with handle_errors(json_mode=use_json):
        client = UnsplashClient()
        photos = client.get_random_photos(count=count, query=query, orientation=orientation)
        results = [format_photo_summary(p) for p in photos]
        if use_json:
            print_json(results)
        else:
            photo_table(results, title="Random Photos")


@photos.command("download")
@click.argument("photo_id")
@click.option("--size", type=click.Choice(["raw", "full", "regular", "small", "thumb"]), default="full", help="Image size.")
@click.option("--output", "-o", type=click.Path(), help="Output file path. Defaults to <photo_id>_<size>.jpg.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def download(photo_id, size, output, use_json):
    """Download a photo by ID."""
    with handle_errors(json_mode=use_json):
        client = UnsplashClient()
        photo = client.get_photo(photo_id)
        urls = photo.get("urls", {})
        url = urls.get(size)
        if not url:
            raise click.ClickException(f"No '{size}' URL available for photo {photo_id}")

        if not output:
            output = f"{photo.get('id', photo_id)}_{size}.jpg"

        out_path = Path(output)
        resp = curl_requests.get(url, impersonate="chrome131", timeout=60)
        if resp.status_code >= 400:
            raise click.ClickException(f"Download failed: HTTP {resp.status_code}")
        out_path.write_bytes(resp.content)

        file_size = out_path.stat().st_size
        if use_json:
            print_json({
                "photo_id": photo.get("id"),
                "size": size,
                "file": str(out_path),
                "bytes": file_size,
                "description": photo.get("alt_description") or photo.get("description") or "",
            })
        else:
            click.echo(f"  Downloaded: {out_path} ({file_size:,} bytes)")
            click.echo(f"  Photo: {photo.get('alt_description') or photo.get('description') or photo_id}")


@photos.command("stats")
@click.argument("photo_id")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def stats(photo_id, use_json):
    """Get photo statistics (views, downloads)."""
    with handle_errors(json_mode=use_json):
        client = UnsplashClient()
        data = client.get_photo_statistics(photo_id)
        if use_json:
            print_json(data)
        else:
            click.echo(f"\n  Photo: {data.get('id')}")
            click.echo(f"  Views: {data.get('views', {}).get('total', 0):,}")
            click.echo(f"  Downloads: {data.get('downloads', {}).get('total', 0):,}")
            click.echo()
