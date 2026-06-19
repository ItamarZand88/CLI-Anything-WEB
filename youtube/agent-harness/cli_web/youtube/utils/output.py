"""Output formatting for cli-web-youtube."""

from __future__ import annotations

import click


def print_videos_table(videos: list[dict]) -> None:
    """Print videos as a formatted table."""
    for i, v in enumerate(videos, 1):
        duration = v.get("duration", "")
        views = v.get("views", "")
        channel = v.get("channel", "")
        title = v.get("title", "")[:70]
        vid = v.get("id", "")

        click.echo(f"  {i:>2}. {title}")
        click.echo(f"      {channel} | {views} | {duration} | {vid}")
        click.echo()


def print_video_detail(video: dict) -> None:
    """Print detailed video info."""
    click.echo(f"\n  {video.get('title', '')}")
    click.echo(f"  {'=' * 60}")
    click.echo(f"  Channel:   {video.get('channel', '')}")
    click.echo(f"  Views:     {video.get('views', 0):,}")
    click.echo(f"  Duration:  {_format_duration(video.get('duration_seconds', 0))}")
    click.echo(f"  Published: {video.get('publish_date', '')}")
    click.echo(f"  Category:  {video.get('category', '')}")
    click.echo(f"  URL:       {video.get('url', '')}")
    if video.get("keywords"):
        click.echo(f"  Keywords:  {', '.join(video['keywords'][:10])}")
    if video.get("description"):
        desc = video["description"][:300]
        click.echo(f"\n  {desc}{'...' if len(video['description']) > 300 else ''}")
    click.echo()


def print_channel_detail(channel: dict) -> None:
    """Print channel info."""
    click.echo(f"\n  {channel.get('title', '')}")
    click.echo(f"  {'=' * 60}")
    click.echo(f"  Subscribers: {channel.get('subscriber_count', '')}")
    if channel.get("video_count"):
        click.echo(f"  Videos:      {channel['video_count']}")
    if channel.get("description"):
        click.echo(f"  About:       {channel['description'][:200]}")
    click.echo(f"  URL:         {channel.get('url', '')}")

    if channel.get("recent_videos"):
        click.echo(f"\n  Recent Videos ({len(channel['recent_videos'])})")
        click.echo(f"  {'-' * 40}")
        for v in channel["recent_videos"][:5]:
            click.echo(f"    {v.get('title', '')[:60]}")
            click.echo(f"    {v.get('views', '')} | {v.get('duration', '')} | {v.get('id', '')}")
            click.echo()


def print_transcript(data: dict) -> None:
    """Print a transcript as timestamped lines."""
    click.echo(f"\n  {data.get('title', '')}")
    lang = data.get("language_code", "")
    kind = data.get("kind", "")
    tag = f"{lang} ({kind})" + (" [translated]" if data.get("is_translated") else "")
    click.echo(f"  Transcript: {tag} — {data.get('segment_count', 0)} segments")
    click.echo(f"  {'=' * 60}")
    for seg in data.get("segments", []):
        click.echo(f"  [{_timestamp(seg['start'])}] {seg['text']}")
    click.echo()


def print_transcript_list(data: dict) -> None:
    """Print available transcript tracks for a video."""
    transcripts = data.get("transcripts", [])
    click.echo(f"\n  {data.get('title', '')}")
    click.echo(f"  Available transcripts ({len(transcripts)})")
    click.echo(f"  {'=' * 60}")
    for t in transcripts:
        flags = [t.get("kind", "")]
        if t.get("translatable"):
            flags.append("translatable")
        click.echo(f"  {t.get('language_code', ''):<8} {t.get('name', '')}  ({', '.join(flags)})")
    click.echo()


def _timestamp(seconds: float) -> str:
    """Format seconds as M:SS or H:MM:SS."""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _format_duration(seconds: int) -> str:
    """Format seconds into H:MM:SS or M:SS."""
    if seconds <= 0:
        return "Live"
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
