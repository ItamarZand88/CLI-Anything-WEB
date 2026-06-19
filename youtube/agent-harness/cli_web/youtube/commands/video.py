"""Video command for cli-web-youtube."""

from __future__ import annotations

import click

from ..core.client import YouTubeClient
from ..utils.helpers import (
    extract_video_id,
    handle_errors,
    print_json,
    resolve_json_mode,
)
from ..utils.output import print_video_detail


@click.group("video")
def video_group():
    """Get video details."""


@video_group.command("get")
@click.argument("video_id")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def video_get(video_id, use_json):
    """Get details for a specific video.

    VIDEO_ID can be the 11-character ID or a full YouTube URL.

    Example: video get dQw4w9WgXcQ
    """
    video_id = extract_video_id(video_id)
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = YouTubeClient()
        result = client.video_detail(video_id)
        if use_json:
            print_json(result)
        else:
            print_video_detail(result)
