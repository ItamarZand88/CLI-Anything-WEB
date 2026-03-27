"""Stories command group — browse HN feeds (top, new, best, ask, show, job)."""

from __future__ import annotations

import click

from cli_web.hackernews.core.client import HackerNewsClient
from cli_web.hackernews.utils.helpers import handle_errors, resolve_json_mode
from cli_web.hackernews.utils.output import (
    print_comments_list,
    print_json,
    print_stories_table,
)


@click.group("stories")
def stories_group():
    """Browse Hacker News stories."""


@stories_group.command("top")
@click.option("-n", "--limit", default=30, show_default=True, help="Number of stories to show.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def stories_top(ctx, limit, json_mode):
    """Show top stories from the front page."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = HackerNewsClient()
        stories = client.get_stories("top", limit=limit)
        if json_mode:
            print_json([s.to_dict() for s in stories])
        else:
            click.echo("\nTop Stories\n")
            print_stories_table(stories)
            click.echo(f"\n{len(stories)} stories\n")


@stories_group.command("new")
@click.option("-n", "--limit", default=30, show_default=True, help="Number of stories to show.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def stories_new(ctx, limit, json_mode):
    """Show newest stories."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = HackerNewsClient()
        stories = client.get_stories("new", limit=limit)
        if json_mode:
            print_json([s.to_dict() for s in stories])
        else:
            click.echo("\nNew Stories\n")
            print_stories_table(stories)
            click.echo(f"\n{len(stories)} stories\n")


@stories_group.command("best")
@click.option("-n", "--limit", default=30, show_default=True, help="Number of stories to show.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def stories_best(ctx, limit, json_mode):
    """Show best stories (all time)."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = HackerNewsClient()
        stories = client.get_stories("best", limit=limit)
        if json_mode:
            print_json([s.to_dict() for s in stories])
        else:
            click.echo("\nBest Stories\n")
            print_stories_table(stories)
            click.echo(f"\n{len(stories)} stories\n")


@stories_group.command("ask")
@click.option("-n", "--limit", default=30, show_default=True, help="Number of stories to show.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def stories_ask(ctx, limit, json_mode):
    """Show Ask HN stories."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = HackerNewsClient()
        stories = client.get_stories("ask", limit=limit)
        if json_mode:
            print_json([s.to_dict() for s in stories])
        else:
            click.echo("\nAsk HN\n")
            print_stories_table(stories)
            click.echo(f"\n{len(stories)} stories\n")


@stories_group.command("show")
@click.option("-n", "--limit", default=30, show_default=True, help="Number of stories to show.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def stories_show(ctx, limit, json_mode):
    """Show Show HN stories."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = HackerNewsClient()
        stories = client.get_stories("show", limit=limit)
        if json_mode:
            print_json([s.to_dict() for s in stories])
        else:
            click.echo("\nShow HN\n")
            print_stories_table(stories)
            click.echo(f"\n{len(stories)} stories\n")


@stories_group.command("jobs")
@click.option("-n", "--limit", default=30, show_default=True, help="Number of stories to show.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def stories_jobs(ctx, limit, json_mode):
    """Show job stories."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = HackerNewsClient()
        stories = client.get_stories("job", limit=limit)
        if json_mode:
            print_json([s.to_dict() for s in stories])
        else:
            click.echo("\nJobs\n")
            print_stories_table(stories)
            click.echo(f"\n{len(stories)} stories\n")


@stories_group.command("view")
@click.argument("story_id", type=int)
@click.option("--comments/--no-comments", default=True, help="Show comments.")
@click.option("-n", "--limit", default=10, show_default=True, help="Number of comments to show.")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def stories_view(ctx, story_id, comments, limit, json_mode):
    """View a story and its comments by ID."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        client = HackerNewsClient()
        story = client.get_story(story_id)

        if json_mode:
            data = story.to_dict()
            if comments:
                cmts = client.get_comments(story_id, limit=limit)
                data["comments"] = [c.to_dict() for c in cmts]
            print_json(data)
        else:
            click.echo(f"\n  {story.title}")
            if story.url:
                click.echo(f"  {story.url}")
            click.echo(f"  {story.score} points by {story.by} | {story.age} | {story.descendants} comments")
            click.echo()

            if comments:
                cmts = client.get_comments(story_id, limit=limit)
                if cmts:
                    click.echo("  Comments:\n")
                    print_comments_list(cmts)
