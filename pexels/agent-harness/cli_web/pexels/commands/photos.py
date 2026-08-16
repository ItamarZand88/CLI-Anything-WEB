"""Photos commands for cli-web-pexels."""

import os

import click

from ..core.client import PexelsClient
from ..core.exceptions import NotFoundError
from ..utils.helpers import handle_errors, sanitize_filename
from ..utils.output import (
    print_json,
    print_pagination,
    print_photo_detail,
    print_photos_table,
)


@click.group("photos")
@click.pass_context
def photos(ctx):
    """Browse and download Pexels photos."""
    pass


@photos.command()
@click.argument("query")
@click.option(
    "--orientation",
    type=click.Choice(["landscape", "portrait", "square"]),
    default=None,
    help="Filter by orientation.",
)
@click.option(
    "--size",
    type=click.Choice(["large", "medium", "small"]),
    default=None,
    help="Filter by minimum size.",
)
@click.option("--color", default=None, help="Filter by color (hex or named color).")
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def search(ctx, query, orientation, size, color, page, json_mode):
    """Search photos by keyword."""
    json_mode = json_mode or ctx.obj.get("json", False)
    with handle_errors(json_mode):
        client = PexelsClient()
        result = client.search_photos(
            query=query,
            orientation=orientation,
            size=size,
            color=color,
            page=page,
        )
        if json_mode:
            print_json(result)
        else:
            print_photos_table(result["data"])
            print_pagination(result.get("pagination", {}))


@photos.command("suggest")
@click.argument("query")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def suggest(ctx, query, json_mode):
    """Return Pexels autocomplete suggestions for a query."""
    json_mode = json_mode or ctx.obj.get("json", False)
    with handle_errors(json_mode):
        suggestions = PexelsClient().search_suggestions(query)
        if json_mode:
            from ..utils.output import print_json

            print_json(suggestions)
        else:
            for suggestion in suggestions:
                click.echo(suggestion)


@photos.command()
@click.argument("slug")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def get(ctx, slug, json_mode):
    """Get photo details by slug or ID."""
    json_mode = json_mode or ctx.obj.get("json", False)
    with handle_errors(json_mode):
        client = PexelsClient()
        photo = client.get_photo(slug)
        if json_mode:
            print_json(photo)
        else:
            print_photo_detail(photo)


@photos.command()
@click.argument("slug")
@click.option("--output", "-o", default=None, help="Output file path.")
@click.option(
    "--size",
    type=click.Choice(["small", "medium", "large", "original"]),
    default="original",
    help="Download size.",
)
@click.pass_context
def download(ctx, slug, output, size):
    """Download a photo by slug or ID."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        client = PexelsClient()
        photo = client.get_photo(slug)

        image = photo.get("image", {})
        size_map = {
            "original": "download",
            "large": "large",
            "medium": "medium",
            "small": "small",
        }
        url = image.get(size_map[size]) or image.get("download") or image.get("large")
        if not url:
            raise NotFoundError("No download URL available")

        if output is None:
            title = photo.get("title") or photo.get("alt") or "photo"
            ext = os.path.splitext(url.split("?")[0])[1] or ".jpeg"
            output = sanitize_filename(title) + ext

        client.download_file(url, output)

        if json_mode:
            print_json({"downloaded": True, "path": output, "size": size})
        else:
            click.echo(f"Downloaded: {output}")
