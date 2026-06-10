"""Video commands for cli-web-pexels."""

from __future__ import annotations

from pathlib import Path

import click

from ..core.client import PexelsClient
from ..core.exceptions import NotFoundError
from ..utils.helpers import handle_errors, sanitize_filename
from ..utils.output import print_json, print_pagination, print_video_detail, print_videos_table

QUALITY_ORDER = {"sd": 0, "hd": 1, "uhd": 2}


@click.group("videos")
def videos():
    """Search, view, and download videos."""


@videos.command("search")
@click.argument("query")
@click.option(
    "--orientation",
    type=click.Choice(["landscape", "portrait", "square"]),
    help="Filter by orientation.",
)
@click.option("--page", type=int, default=1, help="Page number.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def search(ctx, query, orientation, page, json_mode):
    """Search videos by keyword."""
    json_mode = json_mode or ctx.obj.get("json", False)
    with handle_errors(json_mode):
        client = PexelsClient()
        result = client.search_videos(query, page=page, orientation=orientation)
        videos_list = result.get("data", [])
        pagination = result.get("pagination", {})

        if json_mode:
            print_json(
                {
                    "query": query,
                    "page": page,
                    "total_results": pagination.get("total_results", 0),
                    "total_pages": pagination.get("total_pages", 0),
                    "results": videos_list,
                }
            )
        else:
            total = pagination.get("total_results", 0)
            click.echo(f"\n  Found {total:,} videos for '{query}'")
            print_videos_table(videos_list)
            print_pagination(pagination)


@videos.command("get")
@click.argument("slug")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def get(ctx, slug, json_mode):
    """Get video details by slug or ID (e.g., 'long-narrow-road-856479' or '856479')."""
    json_mode = json_mode or ctx.obj.get("json", False)
    with handle_errors(json_mode):
        client = PexelsClient()
        video = client.get_video(slug)

        if json_mode:
            print_json(video)
        else:
            print_video_detail(video)


@videos.command("download")
@click.argument("slug")
@click.option(
    "--quality",
    type=click.Choice(["sd", "hd", "uhd"]),
    default="hd",
    help="Video quality (default: hd).",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path.")
@click.pass_context
def download(ctx, slug, quality, output):
    """Download a video by slug or ID."""
    json_mode = ctx.obj.get("json", False)
    with handle_errors(json_mode):
        client = PexelsClient()
        video = client.get_video(slug)

        video_files = video.get("video_files", [])
        if not video_files:
            raise NotFoundError(f"No video files available for '{slug}'")

        # Find best matching file by quality
        best = _select_video_file(video_files, quality)
        if not best:
            raise NotFoundError(f"No downloadable video file found for '{slug}'")

        download_url = best.get("link")
        if not download_url:
            raise NotFoundError(f"No download link for selected quality ({best.get('quality')})")

        # Determine output filename
        if not output:
            title = video.get("title") or slug
            safe_name = sanitize_filename(title)
            output = f"{safe_name}.mp4"

        out_path = Path(output)
        client.download_file(download_url, str(out_path))

        file_size = out_path.stat().st_size
        if json_mode:
            print_json(
                {
                    "video_id": video.get("id"),
                    "slug": slug,
                    "quality": best.get("quality"),
                    "resolution": f"{best.get('width')}x{best.get('height')}",
                    "file": str(out_path),
                    "bytes": file_size,
                }
            )
        else:
            click.echo(f"  Downloaded: {out_path} ({file_size:,} bytes)")
            click.echo(
                f"  Quality: {best.get('quality')} "
                f"({best.get('width')}x{best.get('height')}, "
                f"{best.get('fps', '?')}fps)"
            )
            click.echo(f"  Video: {video.get('title') or slug}")


def _select_video_file(video_files: list[dict], target_quality: str) -> dict | None:
    """Select the best video file matching the requested quality.

    Picks the highest-resolution file at the target quality level.
    Falls back to the closest available quality if no exact match.
    """
    target_rank = QUALITY_ORDER.get(target_quality, 1)

    # Filter exact matches and pick highest resolution
    exact = [f for f in video_files if f.get("quality") == target_quality]
    if exact:
        return max(exact, key=lambda f: f.get("width", 0) * f.get("height", 0))

    # No exact match — find closest quality
    # Sort candidates by distance to target rank, then by resolution descending
    candidates = [f for f in video_files if f.get("link")]
    if not candidates:
        return None

    def sort_key(f):
        f_rank = QUALITY_ORDER.get(f.get("quality", ""), 1)
        distance = abs(f_rank - target_rank)
        resolution = f.get("width", 0) * f.get("height", 0)
        return (distance, -resolution)

    candidates.sort(key=sort_key)
    return candidates[0]
