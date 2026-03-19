"""
Reference: Persistent Context & Partial ID Pattern
=====================================================
For apps where users work within a specific context (notebook, project, workspace),
provide `use <id>` and `status` commands that persist across CLI sessions.

Key patterns:
1. `use <id>` — validates and saves to context.json
2. `status` — shows current context + auth status
3. `require_<resource>()` — --<resource> is optional when context is set
4. Partial ID resolution — users type short prefixes

This pattern eliminates the need to pass --<resource> on every command.
Replace <resource> with the app's primary entity (notebook, project, workspace, etc.).
"""

# --- In <app>_cli.py ---

import click


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    pass


@cli.command("use")
@click.argument("resource_id")
@click.pass_context
def use_resource(ctx, resource_id):
    """Set the current resource context (persists across sessions)."""
    from .utils.helpers import handle_errors, set_context_value, resolve_partial_id

    with handle_errors():
        client = AppClient()
        # Resolve partial ID (user can type 'abc' instead of full UUID)
        all_items = client.list_resources()
        matched = resolve_partial_id(resource_id, all_items, kind="resource")
        set_context_value("resource_id", matched.id)
        set_context_value("resource_title", matched.title)
        click.echo(f"  Now using: {matched.title} ({matched.id})")


@cli.command("status")
@click.option("--json", "use_json", is_flag=True)
@click.pass_context
def show_status(ctx, use_json):
    """Show current context and auth status."""
    from .utils.helpers import handle_errors, get_context_value, print_json

    with handle_errors(json_mode=use_json):
        status = {
            "resource_id": get_context_value("resource_id"),
            "resource_title": get_context_value("resource_title"),
        }
        # Add auth status if the app requires auth
        try:
            from .core.auth import get_auth_status
            status["auth"] = get_auth_status()
        except ImportError:
            status["auth"] = {"configured": False, "message": "No auth required"}
        if use_json:
            print_json(status)
        else:
            click.echo(f"  Resource: {status['resource_title'] or '(none)'}")
            click.echo(f"  Auth: {status['auth'].get('message', 'unknown')}")


# --- In command files: --<resource> becomes optional ---

@cli.group()
def items():
    """Item commands."""
    pass


@items.command("list")
@click.option("--resource", default=None, help="Resource ID (optional if context set)")
@click.option("--json", "use_json", is_flag=True)
def list_items(resource, use_json):
    """List items in a resource."""
    from .utils.helpers import handle_errors, require_resource

    with handle_errors(json_mode=use_json):
        res_id = require_resource(resource)  # Checks arg first, then context.json
        client = AppClient()
        items = client.list_items(res_id)
        # ... output items


# --- In command files: partial ID for get/rename/delete ---

@items.command("get")
@click.argument("item_id")  # Positional — supports partial IDs
@click.option("--json", "use_json", is_flag=True)
def get_item(item_id, use_json):
    """Get an item by ID (partial prefix OK)."""
    from .utils.helpers import handle_errors, resolve_partial_id

    with handle_errors(json_mode=use_json):
        client = AppClient()
        all_items = client.list_items()
        matched = resolve_partial_id(item_id, all_items, kind="item")
        item = client.get_item(matched.id)
        # ... output item


# --- Context file format ---
# ~/.config/cli-web-<app>/context.json
# {
#   "resource_id": "abc123-full-uuid",
#   "resource_title": "My Project"
# }
