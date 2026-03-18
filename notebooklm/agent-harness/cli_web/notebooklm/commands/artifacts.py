"""Artifact commands: generate, download, list types."""
import json
import time

import click
from ..core.client import NotebookLMClient
from ..core.exceptions import NotebookLMError, RateLimitError
from ..core.rpc.types import ArtifactType
from ..utils.output import print_artifact, print_json
from ..utils.helpers import handle_errors, require_notebook, sanitize_filename


ARTIFACT_TYPE_MAP = {
    "mindmap": ArtifactType.MIND_MAP,
    "study-guide": ArtifactType.STUDY_GUIDE,
    "briefing": ArtifactType.BRIEFING_DOC,
    "faq": ArtifactType.FAQ,
    "timeline": ArtifactType.TIMELINE,
}


def _retry_on_rate_limit(fn, max_retries=3):
    """Retry a function on RateLimitError with exponential backoff."""
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except RateLimitError as e:
            if attempt == max_retries:
                raise
            delay = e.retry_after or (60 * (2 ** attempt))
            delay = min(delay, 300)
            click.echo(
                f"  Rate limited. Retrying in {delay:.0f}s "
                f"(attempt {attempt + 1}/{max_retries})...",
                err=True,
            )
            time.sleep(delay)


@click.group()
def artifacts():
    """Generate and download artifacts from a notebook."""
    pass


@artifacts.command("generate")
@click.option("--notebook", default=None, help="Notebook ID (or use current context).")
@click.option(
    "--type", "artifact_type",
    type=click.Choice(list(ARTIFACT_TYPE_MAP.keys())),
    default="mindmap",
    show_default=True,
    help="Type of artifact to generate.",
)
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
@click.option("--wait", is_flag=True, default=False, help="Wait for generation to complete.")
@click.option("--retry", "max_retries", type=int, default=3, show_default=True,
              help="Max retries on rate limit.")
@click.option("--output", "-o", type=click.Path(), default=None,
              help="Save content to file.")
def generate(notebook, artifact_type, use_json, wait, max_retries, output):
    """Generate an artifact from a notebook."""
    with handle_errors(json_mode=use_json):
        nb_id = require_notebook(notebook)
        client = NotebookLMClient()
        mapped_type = ARTIFACT_TYPE_MAP[artifact_type]

        a = _retry_on_rate_limit(
            lambda: client.generate_artifact(nb_id, mapped_type),
            max_retries=max_retries,
        )

        if output and a.content:
            from pathlib import Path
            Path(output).write_text(a.content, encoding="utf-8")
            if not use_json:
                click.echo(f"Saved to {output}")

        if use_json:
            print_json({"id": a.id, "type": a.artifact_type, "content": a.content})
        else:
            print_artifact(a)


@artifacts.command("generate-notes")
@click.option("--notebook", default=None, help="Notebook ID (or use current context).")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
@click.option("--retry", "max_retries", type=int, default=3, show_default=True,
              help="Max retries on rate limit.")
@click.option("--output", "-o", type=click.Path(), default=None,
              help="Save content to file.")
def generate_notes(notebook, use_json, max_retries, output):
    """Generate study notes from a notebook."""
    with handle_errors(json_mode=use_json):
        nb_id = require_notebook(notebook)
        client = NotebookLMClient()

        a = _retry_on_rate_limit(
            lambda: client.generate_notes(nb_id),
            max_retries=max_retries,
        )

        if output and a.content:
            from pathlib import Path
            Path(output).write_text(a.content, encoding="utf-8")
            if not use_json:
                click.echo(f"Saved to {output}")

        if use_json:
            print_json({"id": a.id, "type": a.artifact_type, "content": a.content})
        else:
            print_artifact(a)


@artifacts.command("list-audio-types")
@click.option("--notebook", default=None, help="Notebook ID (or use current context).")
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON.")
def list_audio_types(notebook, use_json):
    """List available audio overview types for a notebook."""
    with handle_errors(json_mode=use_json):
        nb_id = require_notebook(notebook)
        client = NotebookLMClient()
        types = client.list_audio_types(nb_id)
        if use_json:
            print_json(types)
        else:
            for t in types:
                click.echo(f"{t['id']}: {t['name']} — {t['description']}")
