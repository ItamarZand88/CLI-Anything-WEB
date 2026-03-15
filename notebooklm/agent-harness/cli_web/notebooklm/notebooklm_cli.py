"""Main CLI entry point for cli-web-notebooklm."""

from __future__ import annotations

import json
import sys

import click

from cli_web.notebooklm import __version__
from cli_web.notebooklm.commands.notebooks import notebooks_group
from cli_web.notebooklm.commands.sources import sources_group
from cli_web.notebooklm.commands.notes import notes_group
from cli_web.notebooklm.commands.chat import chat_group
from cli_web.notebooklm.commands.artifacts import artifacts_group
from cli_web.notebooklm.core.auth import (
    load_cookies,
    save_cookies,
    validate_cookies,
    export_cookies_json,
    REQUIRED_COOKIES,
)
from cli_web.notebooklm.utils.output import output_json, output_error


@click.group()
@click.version_option(version=__version__, prog_name="cli-web-notebooklm")
def cli():
    """CLI harness for Google NotebookLM.

    Manage notebooks, sources, notes, chat, and artifacts
    from the command line via the cli-anything-web pipeline.
    """
    pass


# ── Register command groups ────────────────────────────────────────────

cli.add_command(notebooks_group)
cli.add_command(sources_group)
cli.add_command(notes_group)
cli.add_command(chat_group)
cli.add_command(artifacts_group)


# ── Auth commands ──────────────────────────────────────────────────────

@cli.group("auth")
def auth_group():
    """Manage authentication (cookie-based)."""
    pass


@auth_group.command("login")
@click.option(
    "--from-browser", is_flag=True,
    help="Auto-extract cookies from Chrome debug profile (port 9222).",
)
@click.option(
    "--cookies-json",
    type=click.Path(exists=True),
    help="Path to a JSON file with exported cookies.",
)
@click.option("--port", type=int, default=9222, help="Chrome debug port (default: 9222).")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def auth_login(from_browser: bool, cookies_json: str | None, port: int, as_json: bool):
    """Import browser cookies for authentication.

    Recommended: use --from-browser to auto-extract cookies from your
    Chrome debug profile. Launch Chrome first with:

        chrome --remote-debugging-port=9222 --user-data-dir="~/.chrome-debug-profile"

    Then log into NotebookLM in that Chrome window, and run:

        cli-web-notebooklm auth login --from-browser
    """
    if from_browser:
        try:
            from cli_web.notebooklm.core.auth import extract_cookies_from_browser
            click.echo(f"Connecting to Chrome on port {port}...")
            cookies = extract_cookies_from_browser(domain=".google.com", port=port)
            if not cookies:
                output_error("No Google cookies found. Make sure you're logged in.")
                raise SystemExit(1)
            click.echo(f"Extracted {len(cookies)} cookies from browser")
        except ConnectionRefusedError:
            output_error(
                f"Cannot connect to Chrome on port {port}.\n"
                "Launch Chrome with:\n"
                f'  chrome --remote-debugging-port={port} '
                f'--user-data-dir="~/.chrome-debug-profile"'
            )
            raise SystemExit(1)
        except ImportError as e:
            output_error(str(e))
            raise SystemExit(1)
    elif cookies_json:
        with open(cookies_json, "r", encoding="utf-8") as f:
            cookies = json.load(f)
    else:
        click.echo("Paste your cookies as a JSON object (then press Enter):")
        raw = sys.stdin.read() if not sys.stdin.isatty() else input()
        try:
            cookies = json.loads(raw)
        except json.JSONDecodeError:
            output_error("Invalid JSON. Expected a dict of cookie name -> value.")
            raise SystemExit(1)

    if not isinstance(cookies, dict):
        output_error("Expected a JSON object mapping cookie names to values.")
        raise SystemExit(1)

    missing = validate_cookies(cookies)
    if missing:
        click.echo(f"Warning: Missing recommended cookies: {', '.join(missing)}")

    path = save_cookies(cookies)

    if as_json:
        output_json({"status": "saved", "path": str(path), "cookie_count": len(cookies)})
        return

    click.echo(f"Saved {len(cookies)} cookies to {path}")


@auth_group.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def auth_status(as_json: bool):
    """Check authentication status."""
    try:
        cookies = load_cookies()
    except FileNotFoundError as e:
        if as_json:
            output_json({"authenticated": False, "error": str(e)})
        else:
            output_error(str(e))
        raise SystemExit(1)

    missing = validate_cookies(cookies)
    is_valid = len(missing) == 0

    if as_json:
        output_json({
            "authenticated": True,
            "cookie_count": len(cookies),
            "missing_cookies": missing,
            "all_required_present": is_valid,
        })
        return

    click.echo(f"Cookies loaded: {len(cookies)}")
    if missing:
        click.echo(f"Missing: {', '.join(missing)}")
    else:
        click.echo("All required cookies present.")

    # Try a live validation
    try:
        from cli_web.notebooklm.core.client import NotebookLMClient
        from cli_web.notebooklm.utils.config import RPC_USER_SETTINGS
        client = NotebookLMClient(cookies=cookies)
        data = client.rpc(
            RPC_USER_SETTINGS,
            [None, [1, None, None, None, None, None, None, None, None, None, [1]]],
        )
        click.echo("Live validation: OK (API responded)")
    except Exception as e:
        click.echo(f"Live validation: FAILED ({e})")


@auth_group.command("export")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def auth_export(as_json: bool):
    """Export stored cookies as JSON."""
    try:
        cookies = load_cookies()
    except FileNotFoundError as e:
        output_error(str(e))
        raise SystemExit(1)

    # Always output as JSON for this command
    click.echo(export_cookies_json(cookies))


if __name__ == "__main__":
    cli()
