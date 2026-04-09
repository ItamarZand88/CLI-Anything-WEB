"""LinkedIn profile commands."""
from __future__ import annotations

import click

from ..core.client import LinkedinClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode


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

        # Extract profile elements from the response
        elements = data.get("elements", [data]) if isinstance(data, dict) else [data]
        prof = elements[0] if elements else data

        name_parts = []
        if prof.get("firstName"):
            name_parts.append(prof["firstName"])
        if prof.get("lastName"):
            name_parts.append(prof["lastName"])
        name = " ".join(name_parts) if name_parts else username

        click.echo(f"Name:        {name}")
        if prof.get("headline"):
            click.echo(f"Headline:    {prof['headline']}")
        if prof.get("locationName") or prof.get("geoLocationName"):
            location = prof.get("locationName") or prof.get("geoLocationName", "")
            click.echo(f"Location:    {location}")
        if prof.get("industryName"):
            click.echo(f"Industry:    {prof['industryName']}")
        if prof.get("summary"):
            click.echo(f"Summary:     {prof['summary']}")
        if prof.get("publicIdentifier"):
            click.echo(f"Profile URL: https://www.linkedin.com/in/{prof['publicIdentifier']}")


@profile.command("me")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def my_profile(ctx, json_mode):
    """View your own profile."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
            data = client._rest_get("me")

        if json_mode:
            print_json(data)
            return

        # /me response has data in miniProfile sub-object
        mp = data.get("miniProfile", data)
        name_parts = []
        if mp.get("firstName"):
            name_parts.append(mp["firstName"])
        if mp.get("lastName"):
            name_parts.append(mp["lastName"])
        name = " ".join(name_parts) if name_parts else "(unknown)"

        click.echo(f"Name:        {name}")
        headline = mp.get("occupation") or mp.get("headline") or data.get("headline") or ""
        if headline:
            click.echo(f"Headline:    {headline}")
        location = data.get("locationName") or data.get("geoLocationName") or ""
        if location:
            click.echo(f"Location:    {location}")
        if data.get("industryName"):
            click.echo(f"Industry:    {data['industryName']}")
        slug = mp.get("publicIdentifier") or data.get("vanityName") or ""
        if slug:
            click.echo(f"Profile URL: https://www.linkedin.com/in/{slug}")
