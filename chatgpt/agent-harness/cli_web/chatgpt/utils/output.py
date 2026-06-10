"""Output formatting for cli-web-chatgpt."""

from __future__ import annotations

import json

import click


def print_json(data) -> None:
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


def truncate(text: str | None, length: int = 60) -> str:
    if not text:
        return ""
    return text[:length] + "..." if len(text) > length else text
