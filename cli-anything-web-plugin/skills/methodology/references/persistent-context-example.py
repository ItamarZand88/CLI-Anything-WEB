"""
Reference: Persistent Context & Partial ID Pattern
=====================================================
For apps where users work within a specific context (notebook, project, workspace),
provide `use <id>` and `status` commands that persist across CLI sessions.

Key patterns:
1. `use <id>` — validates and saves to context.json
2. `status` — shows current context + auth status
3. `require_notebook()` — --notebook is optional when context is set
4. Partial ID resolution — users type short prefixes

This pattern eliminates the need to pass --notebook on every command.
"""

# --- In notebooklm_cli.py (or <app>_cli.py) ---

import click

# @main.command("use")
# @click.argument("notebook_id")
# def use_notebook(notebook_id):
#     """Set the current notebook context (persists across sessions)."""
#     from .utils.helpers import handle_errors, set_context_value
#     with handle_errors():
#         client = AppClient()
#         nb = client.get_notebook(notebook_id)
#         set_context_value("notebook_id", nb.id)
#         set_context_value("notebook_title", nb.title)
#         click.echo(f"Now using: {nb.title} ({nb.id})")
#
# @main.command("status")
# @click.option("--json", "as_json", is_flag=True)
# def show_status(as_json):
#     """Show current context and auth status."""
#     from .utils.helpers import handle_errors, get_context_value
#     with handle_errors(json_mode=as_json):
#         context = {
#             "notebook_id": get_context_value("notebook_id"),
#             "notebook_title": get_context_value("notebook_title"),
#         }
#         # ... show context + auth status


# --- In command files: --notebook becomes optional ---

# BEFORE (required):
# @sources.command("list")
# @click.option("--notebook", required=True)  # User must always specify
# def list_sources(notebook, use_json):
#     ...

# AFTER (optional with context fallback):
# @sources.command("list")
# @click.option("--notebook", default=None)  # Falls back to context
# def list_sources(notebook, use_json):
#     with handle_errors(json_mode=use_json):
#         nb_id = require_notebook(notebook)  # Checks arg, then context.json
#         client = AppClient()
#         sources = client.list_sources(nb_id)


# --- In command files: partial ID for get/rename/delete ---

# BEFORE:
# @notebooks.command("get")
# @click.option("--id", "notebook_id", required=True)  # Full UUID required
# def get_notebook(notebook_id, as_json):
#     client = AppClient()
#     nb = client.get_notebook(notebook_id)

# AFTER:
# @notebooks.command("get")
# @click.argument("notebook_id")  # Positional, supports partial
# def get_notebook(notebook_id, as_json):
#     with handle_errors(json_mode=as_json):
#         client = AppClient()
#         nbs = client.list_notebooks()
#         matched = resolve_partial_id(notebook_id, nbs, kind="notebook")
#         nb = client.get_notebook(matched.id)


# --- Context file format ---
# ~/.config/cli-web-<app>/context.json
# {
#   "notebook_id": "abc123-full-uuid",
#   "notebook_title": "My Research"
# }
