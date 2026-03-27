"""Auth command group — login, status, logout."""

from __future__ import annotations

import click

from cli_web.hackernews.core import auth
from cli_web.hackernews.core.exceptions import AuthError
from cli_web.hackernews.utils.helpers import handle_errors, print_json, resolve_json_mode


@click.group("auth")
def auth_group():
    """Manage Hacker News authentication."""


@auth_group.command("login")
@click.option("--username", "-u", prompt="HN username", help="Your Hacker News username.")
@click.option("--password", "-p", prompt=True, hide_input=True, help="Your Hacker News password.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def auth_login(ctx, username, password, json_mode):
    """Login to Hacker News with username and password."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        result = auth.login_with_password(username, password)
        if json_mode:
            print_json({"success": True, "username": result["username"]})
        else:
            click.echo(f"Logged in as {result['username']}")


@auth_group.command("login-browser")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def auth_login_browser(ctx, json_mode):
    """Login to Hacker News via browser (opens a browser window)."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        result = auth.login_browser()
        if json_mode:
            print_json({"success": True, "username": result["username"]})
        else:
            click.echo(f"Logged in as {result['username']}")


@auth_group.command("status")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def auth_status(ctx, json_mode):
    """Check authentication status."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        if not auth.is_logged_in():
            if json_mode:
                print_json({"logged_in": False})
            else:
                click.echo("Not logged in. Run: cli-web-hackernews auth login")
            return

        result = auth.validate_auth()
        if json_mode:
            print_json({"logged_in": True, "username": result["username"], "valid": result["valid"]})
        else:
            click.echo(f"Logged in as: {result['username']}")
            click.echo(f"Cookie valid: {'yes' if result['valid'] else 'no'}")


@auth_group.command("logout")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def auth_logout(ctx, json_mode):
    """Remove stored authentication credentials."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        auth.logout()
        if json_mode:
            print_json({"success": True, "message": "Logged out"})
        else:
            click.echo("Logged out successfully.")
