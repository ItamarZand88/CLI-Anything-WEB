"""Artifact management commands (study guides, summaries, audio overviews)."""

from __future__ import annotations

from typing import Any

import click

from cli_web.notebooklm.core.client import NotebookLMClient
from cli_web.notebooklm.core.models import Artifact
from cli_web.notebooklm.utils.config import RPC_LIST_ARTIFACTS
from cli_web.notebooklm.utils.output import output_json, output_table, output_error, truncate


ARTIFACT_TYPES = ["study_guide", "summary", "faq", "timeline", "briefing", "audio_overview"]


def _parse_artifact(raw: Any, notebook_id: str = "") -> Artifact:
    """Parse a raw artifact entry."""
    if not isinstance(raw, list):
        return Artifact(id=str(raw), notebook_id=notebook_id)

    art_id = raw[0] if len(raw) > 0 else ""
    art_type = raw[1] if len(raw) > 1 and isinstance(raw[1], str) else ""
    title = raw[2] if len(raw) > 2 and isinstance(raw[2], str) else ""
    content = raw[3] if len(raw) > 3 and isinstance(raw[3], str) else ""
    status = raw[4] if len(raw) > 4 and isinstance(raw[4], str) else ""
    created_at = str(raw[5]) if len(raw) > 5 else ""

    return Artifact(
        id=str(art_id),
        artifact_type=art_type,
        title=title,
        content=content,
        status=status,
        created_at=created_at,
        notebook_id=notebook_id,
    )


@click.group("artifacts")
def artifacts_group():
    """Manage notebook artifacts (study guides, summaries, etc.)."""
    pass


@artifacts_group.command("list")
@click.argument("notebook_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def list_artifacts(notebook_id: str, as_json: bool):
    """List all artifacts for a notebook."""
    try:
        client = NotebookLMClient()
        payload = [
            [2, None, None,
             [1, None, None, None, None, None, None, None, None, None, [1]],
             [[2, 1, 3]]],
            notebook_id,
            'NOT artifact.status = "ARTIFACT_STATUS_SUGGESTED"',
        ]
        data = client.rpc(RPC_LIST_ARTIFACTS, payload)
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    artifacts = []
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, list):
                artifacts.append(_parse_artifact(entry, notebook_id))

    if as_json:
        output_json([a.to_dict() for a in artifacts])
        return

    if not artifacts:
        click.echo("No artifacts found.")
        return

    headers = ["ID", "Type", "Title", "Status"]
    rows = [
        [truncate(a.id, 20), a.artifact_type, truncate(a.title, 40), a.status]
        for a in artifacts
    ]
    output_table(headers, rows)


@artifacts_group.command("get")
@click.argument("notebook_id")
@click.argument("artifact_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def get_artifact(notebook_id: str, artifact_id: str, as_json: bool):
    """Get the content of a specific artifact."""
    try:
        client = NotebookLMClient()
        payload = [
            [2, None, None,
             [1, None, None, None, None, None, None, None, None, None, [1]],
             [[2, 1, 3]]],
            notebook_id,
            'NOT artifact.status = "ARTIFACT_STATUS_SUGGESTED"',
        ]
        data = client.rpc(RPC_LIST_ARTIFACTS, payload)
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    artifact = None
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, list) and len(entry) > 0 and str(entry[0]) == artifact_id:
                artifact = _parse_artifact(entry, notebook_id)
                break

    if artifact is None:
        output_error(f"Artifact {artifact_id} not found")
        raise SystemExit(1)

    if as_json:
        output_json(artifact.to_dict())
        return

    click.echo(f"Type:    {artifact.artifact_type}")
    click.echo(f"Title:   {artifact.title}")
    click.echo(f"Status:  {artifact.status}")
    click.echo()
    click.echo(artifact.content)


@artifacts_group.command("generate")
@click.argument("notebook_id")
@click.argument("artifact_type", type=click.Choice(ARTIFACT_TYPES))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def generate_artifact(notebook_id: str, artifact_type: str, as_json: bool):
    """Generate a new artifact for a notebook."""
    try:
        client = NotebookLMClient()
        # The generate artifact RPC
        data = client.rpc("pwrvEe", [notebook_id, artifact_type])
    except Exception as e:
        output_error(str(e))
        raise SystemExit(1)

    if as_json:
        output_json(data)
        return

    click.echo(f"Generating {artifact_type} for notebook {notebook_id}...")
    if isinstance(data, list) and data:
        art = _parse_artifact(data, notebook_id)
        click.echo(f"Artifact created: {art.id}")
    else:
        click.echo("Generation initiated. Check artifacts list for progress.")
