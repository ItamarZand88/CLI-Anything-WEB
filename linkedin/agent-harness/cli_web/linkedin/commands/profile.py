"""LinkedIn profile commands."""
from __future__ import annotations

import click

from ..core.client import LinkedinClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode


def _find_profile(data: dict) -> dict:
    """Find the main profile object in a Voyager response.

    Checks: elements[], included[] (Profile type with firstName), then
    falls back to the top-level data dict.
    """
    # Direct elements
    elements = data.get("elements", [])
    if elements and elements[0].get("firstName"):
        return elements[0]

    # REST.li included array — find Profile with firstName
    for inc in data.get("included", []):
        t = inc.get("$type", "")
        if "Profile" in t and "firstName" in inc:
            return inc

    # Flat response (legacy)
    if data.get("firstName"):
        return data

    return {}


def _print_profile(prof: dict, fallback_name: str = "") -> None:
    """Pretty-print profile fields."""
    name_parts = []
    if prof.get("firstName"):
        name_parts.append(prof["firstName"])
    if prof.get("lastName"):
        name_parts.append(prof["lastName"])
    name = " ".join(name_parts) if name_parts else fallback_name

    click.echo(f"Name:        {name}")
    headline = prof.get("headline") or prof.get("occupation") or ""
    if headline:
        click.echo(f"Headline:    {headline}")
    location = prof.get("locationName") or prof.get("geoLocationName") or ""
    if location:
        click.echo(f"Location:    {location}")
    if prof.get("industryName"):
        click.echo(f"Industry:    {prof['industryName']}")
    if prof.get("summary"):
        summary = prof["summary"]
        if len(summary) > 300:
            summary = summary[:297] + "..."
        click.echo(f"Summary:     {summary}")
    slug = prof.get("publicIdentifier") or ""
    if slug:
        click.echo(f"Profile URL: https://www.linkedin.com/in/{slug}")


def _print_positions(data: dict) -> None:
    """Print work experience from included array."""
    positions = []
    for inc in data.get("included", []):
        t = inc.get("$type", "")
        if "Position" in t and "title" in inc:
            title = inc.get("title", "")
            company = inc.get("companyName", "")
            positions.append((title, company))

    if positions:
        click.echo()
        click.echo("Experience:")
        for title, company in positions[:5]:
            if company:
                click.echo(f"  - {title} at {company}")
            else:
                click.echo(f"  - {title}")
        if len(positions) > 5:
            click.echo(f"  ... and {len(positions) - 5} more")


@click.group("profile")
def profile():
    """View LinkedIn profiles."""


@profile.command("get")
@click.argument("username")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def get_profile(ctx, username, json_mode):
    """View a LinkedIn profile by username."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
            data = client.get_profile(username)

        if json_mode:
            print_json(data)
            return

        prof = _find_profile(data)
        _print_profile(prof, fallback_name=username)
        _print_positions(data)


@profile.command("me")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def my_profile(ctx, json_mode):
    """View your own profile."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
            data = client.get_me()

        if json_mode:
            print_json(data)
            return

        prof = _find_profile(data)
        _print_profile(prof, fallback_name="(unknown)")
