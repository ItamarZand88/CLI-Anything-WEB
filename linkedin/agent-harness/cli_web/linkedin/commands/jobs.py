"""LinkedIn jobs commands."""
from __future__ import annotations

import click

from ..core.client import LinkedinClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode


def _get_text(obj, *keys) -> str:
    """Safely drill into nested dicts."""
    current = obj
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return ""
    if isinstance(current, dict):
        return current.get("text", str(current))
    return str(current) if current else ""


def _extract_job_cards(data: dict) -> list[dict]:
    """Extract job cards from the Voyager job search response.

    Handles both direct values and REST.li ``*jobPostingCard`` pointers
    that reference objects in the ``included`` array.
    """
    # Build included index for pointer resolution
    included_index: dict[str, dict] = {}
    for inc in data.get("included", []):
        urn = inc.get("entityUrn", "")
        if urn:
            included_index[urn] = inc

    elements = data.get("elements", [])
    if not elements:
        elements = data.get("data", {}).get("elements", [])

    cards = []
    for el in elements:
        jcu = el.get("jobCardUnion", {})
        if not jcu:
            continue
        # Direct value
        card = jcu.get("jobPostingCard")
        if isinstance(card, dict):
            cards.append(card)
            continue
        # Pointer: *jobPostingCard → resolve from included
        ptr = jcu.get("*jobPostingCard", "")
        if ptr and ptr in included_index:
            cards.append(included_index[ptr])
    return cards


@click.group("jobs")
def jobs():
    """Search and view jobs."""


@jobs.command("search")
@click.argument("query")
@click.option("--limit", default=10, help="Maximum number of results.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def search_jobs(ctx, query, limit, json_mode):
    """Search for jobs."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
            data = client.search_jobs(query, count=limit)
        cards = _extract_job_cards(data)

        if json_mode:
            print_json({
                "success": True,
                "count": len(cards),
                "jobs": [
                    {
                        "title": _get_text(c, "jobPostingTitle") or _get_text(c, "title"),
                        "company": _get_text(c, "primaryDescription") or _get_text(c, "companyName"),
                        "location": _get_text(c, "secondaryDescription") or _get_text(c, "formattedLocation"),
                        "urn": c.get("entityUrn", ""),
                        "job_id": c.get("entityUrn", "").split("(")[1].split(",")[0]
                            if "(" in c.get("entityUrn", "") else "",
                    }
                    for c in cards
                ],
            })
            return

        if not cards:
            click.echo(f"No jobs found for '{query}'.")
            return

        click.echo(f"Jobs for '{query}':\n")
        for i, c in enumerate(cards[:limit], 1):
            title = _get_text(c, "jobPostingTitle") or _get_text(c, "title")
            company = _get_text(c, "primaryDescription") or _get_text(c, "companyName")
            location = _get_text(c, "secondaryDescription") or _get_text(c, "formattedLocation")
            urn = c.get("entityUrn", "")
            job_id = urn.split("(")[1].split(",")[0] if "(" in urn else ""
            click.echo(f"  {i}. {title}")
            click.echo(f"     {company} | {location}")
            if job_id:
                click.echo(f"     ID: {job_id}")
            click.echo()


@jobs.command("get")
@click.argument("job_id")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def get_job(ctx, job_id, json_mode):
    """View job details by ID (from search results)."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
            data = client.get_job(job_id)

        if json_mode:
            print_json(data)
            return

        title = _get_text(data, "jobPostingTitle") or _get_text(data, "title")
        company = _get_text(data, "primaryDescription") or _get_text(data, "companyName")
        location = _get_text(data, "secondaryDescription") or _get_text(data, "formattedLocation")

        click.echo(f"  Title:    {title}")
        click.echo(f"  Company:  {company}")
        click.echo(f"  Location: {location}")

        # Show footer items (benefits, workplace type, etc.)
        for item in data.get("footerItems", []):
            if isinstance(item, dict):
                label = _get_text(item, "title")
                if label:
                    click.echo(f"  Info:     {label}")
