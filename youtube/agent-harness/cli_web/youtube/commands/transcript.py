"""Transcript commands for cli-web-youtube."""

from __future__ import annotations

import click

from ..core.client import YouTubeClient
from ..utils.helpers import (
    extract_video_id,
    handle_errors,
    print_json,
    resolve_json_mode,
)
from ..utils.output import print_transcript, print_transcript_list


@click.group("transcript")
def transcript_group():
    """Fetch video transcripts and captions."""


@transcript_group.command("get")
@click.argument("video")
@click.option(
    "--lang",
    "-l",
    "languages",
    multiple=True,
    help="Preferred language code(s), in priority order (e.g. -l en -l es).",
)
@click.option(
    "--translate",
    "-t",
    default=None,
    help="Translate the transcript into this language code (e.g. -t en).",
)
@click.option("--text-only", is_flag=True, help="Output only the plain transcript text.")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def transcript_get(video, languages, translate, text_only, use_json):
    """Get the transcript for a video.

    VIDEO can be the 11-character ID or a full YouTube URL.

    Example: transcript get dQw4w9WgXcQ --text-only
    """
    video_id = extract_video_id(video)
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = YouTubeClient()
        result = client.transcript(video_id, languages=list(languages) or None, translate=translate)
        if use_json:
            print_json(result)
        elif text_only:
            click.echo(result["text"])
        else:
            print_transcript(result)


@transcript_group.command("list")
@click.argument("video")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def transcript_list(video, use_json):
    """List available transcript languages for a video.

    Example: transcript list dQw4w9WgXcQ
    """
    video_id = extract_video_id(video)
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = YouTubeClient()
        result = client.list_transcripts(video_id)
        if use_json:
            print_json(result)
        else:
            print_transcript_list(result)
