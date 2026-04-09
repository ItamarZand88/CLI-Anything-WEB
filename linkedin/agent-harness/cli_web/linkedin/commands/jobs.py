"""LinkedIn jobs commands."""
from __future__ import annotations

import click

from ..core.client import LinkedinClient
from ..utils.helpers import get_text, handle_errors, print_json, resolve_json_mode


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
                        "title": get_text(c, "jobPostingTitle") or get_text(c, "title"),
                        "company": get_text(c, "primaryDescription") or get_text(c, "companyName"),
                        "location": get_text(c, "secondaryDescription") or get_text(c, "formattedLocation"),
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
            title = get_text(c, "jobPostingTitle") or get_text(c, "title")
            company = get_text(c, "primaryDescription") or get_text(c, "companyName")
            location = get_text(c, "secondaryDescription") or get_text(c, "formattedLocation")
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
    """View full job details by ID."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
            data = client.get_job(job_id)

        if json_mode:
            print_json(data)
            return

        # The dash job posting endpoint returns fields directly in data
        job = data.get("data", data)

        title = get_text(job, "title")
        location = get_text(job, "formattedLocation")

        # Company name may be in included or in companyResolutionResult
        company = ""
        for inc in data.get("included", []):
            if inc.get("name") and "Company" in inc.get("$type", ""):
                company = inc["name"]
                break

        click.echo(f"  Title:       {title or job_id}")
        if company:
            click.echo(f"  Company:     {company}")
        if location:
            click.echo(f"  Location:    {location}")

        # Description
        desc = job.get("description", "")
        if isinstance(desc, dict):
            desc = desc.get("text", "")
        if desc:
            click.echo(f"\n  Description:")
            for line in desc[:500].split("\n"):
                click.echo(f"    {line}")
            if len(desc) > 500:
                click.echo("    ...")
