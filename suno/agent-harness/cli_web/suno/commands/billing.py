"""Billing and credits information for Suno."""

import click
from cli_web.suno.core.client import SunoClient
from cli_web.suno.core.models import BillingInfo
from cli_web.suno.utils.output import output_result, output_json


@click.group()
def billing():
    """Billing and credits information."""
    pass


@billing.command()
@click.pass_context
def info(ctx):
    """Show credits, plan, and usage limits."""
    as_json = ctx.obj.get("json", False)
    client = SunoClient()
    try:
        result = client.get_billing_info()
        bi = BillingInfo.from_dict(result)
        data = {
            "credits": bi.credits,
            "total_credits_left": bi.total_credits_left,
            "is_active": bi.is_active,
            "subscription_type": bi.subscription_type,
            "monthly_usage": bi.monthly_usage,
            "monthly_limit": bi.monthly_limit,
        }
        output_result(data, as_json=as_json)
    finally:
        client.close()


@billing.command()
@click.pass_context
def plans(ctx):
    """List available plans."""
    as_json = ctx.obj.get("json", False)
    client = SunoClient()
    try:
        result = client.get_billing_info()
        plans_data = result.get("plans", [])
        output_result(plans_data, as_json=as_json)
    finally:
        client.close()
