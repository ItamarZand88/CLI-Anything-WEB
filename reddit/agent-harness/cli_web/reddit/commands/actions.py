"""Action commands for cli-web-reddit — vote, save, hide, comment, submit, edit, delete."""

from __future__ import annotations

import click

from ..core.client import RedditClient
from ..core.exceptions import SubmitError
from ..utils.helpers import handle_errors, print_json, resolve_json_mode

# ── Vote ──────────────────────────────────────────────────────


@click.group("vote")
def vote():
    """Vote on posts and comments (requires login)."""


@vote.command("up")
@click.argument("thing_id")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def up(thing_id, use_json):
    """Upvote a post or comment. Pass the fullname (t3_xxx or t1_xxx)."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        client.vote(thing_id, 1)
        if use_json:
            print_json({"success": True, "action": "upvote", "id": thing_id})
        else:
            click.echo(f"  Upvoted {thing_id}")


@vote.command("down")
@click.argument("thing_id")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def down(thing_id, use_json):
    """Downvote a post or comment."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        client.vote(thing_id, -1)
        if use_json:
            print_json({"success": True, "action": "downvote", "id": thing_id})
        else:
            click.echo(f"  Downvoted {thing_id}")


@vote.command("unvote")
@click.argument("thing_id")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def unvote(thing_id, use_json):
    """Remove vote from a post or comment."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        client.vote(thing_id, 0)
        if use_json:
            print_json({"success": True, "action": "unvote", "id": thing_id})
        else:
            click.echo(f"  Removed vote on {thing_id}")


# ── Submit ────────────────────────────────────────────────────


@click.group("submit")
def submit():
    """Submit posts to subreddits (requires login)."""


@submit.command("flairs")
@click.argument("subreddit")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def submit_flairs(subreddit, use_json):
    """List available post flairs for a subreddit.

    Example: submit flairs ClaudeCode
    """
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        flairs = client.get_subreddit_flairs(subreddit)
        if use_json:
            print_json({"success": True, "subreddit": subreddit, "flairs": flairs})
        else:
            if not flairs:
                click.echo(f"  No flairs available for r/{subreddit}")
            else:
                click.echo(f"  Flairs for r/{subreddit}:")
                for f in flairs:
                    click.echo(f"    {f['id']}  {f['text']}")


@submit.command("text")
@click.argument("subreddit")
@click.argument("title")
@click.argument("body")
@click.option(
    "--flair", "flair_id", default=None, help="Flair ID (use 'submit flairs <sub>' to list)."
)
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def submit_text(subreddit, title, body, flair_id, use_json):
    """Submit a text (self) post.

    Example: submit text python "My Title" "Post body here"
    Example with flair: submit text ClaudeCode "Title" "Body" --flair abc123
    """
    use_json = resolve_json_mode(use_json)
    # Decode escape sequences so \n from CLI becomes actual newlines
    body = body.encode("utf-8").decode("unicode_escape") if "\\n" in body else body
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        result = client.submit_text(subreddit, title, body, flair_id=flair_id)
        data = result.get("json", {}).get("data", {})
        errors = result.get("json", {}).get("errors", [])
        if errors:
            msg = "; ".join(str(e) for e in errors)
            raise SubmitError(f"Submit failed: {msg}")
        if use_json:
            print_json(
                {
                    "success": True,
                    "id": data.get("name", ""),
                    "url": data.get("url", ""),
                }
            )
        else:
            click.echo(f"  Posted to r/{subreddit}: {data.get('url', '')}")


@submit.command("link")
@click.argument("subreddit")
@click.argument("title")
@click.argument("url")
@click.option(
    "--flair", "flair_id", default=None, help="Flair ID (use 'submit flairs <sub>' to list)."
)
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def submit_link(subreddit, title, url, flair_id, use_json):
    """Submit a link post.

    Example: submit link python "Check this out" "https://example.com"
    Example with flair: submit link ClaudeCode "Title" "https://..." --flair abc123
    """
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        result = client.submit_link(subreddit, title, url, flair_id=flair_id)
        data = result.get("json", {}).get("data", {})
        errors = result.get("json", {}).get("errors", [])
        if errors:
            msg = "; ".join(str(e) for e in errors)
            raise SubmitError(f"Submit failed: {msg}")
        if use_json:
            print_json(
                {
                    "success": True,
                    "id": data.get("name", ""),
                    "url": data.get("url", ""),
                }
            )
        else:
            click.echo(f"  Posted to r/{subreddit}: {data.get('url', '')}")


# ── Comment ───────────────────────────────────────────────────


@click.group("comment")
def comment_group():
    """Comment on posts and reply to comments (requires login)."""


@comment_group.command("add")
@click.argument("thing_id")
@click.argument("text")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def add_comment(thing_id, text, use_json):
    """Add a comment to a post or reply to a comment.

    thing_id: fullname of the post (t3_xxx) or comment (t1_xxx) to reply to.
    """
    use_json = resolve_json_mode(use_json)
    # Decode escape sequences so \n from CLI becomes actual newlines
    text = text.encode("utf-8").decode("unicode_escape") if "\\n" in text else text
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        result = client.comment(thing_id, text)
        things = result.get("json", {}).get("data", {}).get("things", [])
        comment_id = things[0].get("data", {}).get("name", "") if things else ""
        errors = result.get("json", {}).get("errors", [])
        if errors:
            msg = "; ".join(str(e) for e in errors)
            raise SubmitError(f"Comment failed: {msg}")
        if use_json:
            print_json({"success": True, "comment_id": comment_id})
        else:
            click.echo(f"  Comment posted: {comment_id}")


@comment_group.command("edit")
@click.argument("thing_id")
@click.argument("text")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def edit_comment(thing_id, text, use_json):
    """Edit your own post or comment text."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        client.edit(thing_id, text)
        if use_json:
            print_json({"success": True, "action": "edit", "id": thing_id})
        else:
            click.echo(f"  Edited {thing_id}")


@comment_group.command("delete")
@click.argument("thing_id")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def delete_thing(thing_id, use_json):
    """Delete your own post or comment."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        client.delete(thing_id)
        if use_json:
            print_json({"success": True, "action": "delete", "id": thing_id})
        else:
            click.echo(f"  Deleted {thing_id}")


# ── Save ──────────────────────────────────────────────────────


@click.group("saved")
def saved_group():
    """Save and unsave posts (requires login)."""


@saved_group.command("save")
@click.argument("thing_id")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def save_thing(thing_id, use_json):
    """Save a post or comment."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        client.save(thing_id)
        if use_json:
            print_json({"success": True, "action": "save", "id": thing_id})
        else:
            click.echo(f"  Saved {thing_id}")


@saved_group.command("unsave")
@click.argument("thing_id")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON.")
def unsave_thing(thing_id, use_json):
    """Unsave a post or comment."""
    use_json = resolve_json_mode(use_json)
    with handle_errors(json_mode=use_json):
        client = RedditClient()
        client.unsave(thing_id)
        if use_json:
            print_json({"success": True, "action": "unsave", "id": thing_id})
        else:
            click.echo(f"  Unsaved {thing_id}")
