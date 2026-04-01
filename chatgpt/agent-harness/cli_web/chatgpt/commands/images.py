"""Image browsing and download commands."""

from __future__ import annotations

from pathlib import Path

import click

from ..core.client import ChatGPTClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode, truncate


@click.group("images")
def images_group():
    """Browse and download generated images."""


@images_group.command("list")
@click.option("--limit", "-n", default=10, help="Number of images to show.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def list_images(ctx, limit: int, json_mode: bool) -> None:
    """List recently generated images."""
    json_mode = resolve_json_mode(json_mode)

    with handle_errors(json_mode=json_mode):
        with ChatGPTClient() as client:
            data = client.list_recent_images(limit=limit)

            if json_mode:
                print_json({"success": True, "data": data})
                return

            items = data.get("items", [])
            if not items:
                click.echo("No recent images found.")
                return

            click.echo(f"{'Title':<50} {'Size':<12} {'ID'}")
            click.echo("-" * 100)
            for img in items:
                title = truncate(img.get("title", "Untitled"), 48)
                w = img.get("width", "?")
                h = img.get("height", "?")
                size = f"{w}x{h}"
                iid = img.get("id", "")
                click.echo(f"{title:<50} {size:<12} {iid}")


@images_group.command("download")
@click.argument("file_id")
@click.option("--conversation", "-c", required=True, help="Conversation ID containing the image.")
@click.option("--output", "-o", default=None, type=click.Path(), help="Output file path.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def download_image(ctx, file_id: str, conversation: str, output: str | None, json_mode: bool) -> None:
    """Download a generated image by file ID."""
    json_mode = resolve_json_mode(json_mode)

    with handle_errors(json_mode=json_mode):
        with ChatGPTClient() as client:
            dl_info = client.get_file_download_url(file_id, conversation)
            download_url = dl_info.get("download_url")
            file_name = dl_info.get("file_name", "image.png")

            if not download_url:
                click.echo("No download URL available.", err=True)
                return

            img_bytes = client.download_file(download_url)

            if not output:
                # Use file_name from API, extract just the filename part
                output = Path(file_name).name if file_name else f"{file_id}.png"

            with open(output, "wb") as f:
                f.write(img_bytes)

            if json_mode:
                print_json({
                    "success": True,
                    "data": {
                        "file_id": file_id,
                        "saved_to": output,
                        "size_bytes": len(img_bytes),
                    },
                })
            else:
                click.echo(f"Image saved to {output} ({len(img_bytes)} bytes)")


@images_group.command("styles")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def list_styles(ctx, json_mode: bool) -> None:
    """List available image styles."""
    json_mode = resolve_json_mode(json_mode)

    with handle_errors(json_mode=json_mode):
        with ChatGPTClient() as client:
            data = client.get_image_styles()

            if json_mode:
                print_json({"success": True, "data": data})
                return

            styles = data.get("styles", [])
            if not styles:
                click.echo("No styles available.")
                return

            click.echo(f"{'ID':<40} {'Title'}")
            click.echo("-" * 70)
            for s in styles:
                sid = s.get("id", "?")
                title = s.get("title", "?")
                click.echo(f"{sid:<40} {title}")
