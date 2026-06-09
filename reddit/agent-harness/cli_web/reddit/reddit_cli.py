"""cli-web-reddit — CLI for Reddit browsing, search, and interaction."""

from __future__ import annotations

import shlex
import sys

# Windows UTF-8 fix
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass

import click

from .commands.actions import comment_group, saved_group, submit, vote
from .commands.auth_cmd import auth
from .commands.feed import feed
from .commands.me import me
from .commands.post import post
from .commands.search import search
from .commands.subreddit import sub
from .commands.user import user
from .utils.repl_skin import ReplSkin

_skin = ReplSkin("reddit", version="0.1.0")


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.option("--version", is_flag=True, help="Show version.")
@click.pass_context
def cli(ctx, json_mode, version):
    """Reddit browsing, search, and interaction CLI."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode
    if version:
        click.echo("cli-web-reddit 0.1.0")
        return
    if ctx.invoked_subcommand is None:
        _repl(ctx)


cli.add_command(feed)
cli.add_command(sub)
cli.add_command(search)
cli.add_command(user)
cli.add_command(post)
cli.add_command(auth)
cli.add_command(me)
cli.add_command(vote)
cli.add_command(submit)
cli.add_command(comment_group, "comment")
cli.add_command(saved_group, "saved")


def _print_repl_help():
    """Print REPL help listing all commands and key options."""
    _skin.info("Available commands:")
    print()
    _skin.section("Browse (no login needed)")
    print("  feed hot                  [--limit N] [--after CURSOR]")
    print("  feed new                  [--limit N] [--after CURSOR]")
    print("  feed top                  [--time hour|day|week|month|year|all] [--limit N]")
    print("  feed rising               [--limit N] [--after CURSOR]")
    print("  feed popular              [--limit N] [--after CURSOR]")
    print()
    print("  sub hot <name>            [--limit N] [--after CURSOR]")
    print("  sub new <name>            [--limit N] [--after CURSOR]")
    print("  sub top <name>            [--time day|week|month|year|all] [--limit N]")
    print("  sub info <name>           Subreddit details and stats")
    print("  sub rules <name>          Subreddit rules")
    print("  sub search <name> <query> [--sort relevance|hot|top|new|comments] [--limit N]")
    print()
    print("  search posts <query>      [--sort relevance|hot|top|new|comments]")
    print("                            [--time hour|day|week|month|year|all] [--limit N]")
    print("  search subs <query>       [--limit N] [--after CURSOR]")
    print()
    print("  user info <username>      User profile")
    print("  user posts <username>     [--sort hot|new|top] [--limit N]")
    print("  user comments <username>  [--sort hot|new|top] [--limit N]")
    print()
    print("  post get <url_or_id>      [--sub <name>] [--comments N]")
    print()
    _skin.section("Account (login required)")
    print("  auth login                Open browser to log in")
    print("  auth logout               Remove saved credentials")
    print("  auth status               Check login status")
    print()
    print("  me profile                Your Reddit profile")
    print("  me saved                  [--limit N]  Your saved posts")
    print("  me upvoted                [--limit N]  Your upvoted posts")
    print("  me subscriptions          Your subscribed subreddits")
    print("  me inbox                  [--limit N]  Your inbox messages")
    print()
    print("  vote up <id>              Upvote post/comment (t3_xxx or t1_xxx)")
    print("  vote down <id>            Downvote post/comment")
    print("  vote unvote <id>          Remove vote")
    print()
    print("  submit flairs <sub>                 List available post flairs")
    print("  submit text <sub> <title> <body>    Submit a text post [--flair ID]")
    print("  submit link <sub> <title> <url>     Submit a link post [--flair ID]")
    print()
    print("  comment add <id> <text>   Comment on a post or reply to comment")
    print("  comment edit <id> <text>  Edit your post/comment")
    print("  comment delete <id>       Delete your post/comment")
    print()
    print("  saved save <id>           Save a post/comment")
    print("  saved unsave <id>         Unsave a post/comment")
    print()
    print("  sub join <name>           Subscribe to subreddit")
    print("  sub leave <name>          Unsubscribe from subreddit")
    print()
    print("  help                      Show this help")
    print("  quit / exit               Exit REPL")
    print()


def _repl(ctx):
    """Interactive REPL mode."""
    _skin.print_banner()
    pt_session = _skin.create_prompt_session()

    while True:
        try:
            line = _skin.get_input(pt_session)
            if not line:
                continue
            if line.lower() in ("quit", "exit", "q"):
                _skin.print_goodbye()
                break
            if line.lower() in ("help", "?"):
                _print_repl_help()
                continue

            try:
                args = shlex.split(line)
            except ValueError as exc:
                _skin.error(f"Invalid input: {exc}")
                continue

            repl_args = ["--json"] + args if ctx.obj.get("json") else args
            try:
                cli.main(args=repl_args, standalone_mode=False)
            except SystemExit:
                pass
            except click.exceptions.UsageError as exc:
                _skin.error(str(exc))
            except Exception as exc:
                _skin.error(str(exc))

        except (KeyboardInterrupt, EOFError):
            _skin.print_goodbye()
            break


def main():
    cli()


# MCP server mode — exposes every command as an MCP tool over stdio.
# Canonical adapter: cli-web-core/cli_web_core/mcp_server.py (vendored copy).
from cli_web.reddit import __version__ as _pkg_version  # noqa: E402
from cli_web.reddit.utils.mcp_server import register_mcp_command  # noqa: E402

register_mcp_command(cli, app_name="reddit", version=_pkg_version)


if __name__ == "__main__":
    main()
