"""LinkedIn company command."""
from __future__ import annotations

import click

from ..core.client import LinkedinClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode


@click.command("company")
@click.argument("name")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def company(ctx, name, json_mode):
    """View a company page."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
            data = client.get_company(name)

        if json_mode:
            print_json(data)
            return

        # Extract company info from the response
        elements = data.get("elements", [data]) if isinstance(data, dict) else [data]
        comp = elements[0] if elements else data

        display_name = comp.get("name") or comp.get("universalName") or name
        click.echo(f"Company:     {display_name}")
        if comp.get("tagline"):
            click.echo(f"Tagline:     {comp['tagline']}")
        if comp.get("description"):
            desc = comp["description"]
            # Truncate long descriptions for terminal display
            if len(desc) > 300:
                desc = desc[:297] + "..."
            click.echo(f"Description: {desc}")
        if comp.get("industryV2Name") or comp.get("companyIndustries"):
            industry = comp.get("industryV2Name", "")
            if not industry and comp.get("companyIndustries"):
                industries = comp["companyIndustries"]
                if isinstance(industries, list) and industries:
                    industry = industries[0].get("localizedName", "")
            click.echo(f"Industry:    {industry}")
        if comp.get("staffCount") or comp.get("staffCountRange"):
            staff = comp.get("staffCount") or comp.get("staffCountRange", "")
            click.echo(f"Employees:   {staff}")
        if comp.get("followerCount"):
            click.echo(f"Followers:   {comp['followerCount']:,}")
        if comp.get("websiteUrl") or comp.get("companyPageUrl"):
            url = comp.get("websiteUrl") or comp.get("companyPageUrl", "")
            click.echo(f"Website:     {url}")
        if comp.get("universalName"):
            click.echo(
                f"LinkedIn:    https://www.linkedin.com/company/{comp['universalName']}"
            )
