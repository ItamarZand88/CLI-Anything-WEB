"""Output formatting for cli-web-pexels."""

import json

import click


def print_json(data):
    """Print data as formatted JSON."""
    click.echo(json.dumps(data, indent=2, default=str, ensure_ascii=False))


def print_error_json(exc):
    """Print an error as JSON."""
    from ..core.exceptions import error_code_for

    click.echo(json.dumps({"error": True, "code": error_code_for(exc), "message": str(exc)}))


def print_photos_table(photos: list[dict]):
    """Print photos in a formatted table."""
    if not photos:
        click.echo("  No photos found.")
        return

    click.echo(f"  {'ID':<12} {'Title':<35} {'Size':<12} {'Photographer':<20}")
    click.echo(f"  {'─' * 12} {'─' * 35} {'─' * 12} {'─' * 20}")
    for p in photos:
        title = (p.get("title") or "Untitled")[:34]
        size = f"{p.get('width', '?')}x{p.get('height', '?')}"
        photographer = (p.get("photographer") or "Unknown")[:19]
        click.echo(f"  {p.get('id', ''):<12} {title:<35} {size:<12} {photographer:<20}")


def print_videos_table(videos: list[dict]):
    """Print videos in a formatted table."""
    if not videos:
        click.echo("  No videos found.")
        return

    click.echo(f"  {'ID':<12} {'Title':<35} {'Size':<12} {'Photographer':<20}")
    click.echo(f"  {'─' * 12} {'─' * 35} {'─' * 12} {'─' * 20}")
    for v in videos:
        title = (v.get("title") or "Untitled")[:34]
        size = f"{v.get('width', '?')}x{v.get('height', '?')}"
        photographer = (v.get("photographer") or "Unknown")[:19]
        click.echo(f"  {v.get('id', ''):<12} {title:<35} {size:<12} {photographer:<20}")


def print_photo_detail(photo: dict):
    """Print photo detail in human-readable format."""
    click.echo(f"\n  Photo: {photo.get('title', 'Untitled')}")
    click.echo(f"  {'─' * 50}")
    click.echo(f"  ID:           {photo.get('id')}")
    click.echo(f"  Size:         {photo.get('width')}x{photo.get('height')}")
    click.echo(f"  License:      {photo.get('license')}")
    click.echo(f"  Photographer: {photo.get('photographer')}")
    if photo.get("description"):
        click.echo(f"  Description:  {photo['description'][:80]}")
    if photo.get("tags"):
        click.echo(f"  Tags:         {', '.join(photo['tags'][:8])}")
    if photo.get("colors"):
        click.echo(f"  Colors:       {', '.join(photo['colors'][:5])}")
    if photo.get("image", {}).get("download"):
        click.echo(f"  Download:     {photo['image']['download']}")
    click.echo()


def print_video_detail(video: dict):
    """Print video detail in human-readable format."""
    click.echo(f"\n  Video: {video.get('title', 'Untitled')}")
    click.echo(f"  {'─' * 50}")
    click.echo(f"  ID:           {video.get('id')}")
    click.echo(f"  Size:         {video.get('width')}x{video.get('height')}")
    click.echo(f"  License:      {video.get('license')}")
    click.echo(f"  Photographer: {video.get('photographer')}")
    if video.get("description"):
        click.echo(f"  Description:  {video['description'][:80]}")
    if video.get("video_files"):
        click.echo("  Quality options:")
        for f in video["video_files"]:
            click.echo(f"    {f['quality']:>3} {f['width']}x{f['height']} {f.get('fps', '?')}fps")
    click.echo()


def print_user_detail(user: dict):
    """Print user profile in human-readable format."""
    name = f"{user.get('first_name', '')} {user.get('last_name', '') or ''}".strip()
    click.echo(f"\n  User: {name} (@{user.get('username')})")
    click.echo(f"  {'─' * 50}")
    if user.get("location"):
        click.echo(f"  Location:     {user['location']}")
    click.echo(f"  Photos:       {user.get('photos_count', 0)}")
    click.echo(f"  Total media:  {user.get('media_count', 0)}")
    click.echo(f"  Followers:    {user.get('followers_count', 0)}")
    if user.get("hero"):
        click.echo("  Hero:         Yes")
    click.echo(f"  URL:          {user.get('url')}")
    click.echo()


def print_collection_detail(collection: dict):
    """Print collection detail in human-readable format."""
    click.echo(f"\n  Collection: {collection.get('title', 'Untitled')}")
    click.echo(f"  {'─' * 50}")
    click.echo(f"  ID:           {collection.get('id')}")
    click.echo(f"  Photos:       {collection.get('photos_count', 0)}")
    click.echo(f"  Videos:       {collection.get('videos_count', 0)}")
    click.echo(f"  Total media:  {collection.get('media_count', 0)}")
    if collection.get("description"):
        click.echo(f"  Description:  {collection['description'][:80]}")
    click.echo()


def print_collections_table(collections: list[dict]):
    """Print collections in a table."""
    if not collections:
        click.echo("  No collections found.")
        return

    click.echo(f"  {'Title':<30} {'Photos':<10} {'Videos':<10} {'Total':<10}")
    click.echo(f"  {'─' * 30} {'─' * 10} {'─' * 10} {'─' * 10}")
    for c in collections:
        title = (c.get("title") or "Untitled")[:29]
        click.echo(
            f"  {title:<30} {c.get('photos_count', 0):<10} "
            f"{c.get('videos_count', 0):<10} {c.get('media_count', 0):<10}"
        )


def print_pagination(pagination: dict):
    """Print pagination info."""
    if not pagination:
        return
    current = pagination.get("current_page", 1)
    total = pagination.get("total_pages", 1)
    results = pagination.get("total_results", 0)
    if total > 1:
        click.echo(f"\n  Page {current}/{total} ({results:,} total results)")
