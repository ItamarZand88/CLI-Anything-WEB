"""Auth commands for cli-web-reddit."""

from __future__ import annotations

import click

from ..core.auth import clear_auth, load_auth, login_browser
from ..core.client import RedditClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode


@click.group("auth")
def auth():
    """Login, logout, and check authentication status."""


@auth.command("login")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def login(use_json):
    """Login to Reddit via browser (opens Playwright)."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        login_browser()
        if use_json:
            print_json({"success": True, "message": "Logged in successfully"})
        else:
            click.echo("  Logged in successfully. Token saved.")


@auth.command("logout")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def logout(use_json):
    """Remove saved authentication."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        clear_auth()
        if use_json:
            print_json({"success": True, "message": "Logged out"})
        else:
            click.echo("  Logged out. Auth data removed.")


@auth.command("status")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def status(use_json):
    """Check current authentication status."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        auth_data = load_auth()
        if not auth_data or not auth_data.get("token"):
            if use_json:
                print_json({"authenticated": False, "message": "Not logged in"})
            else:
                click.echo("  Not logged in. Run: cli-web-reddit auth login")
            return

        # Verify token works by calling /api/v1/me
        client = RedditClient()
        me = client.me()
        username = me.get("name", "unknown")
        karma = me.get("total_karma", 0)

        if use_json:
            print_json(
                {
                    "authenticated": True,
                    "username": username,
                    "total_karma": karma,
                }
            )
        else:
            click.echo(f"  Logged in as: u/{username}")
            click.echo(f"  Total karma: {karma:,}")
