"""Output formatting for cli-web-notebooklm."""
import json
import sys
from datetime import datetime
from typing import Any

from ..core.models import Notebook, Source, User, Artifact


def _ts(unix_sec) -> str:
    if not unix_sec:
        return "—"
    try:
        return datetime.fromtimestamp(unix_sec).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        return "—"


def print_json(data: Any):
    """Print data as JSON."""
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def notebook_to_dict(nb: Notebook) -> dict:
    return {
        "id": nb.id,
        "title": nb.title,
        "emoji": nb.emoji,
        "source_count": nb.source_count,
        "is_pinned": nb.is_pinned,
        "created_at": nb.created_at,
        "updated_at": nb.updated_at,
    }


def source_to_dict(src: Source) -> dict:
    return {
        "id": src.id,
        "name": src.name,
        "type": src.source_type,
        "url": src.url,
        "char_count": src.char_count,
        "created_at": src.created_at,
    }


def print_notebooks_table(notebooks: list[Notebook]):
    if not notebooks:
        print("No notebooks found.")
        return
    print(f"{'ID':<38}  {'Title':<40}  {'Sources':>7}  {'Updated'}")
    print("─" * 100)
    for nb in notebooks:
        pin = "★ " if nb.is_pinned else "  "
        title = f"{pin}{nb.display_title()}"
        print(f"{nb.id:<38}  {title[:40]:<40}  {nb.source_count:>7}  {_ts(nb.updated_at)}")


def print_notebook(nb: Notebook):
    pin = " [pinned]" if nb.is_pinned else ""
    print(f"ID:       {nb.id}")
    print(f"Title:    {nb.display_title()}{pin}")
    print(f"Sources:  {nb.source_count}")
    print(f"Created:  {_ts(nb.created_at)}")
    print(f"Updated:  {_ts(nb.updated_at)}")


def print_sources_table(sources: list[Source]):
    if not sources:
        print("No sources found.")
        return
    print(f"{'ID':<38}  {'Name':<40}  {'Type':<6}  {'Chars':>7}")
    print("─" * 100)
    for src in sources:
        print(f"{src.id:<38}  {src.name[:40]:<40}  {src.source_type:<6}  {src.char_count:>7}")


def print_source(src: Source):
    print(f"ID:      {src.id}")
    print(f"Name:    {src.name}")
    print(f"Type:    {src.source_type}")
    if src.url:
        print(f"URL:     {src.url}")
    print(f"Chars:   {src.char_count}")
    print(f"Added:   {_ts(src.created_at)}")


def print_user(user: User):
    print(f"Email:   {user.email}")
    print(f"Name:    {user.display_name}")


def print_artifact(artifact: Artifact):
    if artifact.title:
        print(f"Title:   {artifact.title}")
    print(f"Type:    {artifact.artifact_type}")
    print(f"ID:      {artifact.id or '(generated)'}")
    print()
    print(artifact.content)


def error(msg: str):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def json_success(data: Any) -> str:
    """Format a success response for --json mode."""
    return json.dumps({"success": True, "data": data}, ensure_ascii=False, indent=2, default=str)


def json_error(code: str, message: str, **extra) -> str:
    """Format an error response for --json mode."""
    response = {"error": True, "code": code, "message": message}
    response.update(extra)
    return json.dumps(response, ensure_ascii=False, indent=2)


def handle_error(exc: Exception, json_mode: bool = False) -> None:
    """Convert exception to CLI output — text or structured JSON.

    Call in command except blocks. Always exits with code 1.
    """
    from ..core.exceptions import error_code_for
    code = error_code_for(exc)
    if json_mode:
        print(json_error(code, str(exc)))
    else:
        print(f"Error: {exc}", file=sys.stderr)
    sys.exit(1)
