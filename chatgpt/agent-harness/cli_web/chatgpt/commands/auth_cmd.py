"""Auth management commands."""

from __future__ import annotations

import click

from ..core.auth import clear_auth, is_logged_in, login_browser
from ..utils.helpers import handle_errors
from ..utils.output import print_json


@click.group("auth")
def auth_group():
    """Manage authentication."""


@auth_group.command("login")
@click.pass_context
def login(ctx) -> None:
    """Login to ChatGPT via browser."""
    json_mode = ctx.obj.get("json", False) if ctx.obj else False

    with handle_errors(json_mode=json_mode):
        login_browser()
        if json_mode:
            print_json(
                {
                    "success": True,
                    "data": {"message": "Logged in successfully"},
                }
            )
        else:
            click.echo("Logged in successfully.")


@auth_group.command("status")
@click.pass_context
def status(ctx) -> None:
    """Check authentication status."""
    json_mode = ctx.obj.get("json", False) if ctx.obj else False

    with handle_errors(json_mode=json_mode):
        if not is_logged_in():
            if json_mode:
                print_json(
                    {
                        "success": True,
                        "data": {"logged_in": False},
                    }
                )
            else:
                click.echo("Not logged in. Run: cli-web-chatgpt auth login")
            return

        if json_mode:
            print_json(
                {
                    "success": True,
                    "data": {"logged_in": True},
                }
            )
        else:
            click.echo("Logged in.")


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
