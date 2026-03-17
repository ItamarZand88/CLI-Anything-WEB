"""Authentication commands for NotebookLM CLI."""

import asyncio
import sys

import click

from cli_web.notebooklm.core.auth import (
    check_required_cookies,
    fetch_tokens,
    load_cookies,
    login_from_json,
    login_from_browser,
    login_with_playwright,
    logout,
)
from cli_web.notebooklm.utils.output import output_json


@click.group("auth")
def auth():
    """Manage authentication for NotebookLM."""
    pass


@auth.command("login")
@click.option("--from-browser", is_flag=True, help="Extract cookies from Chrome debug profile (port 9222)")
@click.option("--cookies-json", type=str, default=None, help="Import cookies from a JSON file")
@click.pass_context
def auth_login(ctx, from_browser, cookies_json):
    """Log in to NotebookLM."""
    json_mode = ctx.obj.get("json", False)

    try:
        if cookies_json:
            cookies = login_from_json(cookies_json)
            msg = f"Imported {len(cookies)} cookies from {cookies_json}"
        elif from_browser:
            cookies = asyncio.run(login_from_browser())
            msg = f"Extracted {len(cookies)} cookies from Chrome debug profile"
        else:
            cookies = asyncio.run(login_with_playwright())
            msg = f"Saved {len(cookies)} cookies from browser login"

        ok, missing = check_required_cookies(cookies)
        if not ok:
            if json_mode:
                output_json({"status": "warning", "message": msg, "missing_cookies": missing})
            else:
                click.echo(f"  {msg}")
                click.echo(f"  Warning: Missing required cookies: {', '.join(missing)}")
            sys.exit(1)

        if json_mode:
            output_json({"status": "ok", "message": msg, "cookie_count": len(cookies)})
        else:
            click.echo(f"  {msg}")
            click.echo("  Login successful.")

    except Exception as e:
        if json_mode:
            output_json({"status": "error", "message": str(e)})
        else:
            click.echo(f"  Error: {e}", err=True)
        sys.exit(1)


@auth.command("status")
@click.pass_context
def auth_status(ctx):
    """Check authentication status."""
    json_mode = ctx.obj.get("json", False)

    cookies = load_cookies()
    if not cookies:
        if json_mode:
            output_json({"status": "not_configured", "message": "No cookies found"})
        else:
            click.echo("  Not authenticated. Run: cli-web-notebooklm auth login")
        sys.exit(1)

    ok, missing = check_required_cookies(cookies)

    # Try live validation
    live_ok = False
    live_error = None
    try:
        tokens = fetch_tokens(cookies)
        live_ok = tokens.get("at") is not None
    except Exception as e:
        live_error = str(e)

    if json_mode:
        output_json({
            "status": "ok" if (ok and live_ok) else "error",
            "cookie_count": len(cookies),
            "required_cookies_present": ok,
            "missing_cookies": missing,
            "live_validation": "ok" if live_ok else "failed",
            "live_error": live_error,
        })
    else:
        click.echo(f"  Cookies: {len(cookies)} stored")
        click.echo(f"  Required cookies: {'All present' if ok else f'Missing: {missing}'}")
        click.echo(f"  Live validation: {'OK' if live_ok else f'FAILED — {live_error}'}")

    if not (ok and live_ok):
        sys.exit(1)


@auth.command("logout")
@click.pass_context
def auth_logout(ctx):
    """Remove stored authentication data."""
    json_mode = ctx.obj.get("json", False)

    logout()
    if json_mode:
        output_json({"status": "ok", "message": "Logged out"})
    else:
        click.echo("  Logged out. Auth data removed.")
