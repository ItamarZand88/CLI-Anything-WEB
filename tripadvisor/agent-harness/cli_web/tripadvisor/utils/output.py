"""Output formatting utilities for cli-web-tripadvisor."""

from __future__ import annotations

import json

import click


def json_error(code: str, message: str, **extra) -> str:
    """Format an error as a JSON string."""
    return json.dumps({"error": True, "code": code, "message": message, **extra})


def print_json(data) -> None:
    """Print data as formatted JSON to stdout."""
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))
