"""Song/clip management commands for cli-web-suno."""

import asyncio
import json
import time

import click
import httpx

from cli_web.suno.core.client import SunoClient
from cli_web.suno.core.models import Clip
from cli_web.suno.core.auth import load_auth, AUTH_FILE
from cli_web.suno.utils.output import output_result, output_json


@click.group()
def songs():
    """Manage songs and clips."""
    pass


@songs.command("list")
@click.option("--limit", default=20, help="Number of songs to return")
@click.option("--cursor", default=None, help="Pagination cursor")
@click.option("--project", default="default", help="Project/workspace ID")
@click.pass_context
def list_songs(ctx, limit, cursor, project):
    """List user's songs."""
    as_json = ctx.obj.get("json", False)
    client = SunoClient()
    response = client.get_feed(cursor=cursor, limit=limit, workspace_id=project)
    clips = response.get("clips", [])

    if as_json:
        output_json(clips)
    else:
        if not clips:
            click.echo("No songs found.")
            return
        for clip in clips:
            c = Clip.from_dict(clip) if isinstance(clip, dict) else clip
            click.echo(f"[{c.id}] {c.title or '(untitled)'} - {c.status}")


@songs.command("get")
@click.option("--id", "song_id", required=True, help="Song/clip ID")
@click.pass_context
def get_song(ctx, song_id):
    """Get a single song by ID."""
    as_json = ctx.obj.get("json", False)
    client = SunoClient()
    response = client.get_feed(cursor=None, limit=50, workspace_id="default")
    clips = response.get("clips", [])

    matched = None
    for clip in clips:
        if isinstance(clip, dict) and clip.get("id") == song_id:
            matched = clip
            break

    if matched is None:
        click.echo(f"Song with ID '{song_id}' not found.", err=True)
        ctx.exit(1)
        return

    if as_json:
        output_json(matched)
    else:
        c = Clip.from_dict(matched)
        click.echo(f"ID:       {c.id}")
        click.echo(f"Title:    {c.title}")
        click.echo(f"Status:   {c.status}")
        click.echo(f"Duration: {c.duration}s")
        click.echo(f"Model:    {c.major_model_version}")
        click.echo(f"Plays:    {c.play_count}")
        click.echo(f"Audio:    {c.audio_url}")
        click.echo(f"Created:  {c.created_at}")


@songs.command("generate")
@click.option("--description", "-d", required=True, help="Song description (e.g. 'a happy pop song about summer')")
@click.option("--wait/--no-wait", default=True, help="Wait for generation to complete (default: wait)")
@click.pass_context
def generate(ctx, description, wait):
    """Generate a new song via browser (handles captcha automatically).

    Opens a Playwright browser with your saved session, fills in the
    description, clicks Create, and waits for generation to complete.
    You may need to solve a captcha if prompted.
    """
    as_json = ctx.obj.get("json", False)

    # First try direct API (works for Pro users without captcha)
    client = SunoClient()
    try:
        check = client.post("/api/c/check", json_body={"ctype": "generation"})
        captcha_required = check.get("required", True)
    except Exception:
        captcha_required = True

    if not captcha_required:
        # Direct API generation (no captcha needed)
        click.echo("Generating song via API...") if not as_json else None
        response = client.generate_song(gpt_description_prompt=description)
        if as_json:
            output_json(response)
        else:
            clips = response if isinstance(response, list) else response.get("clips", [response])
            for clip in clips:
                c = Clip.from_dict(clip) if isinstance(clip, dict) else clip
                click.echo(f"Generated: [{c.id}] {c.title or '(generating...)'} - {c.status}")

        if wait:
            _wait_for_generation(client, as_json)
        return

    # Captcha required — use Playwright browser
    click.echo("Captcha required. Opening browser for generation...") if not as_json else None
    result = asyncio.run(_generate_via_browser(description, wait))

    if as_json:
        output_json(result)
    else:
        if result.get("success"):
            for clip in result.get("clips", []):
                click.echo(f"Generated: [{clip.get('id', '?')}] {clip.get('title', '(generating...)')} - {clip.get('status', '?')}")
        else:
            click.echo(f"Generation result: {result.get('message', 'unknown')}")


