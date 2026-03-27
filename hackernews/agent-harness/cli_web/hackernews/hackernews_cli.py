"""cli-web-hackernews — CLI entry point for Hacker News."""

from __future__ import annotations

import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

import shlex

import click

from cli_web.hackernews.commands.actions import (
    comment_cmd,
    favorite_cmd,
    hide_cmd,
    submit_cmd,
    upvote_cmd,
)
from cli_web.hackernews.commands.auth import auth_group
from cli_web.hackernews.commands.search import search_group
from cli_web.hackernews.commands.stories import stories_group
from cli_web.hackernews.commands.user import user_group
from cli_web.hackernews.core.exceptions import AppError
from cli_web.hackernews.utils.repl_skin import ReplSkin

_skin = ReplSkin(app="hackernews", version="0.2.0", display_name="Hacker News")


# ---------------------------------------------------------------------------- main CLI


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON (applies to all commands).")
@click.version_option("0.2.0", prog_name="cli-web-hackernews")
@click.pass_context
def cli(ctx, json_mode):
    """cli-web-hackernews — Browse and interact with Hacker News from the command line.

    Run without arguments to enter interactive REPL mode.
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode

    if ctx.invoked_subcommand is None:
        _run_repl(ctx)


cli.add_command(stories_group)
cli.add_command(search_group)
cli.add_command(user_group)
cli.add_command(auth_group)
cli.add_command(upvote_cmd)
cli.add_command(submit_cmd)
cli.add_command(comment_cmd)
cli.add_command(favorite_cmd)
cli.add_command(hide_cmd)


# ---------------------------------------------------------------------------- REPL


def _print_repl_help() -> None:
    _skin.info("Available commands:")
    print()
    print("  stories top [OPTIONS]         Top stories (front page)")
    print("  stories new [OPTIONS]         Newest stories")
    print("  stories best [OPTIONS]        Best stories (all time)")
    print("  stories ask [OPTIONS]         Ask HN stories")
    print("  stories show [OPTIONS]        Show HN stories")
    print("  stories jobs [OPTIONS]        Job listings")
    print("  stories view ID [OPTIONS]     View story + comments")
    print("    -n, --limit N               Number of items (default 30/10)")
    print("    --json                      Output as JSON")
    print()
    print("  search stories QUERY          Search stories by keyword")
    print("  search comments QUERY         Search comments by keyword")
    print("    --sort-date                 Sort by date instead of relevance")
    print("    -n, --limit N               Number of results (default 20)")
    print("    --json                      Output as JSON")
    print()
    print("  user view USERNAME            View user profile")
    print("  user favorites [USERNAME]     View favorite stories (auth)")
    print("  user submissions [USERNAME]   View submitted stories (auth)")
    print("  user threads [USERNAME]       View replies to comments (auth)")
    print("    -n, --limit N               Number of items (default 30)")
    print("    --json                      Output as JSON")
    print()
    print("  upvote ID                     Upvote a story or comment (auth)")
    print("  submit -t TITLE [-u URL]      Submit a new story (auth)")
    print("  comment PARENT_ID TEXT        Post a comment or reply (auth)")
    print("  favorite ID                   Favorite/save a story (auth)")
    print("  hide ID                       Hide a story from feed (auth)")
    print("    --json                      Output as JSON")
    print()
    print("  auth login                    Login with username/password")
    print("  auth login-browser            Login via browser window")
    print("  auth status                   Check login status")
    print("  auth logout                   Remove credentials")
    print()
    print("  help                          Show this help")
    print("  exit / quit / Ctrl-D          Exit REPL")
    print()


def _run_repl(ctx: click.Context) -> None:
    _skin.print_banner()
    _print_repl_help()

    pt_session = _skin.create_prompt_session()

    while True:
        try:
            line = _skin.get_input(pt_session)
        except (EOFError, KeyboardInterrupt):
            _skin.print_goodbye()
            break

        line = line.strip()
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            _skin.print_goodbye()
            break
        if line.lower() in ("help", "?", "h"):
            _print_repl_help()
            continue

        try:
            args = shlex.split(line)
        except ValueError as exc:
            _skin.error(f"Parse error: {exc}")
            continue

        # Preserve --json flag from context
        if ctx.obj.get("json"):
            args = ["--json"] + args

        try:
            cli.main(args=args, standalone_mode=False)
        except SystemExit:
            pass
        except AppError as exc:
            _skin.error(exc.message)
        except Exception as exc:
            _skin.error(str(exc))


def main():
    cli()


if __name__ == "__main__":
    main()
