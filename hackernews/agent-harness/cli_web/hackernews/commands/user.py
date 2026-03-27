"""User command — view HN user profiles, favorites, and submissions."""

from __future__ import annotations

import click

from cli_web.hackernews.core import auth
from cli_web.hackernews.core.client import HackerNewsClient
from cli_web.hackernews.utils.helpers import handle_errors, resolve_json_mode
from cli_web.hackernews.utils.output import print_comments_list, print_json, print_stories_table, print_user_profile


@click.group("user")
def user_group():
    """View Hacker News user profiles."""


@user_group.command("view")
@click.argument("username")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def user_view(ctx, username, json_mode):
    """View a user's profile by username."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = HackerNewsClient()
        user = client.get_user(username)
        if json_mode:
            print_json(user.to_dict())
        else:
            click.echo(f"\nUser Profile: {username}\n")
            print_user_profile(user)
            click.echo()


@user_group.command("favorites")
@click.argument("username", required=False)
@click.option("-n", "--limit", default=30, show_default=True, help="Number of items to show.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def user_favorites(ctx, username, limit, json_mode):
    """View a user's favorite stories. (Requires auth)

    If USERNAME is omitted, shows your own favorites.
    """
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        if not username:
            username = auth.get_username()
        cookie = auth.get_user_cookie()
        client = HackerNewsClient(user_cookie=cookie)
        stories = client.get_favorites(username, limit=limit)
        if json_mode:
            print_json([s.to_dict() for s in stories])
        else:
            click.echo(f"\n{username}'s Favorites\n")
            print_stories_table(stories)
            click.echo(f"\n{len(stories)} stories\n")


@user_group.command("submissions")
@click.argument("username", required=False)
@click.option("-n", "--limit", default=30, show_default=True, help="Number of items to show.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def user_submissions(ctx, username, limit, json_mode):
    """View a user's submitted stories. (Requires auth)

    If USERNAME is omitted, shows your own submissions.
    """
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        if not username:
            username = auth.get_username()
        cookie = auth.get_user_cookie()
        client = HackerNewsClient(user_cookie=cookie)
        stories = client.get_submissions(username, limit=limit)
        if json_mode:
            print_json([s.to_dict() for s in stories])
        else:
            click.echo(f"\n{username}'s Submissions\n")
            print_stories_table(stories)
            click.echo(f"\n{len(stories)} stories\n")


@user_group.command("threads")
@click.argument("username", required=False)
@click.option("-n", "--limit", default=20, show_default=True, help="Number of comments to show.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def user_threads(ctx, username, limit, json_mode):
    """View comment replies to a user (your threads). (Requires auth)

    If USERNAME is omitted, shows replies to your own comments.
    """
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        if not username:
            username = auth.get_username()
        cookie = auth.get_user_cookie()
        client = HackerNewsClient(user_cookie=cookie)
        comments = client.get_threads(username, limit=limit)
        if json_mode:
            print_json([c.to_dict() for c in comments])
        else:
            click.echo(f"\n{username}'s Threads (replies)\n")
            print_comments_list(comments)
            click.echo(f"\n{len(comments)} comments\n")
