"""${resource} commands for cli-web-${app_name}."""
from __future__ import annotations

import click

from ..core.client import ${AppName}Client
from ..utils.helpers import handle_errors, print_json
from ..utils.output import json_lines


@click.group("${resource}")
def ${resource_underscore}():
    """Commands for ${resource}."""


@${resource_underscore}.command("list")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.option("--jsonl", "jsonl_mode", is_flag=True, help="One JSON object per line (jq/agent piping).")
@click.pass_context
def list_${resource_underscore}(ctx, json_mode, jsonl_mode):
    """List ${resource}."""
    json_mode = json_mode or (ctx.obj or {}).get("json", False)
    with handle_errors(json_mode):
        with ${AppName}Client() as client:
            # FILL_IN: replace with the real client endpoint call, e.g.:
            #   rows = client.list_${resource_underscore}(page=1)
            rows: list = []  # FILL_IN: client call result

        if jsonl_mode:
            click.echo(json_lines(rows))
        elif json_mode:
            print_json({"success": True, "data": rows})
        else:
            if not rows:
                click.echo("No ${resource} found.")
                return
            for row in rows:
                # FILL_IN: human-readable row formatting
                click.echo(f"  {row}")


# FILL_IN: add more commands (get, search, create, ...) following the
# pattern above. Every command must support --json (structured output);
# list commands should also offer --jsonl (CONVENTIONS.md §JSON Envelope).
#
# Remember to register this group in ${app_name_underscore}_cli.py:
#   from .commands.${resource_underscore} import ${resource_underscore}
#   cli.add_command(${resource_underscore})
