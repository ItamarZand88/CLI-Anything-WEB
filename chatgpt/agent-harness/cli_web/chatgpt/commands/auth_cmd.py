"""Auth management commands."""

from __future__ import annotations

import click

from ..core.auth import clear_auth, is_logged_in, load_auth, login_browser
from ..utils.helpers import handle_errors, print_json


@click.group("auth")
def auth_group():
    """Manage authentication."""


@auth_group.command("login")
@click.pass_context
def login(ctx) -> None:
    """Login to ChatGPT via browser."""
    json_mode = ctx.obj.get("json", False) if ctx.obj else False

    with handle_errors(json_mode=json_mode):
        auth_data = login_browser()
        if json_mode:
            print_json({
                "success": True,
                "data": {"message": "Logged in successfully"},
            })
        else:
            click.echo("Logged in successfully.")
            if auth_data.get("device_id"):
                click.echo(f"Device ID: {auth_data['device_id']}")


@auth_group.command("status")
@click.pass_context
def status(ctx) -> None:
    """Check authentication status."""
    json_mode = ctx.obj.get("json", False) if ctx.obj else False

    with handle_errors(json_mode=json_mode):
        if not is_logged_in():
            if json_mode:
                print_json({
                    "success": True,
                    "data": {"logged_in": False},
                })
            else:
                click.echo("Not logged in. Run: cli-web-chatgpt auth login")
            return

        auth = load_auth()
        token_preview = auth["access_token"][:20] + "..."
        device_id = auth.get("device_id", "unknown")

        if json_mode:
            print_json({
                "success": True,
                "data": {
                    "logged_in": True,
                    "device_id": device_id,
                    "token_preview": token_preview,
                },
            })
        else:
            click.echo("Logged in.")
            click.echo(f"Device ID: {device_id}")
            click.echo(f"Token: {token_preview}")


@auth_group.command("logout")
@click.pass_context
def logout(ctx) -> None:
    """Remove stored credentials."""
    json_mode = ctx.obj.get("json", False) if ctx.obj else False

    with handle_errors(json_mode=json_mode):
        clear_auth()
        if json_mode:
            print_json({"success": True, "data": {"message": "Logged out"}})
        else:
            click.echo("Logged out. Credentials removed.")
