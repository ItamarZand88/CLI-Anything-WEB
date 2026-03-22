"""Output formatting for cli-web-stitch."""
import json
from datetime import datetime, timezone
from typing import Any, Optional

from rich.table import Table
from rich.console import Console

from ..core.models import Project, Screen

_console = Console()


# ── JSON helpers ──────────────────────────────────────────────────────

def json_success(data: Any) -> dict:
    """Wrap data in a success envelope."""
    return {"success": True, "data": data}


def json_error(code: str, message: str, **extra) -> dict:
    """Wrap an error in a structured envelope."""
    result = {"error": True, "code": code, "message": message}
    result.update(extra)
    return result


def print_json(obj: Any):
    """Pretty-print a JSON-serialisable object."""
    print(json.dumps(obj, indent=2, default=str))


# ── Timestamp formatting ─────────────────────────────────────────────

def _fmt_ts(epoch: Optional[float]) -> str:
    if epoch is None:
        return ""
    try:
        dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError, OverflowError):
        return ""


# ── Project formatting ───────────────────────────────────────────────

def _project_to_dict(project: Project) -> dict:
    return {
        "id": project.id,
        "resource_name": project.resource_name,
        "title": project.title,
        "created_at": project.created_at,
        "modified_at": project.modified_at,
        "status": project.status,
        "thumbnail_url": project.thumbnail_url,
        "theme_mode": project.theme_mode,
        "owner": project.owner,
    }


def format_project(project: Project, json_mode: bool = False):
    """Format a single project for display."""
    if json_mode:
        print_json(json_success(_project_to_dict(project)))
        return

    url = f"https://stitch.withgoogle.com/projects/{project.id}"
    status = STATUS_LABELS.get(project.status, str(project.status))
    _console.print(f"[bold cyan]{project.title or '(untitled)'}[/]  [dim]({status})[/]")
    _console.print(f"  ID:  {project.id}")
    if project.created_at or project.modified_at:
        parts = []
        if project.created_at:
            parts.append(f"Created {_fmt_ts(project.created_at)}")
        if project.modified_at:
            parts.append(f"Modified {_fmt_ts(project.modified_at)}")
        _console.print(f"  {' · '.join(parts)}")
    _console.print(f"  [link={url}]{url}[/link]")


# ── Screen formatting ────────────────────────────────────────────────

def _screen_to_dict(screen: Screen) -> dict:
    return {
        "id": screen.id,
        "name": screen.name,
        "description": screen.description,
        "resource_name": screen.resource_name,
        "thumbnail_url": screen.thumbnail_url,
        "html_url": screen.html_url,
        "agent_name": screen.agent_name,
        "width": screen.width,
        "height": screen.height,
    }


def format_screen(screen: Screen, json_mode: bool = False):
    """Format a single screen for display."""
    if json_mode:
        print_json(json_success(_screen_to_dict(screen)))
        return

    _console.print(f"[bold cyan]Screen:[/] {screen.name or screen.id}")
    _console.print(f"  ID:          {screen.id}")
    if screen.description:
        _console.print(f"  Description: {screen.description}")
    _console.print(f"  Size:        {screen.width}x{screen.height}")
    if screen.agent_name:
        _console.print(f"  Agent:       {screen.agent_name}")
    if screen.html_url:
        _console.print(f"  HTML URL:    {screen.html_url}")


# ── Status labels ─────────────────────────────────────────────────────

STATUS_LABELS = {0: "Unknown", 1: "Creating", 2: "Processing", 3: "Generating", 4: "Ready"}


# ── Tables ────────────────────────────────────────────────────────────

def format_projects_table(projects: list[Project]):
    """Print a rich table of projects."""
    table = Table(title="Projects", show_lines=False)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Modified", style="dim")
    table.add_column("Status", justify="center")

    for p in projects:
        table.add_row(
            p.id,
            p.title or "(untitled)",
            _fmt_ts(p.modified_at),
            STATUS_LABELS.get(p.status, str(p.status)),
        )

    _console.print(table)


def format_screens_table(screens: list[Screen]):
    """Print a rich table of screens."""
    table = Table(title="Screens", show_lines=False)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="white")
    table.add_column("Size", justify="right", style="dim")
    table.add_column("Agent", style="dim")

    for s in screens:
        table.add_row(
            s.id,
            s.name or "(unnamed)",
            f"{s.width}x{s.height}",
            s.agent_name or "",
        )

    _console.print(table)
