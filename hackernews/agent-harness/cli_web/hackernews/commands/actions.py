"""Actions command group — upvote, submit, comment, favorite, hide (auth required)."""

from __future__ import annotations

import click

from cli_web.hackernews.core import auth
from cli_web.hackernews.core.client import HackerNewsClient
from cli_web.hackernews.utils.helpers import handle_errors, print_json, resolve_json_mode


def _auth_client() -> HackerNewsClient:
    """Create an authenticated client."""
    cookie = auth.get_user_cookie()
    return HackerNewsClient(user_cookie=cookie)


@click.command("upvote")
@click.argument("item_id", type=int)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def upvote_cmd(ctx, item_id, json_mode):
    """Upvote a story or comment by ID. (Requires auth)"""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = _auth_client()
        result = client.upvote(item_id)
        if json_mode:
            print_json(result)
        else:
            click.echo(f"Upvoted item {item_id}")


@click.command("submit")
@click.option("--title", "-t", required=True, help="Story title.")
@click.option("--url", "-u", default=None, help="URL to submit (leave blank for Ask HN).")
@click.option("--text", default=None, help="Text body (for Ask HN or to add context).")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def submit_cmd(ctx, title, url, text, json_mode):
    """Submit a new story to Hacker News. (Requires auth)

    Use --url for link submissions, or leave blank for Ask HN (text only).
    """
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = _auth_client()
        result = client.submit_story(title=title, url=url, text=text)
        if json_mode:
            print_json(result)
        else:
            kind = "link" if url else "Ask HN"
            click.echo(f"Submitted {kind}: {title}")


@click.command("comment")
@click.argument("parent_id", type=int)
@click.argument("text")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def comment_cmd(ctx, parent_id, text, json_mode):
    """Post a comment on a story or reply to a comment. (Requires auth)

    PARENT_ID is the story or comment ID to reply to.
    TEXT is the comment body.
    """
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = _auth_client()
        result = client.post_comment(parent_id=parent_id, text=text)
        if json_mode:
            print_json(result)
        else:
            click.echo(f"Comment posted on item {parent_id}")


@click.command("favorite")
@click.argument("item_id", type=int)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def favorite_cmd(ctx, item_id, json_mode):
    """Favorite (save) a story. (Requires auth)"""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = _auth_client()
        result = client.favorite(item_id)
        if json_mode:
            print_json(result)
        else:
            click.echo(f"Favorited item {item_id}")


@click.command("hide")
@click.argument("item_id", type=int)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def hide_cmd(ctx, item_id, json_mode):
    """Hide a story from your feed. (Requires auth)"""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = _auth_client()
        result = client.hide(item_id)
        if json_mode:
            print_json(result)
        else:
            click.echo(f"Hidden item {item_id}")
