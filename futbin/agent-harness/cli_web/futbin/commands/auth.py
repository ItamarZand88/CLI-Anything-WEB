"""Auth commands for FUTBIN CLI."""

import asyncio
import click

from cli_web.futbin.core import auth
from cli_web.futbin.utils.output import output_json


@click.group()
def auth_group():
    """Manage authentication for FUTBIN."""
    pass


@auth_group.command("login")
@click.option("--from-chrome", is_flag=True, help="Extract cookies from Chrome debug session")
@click.option("--cookies-json", type=click.Path(exists=True), help="Import cookies from JSON file")
@click.pass_context
def login(ctx, from_chrome, cookies_json):
    """Login to FUTBIN."""
    json_mode = ctx.obj.get("json", False)

    if cookies_json:
        cookies = auth.login_from_json_file(cookies_json)
        msg = f"Imported {len(cookies)} cookies from {cookies_json}"
    elif from_chrome:
        cookies = auth.login_from_chrome_cdp()
        msg = f"Extracted {len(cookies)} cookies from Chrome"
    else:
        cookies = asyncio.run(auth.login_with_playwright())
        msg = f"Saved {len(cookies)} cookies from Playwright login"

    if json_mode:
        output_json({"status": "ok", "message": msg, "cookie_count": len(cookies)})
    else:
        click.echo(msg)


@auth_group.command("status")
@click.pass_context
def status(ctx):
    """Show current auth status."""
    json_mode = ctx.obj.get("json", False)
    info = auth.get_auth_status()

    if json_mode:
        output_json(info)
    else:
        if info["authenticated"]:
            click.echo(f"Authenticated: {info['cookie_count']} cookies stored")
            click.echo(f"Cookies: {', '.join(info.get('cookie_names', []))}")
        else:
            click.echo("Not authenticated. Most features work without login.")
            click.echo("To login: cli-web-futbin auth login")


@auth_group.command("logout")
@click.pass_context
def logout(ctx):
    """Clear stored cookies."""
    json_mode = ctx.obj.get("json", False)
    auth.clear_cookies()

    if json_mode:
        output_json({"status": "ok", "message": "Cookies cleared"})
    else:
        click.echo("Cookies cleared.")
