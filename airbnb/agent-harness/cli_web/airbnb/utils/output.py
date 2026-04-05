"""Output utilities for cli-web-airbnb."""

from __future__ import annotations

import json
import click


def json_error(code: str, message: str, **extra) -> None:
    """Print a JSON error to stdout."""
    click.echo(json.dumps({"error": True, "code": code, "message": message, **extra}))
