import json
import os
import sys

import click
import httpx

from cli_web.notebooklm.core.client import NotebookLMClient
from cli_web.notebooklm.core.models import parse_artifact, parse_artifact_content
from cli_web.notebooklm.utils.output import output_json, output_table


@click.group()
def artifacts():
    """NotebookLM studio artifacts."""


@artifacts.command("list")
@click.option("--notebook-id", required=True, help="Notebook ID to list artifacts for.")
@click.pass_context
def list_artifacts(ctx, notebook_id):
    """List studio artifacts for a notebook."""
    json_mode = ctx.obj["json"]
    client = NotebookLMClient()
    try:
        result = client.list_artifacts(notebook_id)
        items = [parse_artifact(raw) for raw in result[0]]
    except Exception as e:
        raise click.ClickException(str(e))

    if json_mode:
        output_json(items)
    else:
        headers = ["ID", "Type", "Title", "Created"]
        rows = [[a["id"], a["type"], a["title"], a["created"]] for a in items]
        output_table(headers, rows)


ARTIFACT_TYPE_MAP = {
    "audio": 1,
    "video": 3,
    "quiz": 4,
    "presentation": 8,
}


@artifacts.command("create")
@click.option("--notebook-id", required=True, help="Notebook ID.")
@click.option(
    "--type",
    "artifact_type",
    required=True,
    type=click.Choice(["audio", "video", "quiz", "presentation"]),
    help="Type of artifact to create.",
)
@click.pass_context
def create_artifact(ctx, notebook_id, artifact_type):
    """Generate a studio artifact."""
    json_mode = ctx.obj.get("json", False)
    type_code = ARTIFACT_TYPE_MAP[artifact_type]
    try:
        client = NotebookLMClient()
        raw_sources = client.list_sources(notebook_id)
        source_ids = [s[0][0] for s in raw_sources]

        result = client.create_artifact(notebook_id, source_ids, type_code)
        artifact_id = result[0][0]
        title = result[0][1]

        if json_mode:
            output_json({
                "id": artifact_id,
                "title": title,
                "type": artifact_type,
                "message": "Artifact creation started",
            })
        else:
            click.echo(f"Started creating {artifact_type}: {title} (id: {artifact_id})")
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@artifacts.command("get")
@click.option("--notebook-id", required=True, help="Notebook ID.")
@click.option("--id", "artifact_id", required=True, help="Artifact ID.")
@click.pass_context
def get_artifact(ctx, notebook_id, artifact_id):
    """Get details for a specific artifact."""
    json_mode = ctx.obj.get("json", False)
    try:
        client = NotebookLMClient()
        raw = client.get_artifact(notebook_id, artifact_id)
        if not raw:
            raise click.ClickException("Artifact not found")

        parsed = parse_artifact_content(raw)

        if json_mode:
            output_json(parsed)
        else:
            click.echo(f"Title: {parsed.get('title', '(untitled)')}")
            click.echo(f"Type:  {parsed.get('type', 'Unknown')}")
            click.echo(f"ID:    {parsed.get('id', '')}")
            click.echo()

            type_code = parsed.get("type_code")

            if type_code in (1, 3):  # Audio or Video
                url = parsed.get("media_url") or "(not available)"
                dur = parsed.get("duration_seconds")
                fmts = parsed.get("formats", [])
                click.echo(f"Media URL: {url}")
                if dur is not None:
                    minutes = int(dur // 60)
                    seconds = dur % 60
                    click.echo(f"Duration:  {minutes}m {seconds:.0f}s")
                click.echo(f"Formats:   {len(fmts)} available")

            elif type_code == 8:  # Presentation
                slides = parsed.get("slides", [])
                click.echo(f"Slides: {len(slides)}")
                click.echo()
                for i, slide in enumerate(slides, 1):
                    desc = slide.get("description", "")
                    if desc and len(desc) > 80:
                        desc = desc[:77] + "..."
                    click.echo(f"  Slide {i}: {desc}")
                    click.echo(f"    Image: {slide.get('image_url', '(none)')}")

            elif type_code == 4:  # Quiz
                config = parsed.get("quiz_config", {})
                click.echo(f"Quiz config: {config}")

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


@artifacts.command("download")
@click.option("--notebook-id", required=True, help="Notebook ID.")
@click.option("--id", "artifact_id", required=True, help="Artifact ID.")
@click.option("--output", "output_path", default=None, help="Output file path (auto-generated if omitted).")
@click.pass_context
def download_artifact(ctx, notebook_id, artifact_id, output_path):
    """Download an artifact (audio, video, or presentation slides)."""
    json_mode = ctx.obj.get("json", False)
    try:
        client = NotebookLMClient()
        raw = client.get_artifact(notebook_id, artifact_id)
        if not raw:
            raise click.ClickException("Artifact not found")

        parsed = parse_artifact_content(raw)
        type_code = parsed.get("type_code")
        title = parsed.get("title", "artifact")

        # Sanitize title for filename
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title).strip()
        if not safe_title:
            safe_title = "artifact"

        if type_code == 8:  # Presentation — download slide images
            dir_name = output_path or f"{safe_title}_slides"
            os.makedirs(dir_name, exist_ok=True)

            slides = parsed.get("slides", [])
            if not slides:
                raise click.ClickException("No slides found in presentation")

            if not json_mode:
                click.echo(f"Downloading {len(slides)} slides from '{title}'...")

            downloaded = []
            for i, slide in enumerate(slides, 1):
                img_url = slide.get("image_url")
                if not img_url:
                    continue
                fname = f"slide_{i:02d}.png"
                fpath = os.path.join(dir_name, fname)
                with open(fpath, "wb") as f:
                    with httpx.stream("GET", img_url, follow_redirects=True) as resp:
                        resp.raise_for_status()
                        for chunk in resp.iter_bytes():
                            f.write(chunk)
                downloaded.append({"file": fpath, "size_bytes": os.path.getsize(fpath)})

            # Write slides.json with text content
            slides_json_path = os.path.join(dir_name, "slides.json")
            slides_data = []
            for i, slide in enumerate(slides, 1):
                slides_data.append({
                    "slide": i,
                    "description": slide.get("description"),
                    "text": slide.get("text"),
                    "image_url": slide.get("image_url"),
                })
            with open(slides_json_path, "w", encoding="utf-8") as f:
                json.dump(slides_data, f, indent=2, ensure_ascii=False)

            if json_mode:
                output_json({"directory": dir_name, "slides": downloaded, "slides_json": slides_json_path})
            else:
                total_size = sum(d["size_bytes"] for d in downloaded)
                click.echo(f"Downloaded {len(downloaded)} slides to {dir_name}/ ({_fmt_size(total_size)})")
                click.echo(f"Slide text saved to {slides_json_path}")

        elif type_code in (1, 3):  # Audio or Video
            media_url = parsed.get("media_url")
            if not media_url:
                raise click.ClickException("No media URL available for this artifact")

            ext = "mp4"
            if not output_path:
                output_path = f"{safe_title}.{ext}"

            if not json_mode:
                click.echo(f"Downloading {parsed.get('type', 'media')}: {title}...")

            with open(output_path, "wb") as f:
                with httpx.stream("GET", media_url, follow_redirects=True) as resp:
                    resp.raise_for_status()
                    for chunk in resp.iter_bytes():
                        f.write(chunk)

            file_size = os.path.getsize(output_path)

            if json_mode:
                output_json({"path": output_path, "size_bytes": file_size})
            else:
                click.echo(f"Downloaded {title} to {output_path} ({_fmt_size(file_size)})")

        else:
            raise click.ClickException("Download only available for audio, video, and presentation artifacts")

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))


def _fmt_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
