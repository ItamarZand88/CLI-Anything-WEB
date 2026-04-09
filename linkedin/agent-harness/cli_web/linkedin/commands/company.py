"""LinkedIn company commands."""
from __future__ import annotations

import click

from ..core.client import LinkedinClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode


def _get_text(obj, *keys) -> str:
    """Safely drill into nested dicts and return a string."""
    current = obj
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return ""
    if isinstance(current, dict):
        return current.get("text", str(current))
    return str(current) if current else ""


@click.group("company", invoke_without_command=True)
@click.argument("name", required=False)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def company(ctx, name, json_mode):
    """View a company page, or follow/unfollow companies."""
    ctx.ensure_object(dict)
    if json_mode:
        ctx.obj["json"] = True
    if ctx.invoked_subcommand is not None:
        return
    if not name:
        click.echo(ctx.get_help())
        return
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
            # Use search to get rich company data (GraphQL company returns minimal stub)
            data = client.search_companies(name, count=1)

        if json_mode:
            print_json(data)
            return

        # Resolve entity results from included
        included_index: dict[str, dict] = {}
        for inc in data.get("included", []):
            urn = inc.get("entityUrn", "")
            if urn:
                included_index[urn] = inc

        # Find the first entity result
        comp = {}
        gql = data.get("data", {})
        if "data" in gql and isinstance(gql["data"], dict):
            gql = gql["data"]
        for val in gql.values():
            if isinstance(val, dict) and "elements" in val:
                for el in val["elements"]:
                    for item in el.get("items", []):
                        inner = item.get("item", {})
                        ptr = inner.get("*entityResult", "")
                        if ptr and ptr in included_index:
                            comp = included_index[ptr]
                            break
                    if comp:
                        break

        if not comp:
            click.echo(f"Company '{name}' not found.")
            return

        display_name = _get_text(comp, "title", "text") or _get_text(comp, "title") or name
        industry = _get_text(comp, "primarySubtitle", "text") or _get_text(comp, "primarySubtitle")
        info = _get_text(comp, "secondarySubtitle", "text") or _get_text(comp, "secondarySubtitle")

        click.echo(f"Company:     {display_name}")
        if industry:
            click.echo(f"Industry:    {industry}")
        if info:
            click.echo(f"Info:        {info}")
        click.echo(f"LinkedIn:    https://www.linkedin.com/company/{name}")


@company.command("follow")
@click.argument("company_urn")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def follow(ctx, company_urn, json_mode):
    """Follow a company by URN."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
            client.follow_company(company_urn)
        if json_mode:
            print_json({"success": True, "followed": company_urn})
        else:
            click.echo("  Company followed.")


@company.command("unfollow")
@click.argument("company_urn")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def unfollow(ctx, company_urn, json_mode):
    """Unfollow a company by URN."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode):
        with LinkedinClient() as client:
            client.unfollow_company(company_urn)
        if json_mode:
            print_json({"success": True, "unfollowed": company_urn})
        else:
            click.echo("  Company unfollowed.")
