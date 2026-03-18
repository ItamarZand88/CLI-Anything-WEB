"""
Reference: Rich Output & JSON Error Responses
===============================================
Patterns for CLI output formatting:

1. Rich progress spinners for long operations
2. Rich tables for list commands
3. Structured JSON error responses
4. Dual-mode output (human vs --json)
"""
import json
import sys
from typing import Any


# --- JSON Output Helpers (utils/output.py) ---

def json_success(data: Any, **extra) -> str:
    """Format a success response for --json mode."""
    response = {"success": True, "data": data}
    response.update(extra)
    return json.dumps(response, indent=2, ensure_ascii=False)


def json_error(code: str, message: str, **extra) -> str:
    """Format an error response for --json mode.

    Standard error codes:
    - AUTH_EXPIRED: session expired, re-login needed
    - RATE_LIMITED: 429, retry after delay
    - NOT_FOUND: resource doesn't exist
    - SERVER_ERROR: 5xx from upstream
    - NETWORK_ERROR: connection/timeout failure
    - VALIDATION_ERROR: bad input parameters
    """
    response = {"error": True, "code": code, "message": message}
    response.update(extra)
    return json.dumps(response, indent=2, ensure_ascii=False)


# --- Error Handler (for commands) ---

def handle_command_error(exc, json_mode: bool = False) -> None:
    """Convert exception to CLI output. Call in command except blocks.

    Example:
        try:
            result = client.notebooks.list()
        except AppError as e:
            handle_command_error(e, json_mode=ctx.obj.get("json"))
            raise SystemExit(1)
    """
    # Import from generated exceptions
    # from .exceptions import error_code_for

    code = error_code_for(exc) if hasattr(exc, '__class__') else "UNKNOWN_ERROR"

    if json_mode:
        print(json_error(code, str(exc)), file=sys.stdout)
    else:
        import click
        click.echo(f"Error: {exc}", err=True)


# --- Rich Progress (for long operations) ---

def with_progress(message: str, fn, json_mode: bool = False):
    """Run function with Rich spinner, suppress in --json mode.

    Example:
        result = with_progress(
            "Generating audio...",
            lambda: client.artifacts.wait_for_completion(nb_id, task_id),
            json_mode=ctx.obj.get("json"),
        )
    """
    if json_mode:
        return fn()

    from rich.console import Console
    console = Console()
    with console.status(message):
        return fn()


# --- Rich Tables (for list commands) ---

def print_table(items: list[dict], columns: list[tuple[str, str]],
                title: str = "", json_mode: bool = False) -> None:
    """Print items as Rich table or JSON.

    Args:
        items: List of dicts to display.
        columns: List of (key, header) tuples.
        title: Table title.
        json_mode: If True, output JSON instead of table.

    Example:
        print_table(
            notebooks,
            columns=[("id", "ID"), ("title", "Title"), ("source_count", "Sources")],
            title="Notebooks",
            json_mode=ctx.obj.get("json"),
        )
    """
    if json_mode:
        print(json_success([{k: item.get(k) for k, _ in columns} for item in items]))
        return

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title=title)

    for key, header in columns:
        table.add_column(header, style="cyan" if key == "id" else "")

    for item in items:
        table.add_row(*[str(item.get(k, "—")) for k, _ in columns])

    console.print(table)
