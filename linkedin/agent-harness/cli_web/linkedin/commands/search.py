"""Search commands for cli-web-linkedin."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from ..core.client import LinkedinClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode

console = Console()


# ---------------------------------------------------------------------------
# Helpers to extract display fields from LinkedIn search result elements
# ---------------------------------------------------------------------------

def _resolve_pointer(obj: dict, key: str, index: dict) -> dict | None:
    """Resolve a REST.li ``*key`` pointer against the included index."""
    # Direct value
    direct = obj.get(key)
    if isinstance(direct, dict):
        return direct
    # Pointer: *key → URN in included
    ptr = obj.get(f"*{key}", "")
    if ptr and ptr in index:
        return index[ptr]
    return None


def _extract_elements(data) -> list[dict]:
    """Pull search-result elements from various LinkedIn response formats.

    LinkedIn's REST.li responses use ``*field`` pointers that reference
    objects in the ``included`` array by ``entityUrn``.  We resolve these
    to get the actual display objects (EntityResultViewModel, JobPostingCard).
    """
    if isinstance(data, list):
        return data

    # Build a lookup of included entities by URN for pointer resolution
    included_index: dict[str, dict] = {}
    for inc in data.get("included", []):
        urn = inc.get("entityUrn", "")
        if urn:
            included_index[urn] = inc

    elements: list[dict] = []

    # Format 1: GraphQL searchDashClusters —
    #   data.data.searchDashClustersByAll.elements[].items[].item.*entityResult
    gql = data.get("data", {})
    # Handle double-nested data (GraphQL wraps in data.data)
    if "data" in gql and isinstance(gql["data"], dict):
        gql = gql["data"]
    for key, val in gql.items():
        if isinstance(val, dict) and "elements" in val:
            for el in val["elements"]:
                for item in el.get("items", []):
                    inner = item.get("item", {})
                    entity = _resolve_pointer(inner, "entityResult", included_index)
                    if entity:
                        elements.append(entity)
            if elements:
                return elements

    # Format 2: Job search — data.elements[].jobCardUnion.*jobPostingCard
    top_elements = data.get("elements", [])
    if not top_elements:
        top_elements = data.get("data", {}).get("elements", [])
    for el in top_elements:
        jcu = el.get("jobCardUnion", {})
        if jcu:
            card = _resolve_pointer(jcu, "jobPostingCard", included_index)
            if card:
                elements.append(card)
                continue
        # Format 3: Clusters at top level
        for item in el.get("items", []):
            inner = item.get("item", {})
            entity = _resolve_pointer(inner, "entityResult", included_index)
            if entity:
                elements.append(entity)

    # Format 4: included array — EntityResultViewModel objects
    if not elements:
        for inc in data.get("included", []):
            t = inc.get("$type", "")
            if "EntityResult" in t and "title" in inc:
                elements.append(inc)

    return elements


def _get_text(obj, *keys) -> str:
    """Safely drill into nested dicts / text accessors and return a string."""
    current = obj
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return ""
    if isinstance(current, dict):
        return current.get("text", str(current))
    return str(current) if current else ""


def _truncate(text: str, length: int = 60) -> str:
    if len(text) <= length:
        return text
    return text[: length - 1] + "\u2026"


# ---------------------------------------------------------------------------
# Click group
# ---------------------------------------------------------------------------

@click.group("search")
@click.pass_context
def search(ctx):
    """Search LinkedIn for people, jobs, companies, and posts."""
    ctx.ensure_object(dict)


# ---------------------------------------------------------------------------
# search all
# ---------------------------------------------------------------------------

@search.command("all")
@click.argument("query")
@click.option("--limit", default=10, type=int, show_default=True, help="Max results.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def search_all(ctx, query, limit, json_mode):
    """Run a general LinkedIn search for QUERY across all verticals."""
    json_mode = resolve_json_mode(json_mode, ctx)

    with handle_errors(json_mode=json_mode):
        with LinkedinClient() as client:
            # Unified search uses people search as default
            data = client.search_people(query, count=limit)
        results = _extract_elements(data)

        if json_mode:
            print_json({"success": True, "count": len(results), "results": results})
            return

        if not results:
            click.echo(f"No results found for '{query}'.")
            return

        table = Table(title=f"LinkedIn Search \u2014 {query}", show_lines=False, expand=False)
        table.add_column("#", style="dim", no_wrap=True, max_width=4)
        table.add_column("Title", max_width=50)
        table.add_column("Subtitle", max_width=40)
        table.add_column("URN", style="dim", max_width=50)

        for idx, el in enumerate(results[:limit], 1):
            title = _get_text(el, "title", "text") or _get_text(el, "title")
            subtitle = _get_text(el, "primarySubtitle", "text") or _get_text(el, "primarySubtitle")
            urn = el.get("entityUrn", el.get("trackingUrn", ""))
            table.add_row(str(idx), _truncate(title), _truncate(subtitle), _truncate(urn, 50))

        console.print(table)
        click.echo(f"\nFound {len(results)} result(s).")


# ---------------------------------------------------------------------------
# search people
# ---------------------------------------------------------------------------

@search.command("people")
@click.argument("query")
@click.option("--limit", default=10, type=int, show_default=True, help="Max results.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def search_people(ctx, query, limit, json_mode):
    """Search LinkedIn for people matching QUERY.

    Examples:

      cli-web-linkedin search people "software engineer"

      cli-web-linkedin search people "John Doe" --limit 5 --json
    """
    json_mode = resolve_json_mode(json_mode, ctx)

    with handle_errors(json_mode=json_mode):
        with LinkedinClient() as client:
            data = client.search_people(query, count=limit)
        results = _extract_elements(data)

        if json_mode:
            print_json({"success": True, "count": len(results), "results": results})
            return

        if not results:
            click.echo(f"No people found for '{query}'.")
            return

        table = Table(title=f"LinkedIn People \u2014 {query}", show_lines=False, expand=False)
        table.add_column("#", style="dim", no_wrap=True, max_width=4)
        table.add_column("Name", max_width=30)
        table.add_column("Headline", max_width=50)
        table.add_column("Location", max_width=25)

        for idx, el in enumerate(results[:limit], 1):
            name = _get_text(el, "title", "text") or _get_text(el, "title")
            headline = _get_text(el, "primarySubtitle", "text") or _get_text(el, "primarySubtitle")
            location = _get_text(el, "secondarySubtitle", "text") or _get_text(el, "secondarySubtitle")
            table.add_row(str(idx), _truncate(name, 30), _truncate(headline, 50), _truncate(location, 25))

        console.print(table)
        click.echo(f"\nFound {len(results)} people.")


# ---------------------------------------------------------------------------
# search jobs
# ---------------------------------------------------------------------------

@search.command("jobs")
@click.argument("query")
@click.option("--limit", default=10, type=int, show_default=True, help="Max results.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def search_jobs(ctx, query, limit, json_mode):
    """Search LinkedIn for jobs matching QUERY.

    Examples:

      cli-web-linkedin search jobs "python developer"

      cli-web-linkedin search jobs "data scientist" --limit 20 --json
    """
    json_mode = resolve_json_mode(json_mode, ctx)

    with handle_errors(json_mode=json_mode):
        with LinkedinClient() as client:
            data = client.search_jobs(query, count=limit)
        results = _extract_elements(data)

        if json_mode:
            print_json({"success": True, "count": len(results), "results": results})
            return

        if not results:
            click.echo(f"No jobs found for '{query}'.")
            return

        table = Table(title=f"LinkedIn Jobs \u2014 {query}", show_lines=False, expand=False)
        table.add_column("#", style="dim", no_wrap=True, max_width=4)
        table.add_column("Title", max_width=40)
        table.add_column("Company", max_width=30)
        table.add_column("Location", max_width=25)

        for idx, el in enumerate(results[:limit], 1):
            title = _get_text(el, "jobPostingTitle") or _get_text(el, "title") or ""
            company = _get_text(el, "primaryDescription", "text") or _get_text(el, "primaryDescription") or ""
            location = _get_text(el, "secondaryDescription", "text") or _get_text(el, "secondaryDescription") or ""
            table.add_row(str(idx), _truncate(title, 40), _truncate(company, 30), _truncate(location, 25))

        console.print(table)
        click.echo(f"\nFound {len(results)} job(s).")


# ---------------------------------------------------------------------------
# search companies
# ---------------------------------------------------------------------------

@search.command("companies")
@click.argument("query")
@click.option("--limit", default=10, type=int, show_default=True, help="Max results.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def search_companies(ctx, query, limit, json_mode):
    """Search LinkedIn for companies matching QUERY.

    Examples:

      cli-web-linkedin search companies "Google"

      cli-web-linkedin search companies "startup AI" --limit 5 --json
    """
    json_mode = resolve_json_mode(json_mode, ctx)

    with handle_errors(json_mode=json_mode):
        with LinkedinClient() as client:
            data = client.search_companies(query, count=limit)
        results = _extract_elements(data)

        if json_mode:
            print_json({"success": True, "count": len(results), "results": results})
            return

        if not results:
            click.echo(f"No companies found for '{query}'.")
            return

        table = Table(title=f"LinkedIn Companies \u2014 {query}", show_lines=False, expand=False)
        table.add_column("#", style="dim", no_wrap=True, max_width=4)
        table.add_column("Name", max_width=35)
        table.add_column("Industry", max_width=30)
        table.add_column("Info", max_width=30)

        for idx, el in enumerate(results[:limit], 1):
            name = _get_text(el, "title", "text") or _get_text(el, "title")
            industry = _get_text(el, "primarySubtitle", "text") or _get_text(el, "primarySubtitle")
            info = _get_text(el, "secondarySubtitle", "text") or _get_text(el, "secondarySubtitle")
            table.add_row(str(idx), _truncate(name, 35), _truncate(industry, 30), _truncate(info, 30))

        console.print(table)
        click.echo(f"\nFound {len(results)} company/companies.")
