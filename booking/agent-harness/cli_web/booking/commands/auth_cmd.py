"""Auth commands for cli-web-booking (WAF cookie management)."""

from __future__ import annotations

import click

from ..core.auth import clear_cookies, is_authenticated, login_browser
from ..utils.helpers import handle_errors, print_json


@click.group("auth")
def auth_group():
    """Manage WAF authentication cookies."""


@auth_group.command("login")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def auth_login(use_json):
    """Open browser to solve WAF challenge and save cookies."""
    with handle_errors(json_mode=use_json):
        cookies = login_browser()
        if use_json:
            print_json({
                "success": True,
                "message": "WAF cookies saved",
                "cookie_count": len(cookies),
            })
        else:
            click.echo(f"  Saved {len(cookies)} cookies. Auth ready.")


@auth_group.command("status")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def auth_status(use_json):
    """Check if WAF cookies are available."""
    with handle_errors(json_mode=use_json):
        authed = is_authenticated()
        if use_json:
            print_json({
                "success": True,
                "authenticated": authed,
            })
        else:
            if authed:
                click.echo("  WAF cookies: available")
            else:
                click.echo("  WAF cookies: not found")
                click.echo("  Run: cli-web-booking auth login")


@auth_group.command("logout")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def auth_logout(use_json):
    """Clear stored WAF cookies."""
    with handle_errors(json_mode=use_json):
        clear_cookies()
        if use_json:
            print_json({"success": True, "message": "Cookies cleared"})
        else:
            click.echo("  WAF cookies cleared.")
