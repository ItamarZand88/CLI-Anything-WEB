"""Authentication commands for cli-web-suno."""

import asyncio
import time

import click

from cli_web.suno.core import auth
from cli_web.suno.utils.output import output_result, output_json


@click.group()
def auth_group():
    """Authentication management."""
    pass


@auth_group.command()
@click.option("--from-browser", is_flag=True, default=False,
              help="Extract cookies from Chrome debug profile (port 9222).")
@click.option("--cookies-json", type=click.Path(exists=True),
              help="Import cookies from a JSON file.")
@click.pass_context
def login(ctx, from_browser, cookies_json):
    """Login to Suno."""
    as_json = ctx.obj.get("json", False)

    try:
        if cookies_json:
            result = auth.login_from_cookies_json(cookies_json)
        elif from_browser:
            result = auth.login_from_browser()
        else:
            result = asyncio.run(auth.login_with_playwright())

        jwt_present = bool(result.get("jwt"))
        num_cookies = len(result.get("cookies", []))
        info = {
            "success": True,
            "method": result.get("login_method", "unknown"),
            "jwt_obtained": jwt_present,
            "cookies_saved": num_cookies,
        }
        if as_json:
            output_json(info)
        else:
            click.echo(f"Login successful ({info['method']})")
            click.echo(f"  JWT obtained: {jwt_present}")
            click.echo(f"  Cookies saved: {num_cookies}")
    except Exception as e:
        if as_json:
            output_json({"error": str(e), "success": False})
        else:
            click.echo(f"error: {e}", err=True)
        raise click.Abort()


@auth_group.command()
@click.pass_context
def status(ctx):
    """Show authentication status and validate live."""
    as_json = ctx.obj.get("json", False)

    auth_data = auth.load_auth()
    if not auth_data:
        msg = {"error": "Not logged in. Run: cli-web-suno auth login --from-browser", "success": False}
        if as_json:
            output_json(msg)
        else:
            click.echo(msg["error"], err=True)
        return

    try:
        session = auth.validate_auth()
        user = session.get("user", {})
        billing_credits = session.get("configs", {})

        info = {
            "logged_in": True,
            "login_method": auth_data.get("login_method", "unknown"),
            "login_time": time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(auth_data.get("login_time", 0))
            ),
            "email": user.get("email", ""),
            "display_name": user.get("display_name", ""),
            "handle": user.get("handle", ""),
            "live_validation": "OK",
        }

        if as_json:
            output_json(info)
        else:
            click.echo(f"Login method:    {info['login_method']}")
            click.echo(f"Login time:      {info['login_time']}")
            click.echo(f"Email:           {info['email']}")
            click.echo(f"Display name:    {info['display_name']}")
            click.echo(f"Handle:          @{info['handle']}")
            click.echo(f"Live validation: {click.style('OK', fg='green')}")

    except Exception as e:
        info = {
            "logged_in": True,
            "login_method": auth_data.get("login_method", "unknown"),
            "live_validation": f"FAILED: {e}",
        }
        if as_json:
            output_json(info)
        else:
            click.echo(f"Login method:    {info['login_method']}")
            click.echo(f"Live validation: {click.style(f'FAILED: {e}', fg='red')}")


@auth_group.command()
@click.pass_context
def refresh(ctx):
    """Refresh JWT token."""
    as_json = ctx.obj.get("json", False)

    auth_data = auth.load_auth()
    if not auth_data:
        msg = {"error": "Not logged in.", "success": False}
        if as_json:
            output_json(msg)
        else:
            click.echo(msg["error"], err=True)
        return

    jwt = auth.refresh_jwt_from_cookies(auth_data.get("cookies", []))
    if jwt:
        auth_data["jwt"] = jwt
        auth_data["jwt_refreshed_at"] = time.time()
        auth.save_auth(auth_data)
        msg = {"success": True, "message": "JWT refreshed."}
    else:
        msg = {"success": False, "error": "Failed to refresh JWT. Try re-logging in."}

    if as_json:
        output_json(msg)
    else:
        click.echo(msg.get("message", msg.get("error", "")))
