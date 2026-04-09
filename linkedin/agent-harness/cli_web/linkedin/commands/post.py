"""Post commands for cli-web-linkedin."""
from __future__ import annotations

import click

from ..core.client import LinkedinClient
from ..utils.helpers import handle_errors, print_json, resolve_json_mode


@click.group("post")
def post():
    """Create, view, and manage posts."""


@post.command("create")
@click.argument("text")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def create_post(ctx, text, json_mode):
    """Publish a new text post."""
    json_mode = resolve_json_mode(json_mode, ctx)

    with handle_errors(json_mode=json_mode):
        with LinkedinClient() as client:
            result = client.create_post(text)

        if json_mode:
            print_json(result)
        else:
            click.secho("Post published successfully!", fg="green", bold=True)
            if result:
                urn = result.get("entityUrn") or result.get("urn") or ""
                if urn:
                    click.echo(f"URN: {urn}")


@post.command("react")
@click.argument("post_urn")
@click.option(
    "--type",
    "reaction_type",
    default="LIKE",
    type=click.Choice(
        ["LIKE", "PRAISE", "EMPATHY", "INTEREST", "APPRECIATION", "ENTERTAINMENT"]
    ),
    help="Reaction type (default: LIKE).",
)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def react(ctx, post_urn, reaction_type, json_mode):
    """React to a post."""
    json_mode = resolve_json_mode(json_mode, ctx)

    with handle_errors(json_mode=json_mode):
        with LinkedinClient() as client:
            result = client.react(post_urn, reaction_type)

        if json_mode:
            print_json({"success": True, "reaction": reaction_type, "post_urn": post_urn})
        else:
            click.secho(
                f"Reacted with {reaction_type} to {post_urn}", fg="green", bold=True
            )


@post.command("comment")
@click.argument("post_urn")
@click.argument("text")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def comment(ctx, post_urn, text, json_mode):
    """Comment on a post."""
    json_mode = resolve_json_mode(json_mode, ctx)

    with handle_errors(json_mode=json_mode):
        with LinkedinClient() as client:
            result = client.add_comment(post_urn, text)

        if json_mode:
            print_json(result if result else {"success": True, "post_urn": post_urn})
        else:
            click.secho("Comment posted successfully!", fg="green", bold=True)
            if result:
                urn = result.get("entityUrn") or result.get("urn") or ""
                if urn:
                    click.echo(f"Comment URN: {urn}")


@post.command("edit")
@click.argument("post_urn")
@click.argument("text")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def edit_post(ctx, post_urn, text, json_mode):
    """Edit an existing post."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode=json_mode):
        with LinkedinClient() as client:
            result = client.edit_post(post_urn, text)
        if json_mode:
            print_json({"success": True, "post_urn": post_urn})
        else:
            click.secho("Post updated.", fg="green")


@post.command("delete")
@click.argument("post_urn")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def delete_post(ctx, post_urn, json_mode):
    """Delete a post."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode=json_mode):
        with LinkedinClient() as client:
            client.delete_post(post_urn)
        if json_mode:
            print_json({"success": True, "deleted": post_urn})
        else:
            click.secho("Post deleted.", fg="green")


@post.command("unreact")
@click.argument("post_urn")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def unreact(ctx, post_urn, json_mode):
    """Remove your reaction from a post."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode=json_mode):
        with LinkedinClient() as client:
            client.unreact(post_urn)
        if json_mode:
            print_json({"success": True, "unreacted": post_urn})
        else:
            click.secho("Reaction removed.", fg="green")


@post.command("edit-comment")
@click.argument("comment_urn")
@click.argument("text")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def edit_comment(ctx, comment_urn, text, json_mode):
    """Edit a comment."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode=json_mode):
        with LinkedinClient() as client:
            client.edit_comment(comment_urn, text)
        if json_mode:
            print_json({"success": True, "comment_urn": comment_urn})
        else:
            click.secho("Comment updated.", fg="green")


@post.command("delete-comment")
@click.argument("comment_urn")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def delete_comment(ctx, comment_urn, json_mode):
    """Delete a comment."""
    json_mode = resolve_json_mode(json_mode, ctx)
    with handle_errors(json_mode=json_mode):
        with LinkedinClient() as client:
            client.delete_comment(comment_urn)
        if json_mode:
            print_json({"success": True, "deleted": comment_urn})
        else:
            click.secho("Comment deleted.", fg="green")
