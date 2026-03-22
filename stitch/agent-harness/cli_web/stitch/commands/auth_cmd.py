"""Auth commands for cli-web-stitch."""
import click

from ..core.auth import login_browser, login_from_cookies_json, get_auth_status
from ..utils.helpers import handle_errors
from ..utils.output import json_success, print_json


@click.group("auth")
def auth():
    """Manage authentication."""


@auth.command("login")
@click.option("--headed/--headless", default=True, help="Show browser window")
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def auth_login(ctx, headed, json_mode):
    """Login via browser (Google SSO)."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        login_browser(headed=headed)
        if json_mode:
            print_json(json_success({"message": "Login complete"}))


@auth.command("status")
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def auth_status(ctx, json_mode):
    """Check authentication status."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        status = get_auth_status()
        if json_mode:
            print_json(json_success(status))
        else:
            configured = status.get("configured", False)
            valid = status.get("valid", False)
            message = status.get("message", "")
            if not configured:
                click.echo("Auth: not configured")
                click.echo("Run: cli-web-stitch auth login")
            elif valid:
                click.echo(f"Auth: {message}")
                count = status.get("cookie_count")
                if count:
                    click.echo(f"Cookies: {count}")
            else:
                click.echo(f"Auth: invalid — {message}")


@auth.command("import")
@click.argument("file", type=click.Path(exists=True))
@click.option("--json", "json_mode", is_flag=True, help="JSON output")
@click.pass_context
def auth_import(ctx, file, json_mode):
    """Import cookies from a JSON file."""
    json_mode = json_mode or (ctx.obj.get("json", False) if ctx.obj else False)
    with handle_errors(json_mode=json_mode):
        login_from_cookies_json(file)
        if json_mode:
            print_json(json_success({"message": "Cookies imported"}))
