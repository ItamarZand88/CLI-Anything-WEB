"""${resource} commands for cli-web-${app_name}."""
from __future__ import annotations

import click

from ..core.client import ${AppName}Client
from ..utils.helpers import handle_errors, print_json


@click.group("${resource}")
def ${resource_underscore}():
    """Commands for ${resource}."""


@${resource_underscore}.command("list")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def list_${resource_underscore}(ctx, json_mode):
    """List ${resource}."""
    json_mode = json_mode or (ctx.obj or {}).get("json", False)
    with handle_errors(json_mode):
        with ${AppName}Client() as client:
            # FILL_IN: replace with the real client endpoint call, e.g.:
            #   rows = client.list_${resource_underscore}(page=1)
            rows: list = []  # FILL_IN: client call result

        if json_mode:
            print_json({"success": True, "data": rows})
        else:
            if not rows:
                click.echo("No ${resource} found.")
                return
            for row in rows:
                # FILL_IN: human-readable row formatting
                click.echo(f"  {row}")


# FILL_IN: add more commands (get, search, create, ...) following the
# pattern above. Every command must support --json (structured output).
#
# Remember to register this group in ${app_name_underscore}_cli.py:
#   from .commands.${resource_underscore} import ${resource_underscore}
#   cli.add_command(${resource_underscore})