async def _generate_via_browser(description: str, wait: bool) -> dict:
    """Generate song using Playwright connected to the debug Chrome on port 9222."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "success": False,
            "message": "Playwright not installed. Install with: pip install 'cli-web-suno[browser]'",
        }

    async with async_playwright() as pw:
        # Connect to existing debug Chrome (already logged in)
        try:
            browser = await pw.chromium.connect_over_cdp("http://localhost:9222")
        except Exception as e:
            return {
                "success": False,
                "message": f"Cannot connect to Chrome on port 9222: {e}. "
                "Launch with: chrome --remote-debugging-port=9222",
            }

        # Use existing context (has all cookies/session)
        contexts = browser.contexts
        if not contexts:
            return {"success": False, "message": "No browser context found"}
        context = contexts[0]

        # Find existing suno.com/create tab, or navigate an existing suno tab
        page = None
        for pg in context.pages:
            if "suno.com/create" in pg.url:
                page = pg
                break
        if not page:
            for pg in context.pages:
                if "suno.com" in pg.url:
                    page = pg
                    await page.goto("https://suno.com/create", wait_until="domcontentloaded", timeout=30000)
                    break
        if not page:
            page = await context.new_page()
            await page.goto("https://suno.com/create", wait_until="domcontentloaded", timeout=30000)

        # Verify textarea exists
        textarea_count = await page.locator('textarea').count()
        if textarea_count == 0:
            await page.wait_for_timeout(3000)
            textarea_count = await page.locator('textarea').count()
        if textarea_count == 0:
            return {"success": False, "message": "Create page didn't load. Are you logged in?"}

        # Fill in the song description (the visible textarea in Simple mode)
        # The description textarea has a placeholder mentioning "song" or "ambient"
        desc_textarea = page.locator('textarea:visible').first
        await desc_textarea.click()
        await desc_textarea.fill(description)
        await page.wait_for_timeout(500)

        # Click Create button
        create_btn = page.get_by_role("button", name="Create song")
        if await create_btn.count() == 0:
            create_btn = page.get_by_role("button", name="Create")
        await create_btn.click()

        click.echo("Clicked Create. Solve captcha if prompted...")

        # Wait for the generate API response
        generated_clips = []
        try:
            async with page.expect_response(
                lambda r: "/api/generate/" in r.url and r.status == 200,
                timeout=180000,  # 3 minutes for captcha solving
            ) as response_info:
                response = await response_info.value
                body = await response.json()
                generated_clips = body if isinstance(body, list) else body.get("clips", [body])
                click.echo(f"Generation started! {len(generated_clips)} clip(s) submitted.")
        except Exception:
            pass

        if wait and generated_clips:
            clip_ids = [c.get("id", "") for c in generated_clips if isinstance(c, dict)]
            click.echo(f"Waiting for clip(s) to complete...")

            for i in range(60):
                await page.wait_for_timeout(3000)
                try:
                    client = SunoClient()
                    feed = client.get_feed(limit=5)
                    done = [c for c in feed.get("clips", [])
                            if c.get("id") in clip_ids and c.get("status") == "complete"]
                    if len(done) == len(clip_ids):
                        click.echo("Generation complete!")
                        pass  # Don't close — it may be user's existing tab
                        return {"success": True, "clips": done}
                except Exception:
                    pass
                if i % 5 == 4:
                    click.echo("  Still generating...")

        pass  # Don't close — it may be user's existing tab

        if generated_clips:
            return {"success": True, "clips": generated_clips}
        else:
            try:
                client = SunoClient()
                feed = client.get_feed(limit=2)
                return {"success": True, "clips": feed.get("clips", [])[:2],
                        "message": "Check library for generated songs"}
            except Exception:
                return {"success": True, "message": "Song submitted. Check your library."}


def _wait_for_generation(client: SunoClient, as_json: bool):
    """Poll until no running jobs remain."""
    for i in range(40):  # ~2 minutes
        time.sleep(3)
        status = client.get_concurrent_status()
        running = status.get("running_jobs", 0)
        if running == 0:
            # Fetch newest clips
            feed = client.get_feed(limit=2)
            clips = feed.get("clips", [])
            if as_json:
                output_json(clips[:2])
            else:
                click.echo("Generation complete!")
                for clip in clips[:2]:
                    c = Clip.from_dict(clip)
                    click.echo(f"  [{c.id}] {c.title or '(untitled)'} - {c.status} ({c.duration}s)")
            return
        if not as_json and i % 3 == 0:
            click.echo(f"  Generating... ({running} job(s) running)")
    if not as_json:
        click.echo("Generation still in progress. Check with: cli-web-suno songs status")


@songs.command("status")
@click.pass_context
def status(ctx):
    """Check generation queue status."""
    as_json = ctx.obj.get("json", False)
    client = SunoClient()
    response = client.get_concurrent_status()

    if as_json:
        output_json(response)
    else:
        running = response.get("running_jobs", 0)
        max_concurrent = response.get("max_concurrent", 0)
        click.echo(f"Running jobs: {running} / {max_concurrent}")


@songs.command("download")
@click.option("--id", "song_id", required=True, help="Song/clip ID to download")
@click.option("--output", "output_path", default=None, help="Output file path (default: <id>.mp3)")
@click.pass_context
def download(ctx, song_id, output_path):
    """Download song audio to a local file."""
    as_json = ctx.obj.get("json", False)
    client = SunoClient()

    response = client.get_feed(cursor=None, limit=50, workspace_id="default")
    clips = response.get("clips", [])

    matched = None
    for clip in clips:
        if isinstance(clip, dict) and clip.get("id") == song_id:
            matched = clip
            break

    if matched is None:
        click.echo(f"Song with ID '{song_id}' not found.", err=True)
        ctx.exit(1)
        return

    audio_url = matched.get("audio_url", "")
    if not audio_url:
        click.echo("No audio URL available for this song.", err=True)
        ctx.exit(1)
        return

    if output_path is None:
        output_path = f"{song_id}.mp3"

    if not as_json:
        click.echo(f"Downloading {song_id} to {output_path}...")
    with httpx.stream("GET", audio_url) as resp:
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=8192):
                f.write(chunk)

    result = {"id": song_id, "output": output_path, "status": "downloaded"}
    if as_json:
        output_json(result)
    else:
        click.echo(f"Downloaded to {output_path}")
