"""cli-web-linkedin — CLI entry point."""
from __future__ import annotations

import sys

# ── Windows UTF-8 fix ──────────────────────────────────────────────────────────
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass

import shlex

import click

from .utils.repl_skin import ReplSkin

_skin = ReplSkin("linkedin", version="0.1.0")


# ── Main CLI group ─────────────────────────────────────────────────────────────


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.version_option("0.1.0", prog_name="cli-web-linkedin")
@click.pass_context
def cli(ctx, json_mode):
    """cli-web-linkedin — Search, post, comment, react on LinkedIn.

    Running without a subcommand enters interactive REPL mode.

    Examples:
      cli-web-linkedin search people "python developer"
      cli-web-linkedin profile get williamhgates
      cli-web-linkedin feed --json
      cli-web-linkedin post create "Hello LinkedIn!"
      cli-web-linkedin jobs search "software engineer" --limit 5
      cli-web-linkedin company anthropic --json
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode

    if ctx.invoked_subcommand is None:
        _run_repl(ctx)


# ── Register commands here ─────────────────────────────────────────────────────
from .commands.feed import feed
from .commands.post import post
from .commands.search import search
from .commands.profile import profile
from .commands.company import company
from .commands.jobs import jobs
from .commands.notifications import notifications
from .commands.network import network
from .commands.messaging import messaging

cli.add_command(feed)
cli.add_command(post)
cli.add_command(search)
cli.add_command(profile)
cli.add_command(company)
cli.add_command(jobs)
cli.add_command(notifications)
cli.add_command(network)
cli.add_command(messaging)

# Auth commands
from .core.auth import login_browser, clear_auth, is_logged_in, load_auth
from .core.exceptions import LinkedinError
from .utils.helpers import handle_errors, print_json, resolve_json_mode

@cli.group("auth")
def auth_group():
    """Login, logout, and check authentication status."""

@auth_group.command("login")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
def auth_login(json_mode):
    """Login to LinkedIn via browser."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        login_browser()
        if json_mode:
            print_json({"success": True, "message": "Logged in successfully"})
        else:
            click.echo("  Logged in successfully. Cookies saved.")

@auth_group.command("status")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
def auth_status(json_mode):
    """Check current authentication status."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        if is_logged_in():
            auth_data = load_auth()
            cookies = auth_data.get("cookies", {}) if auth_data else {}
            if json_mode:
                print_json({"authenticated": True, "has_li_at": "li_at" in cookies})
            else:
                click.echo("  Logged in (li_at cookie present)")
        else:
            if json_mode:
                print_json({"authenticated": False, "message": "Not logged in"})
            else:
                click.echo("  Not logged in. Run: cli-web-linkedin auth login")

@auth_group.command("logout")
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
def auth_logout(json_mode):
    """Remove saved authentication."""
    json_mode = resolve_json_mode(json_mode)
    with handle_errors(json_mode=json_mode):
        clear_auth()
        if json_mode:
            print_json({"success": True, "message": "Logged out"})
        else:
            click.echo("  Logged out. Auth data removed.")


# ── REPL ───────────────────────────────────────────────────────────────────────


def _print_repl_help() -> None:
    _skin.info("Available commands:")
    print()
    print("  search all QUERY              General search (unfiltered)")
    print("  search people QUERY           Search people")
    print("  search jobs QUERY             Search jobs")
    print("  search companies QUERY        Search companies")
    print("    --limit N                     Max results (default: 10)")
    print()
    print("  feed                          View your feed")
    print("    --count N                     Number of posts (default: 10)")
    print()
    print("  profile get USERNAME          View a LinkedIn profile")
    print("  profile me                    View your own profile")
    print()
    print("  company NAME                  View a company page")
    print("  company follow COMPANY_URN    Follow a company")
    print("  company unfollow COMPANY_URN  Unfollow a company")
    print()
    print("  jobs search QUERY             Search for jobs")
    print("    --limit N                     Max results")
    print("  jobs get JOB_ID               View full job details")
    print()
    print("  post create TEXT              Publish a text post")
    print("  post edit POST_URN TEXT       Edit a post")
    print("  post delete POST_URN          Delete a post")
    print("  post react POST_URN           React to a post")
    print("    --type LIKE|PRAISE|EMPATHY|INTEREST|APPRECIATION|ENTERTAINMENT")
    print("  post unreact POST_URN         Remove reaction")
    print("  post comment POST_URN TEXT    Comment on a post")
    print("  post edit-comment URN TEXT    Edit a comment")
    print("  post delete-comment URN       Delete a comment")
    print()
    print("  notifications                 View notifications")
    print("    --limit N                     Max items")
    print()
    print("  network connections           List your connections")
    print("  network invitations           View pending invitations")
    print("  network accept INV_URN        Accept an invitation")
    print("  network decline INV_URN       Decline an invitation")
    print("  network connect PROFILE_URN   Send connection request")
    print("    -m MESSAGE                    Optional message")
    print()
    print("  messaging list                List conversations")
    print("  messaging read CONV_URN       Read messages in a conversation")
    print("  messaging send CONV_URN TEXT  Send a message")
    print()
    print("  auth login                    Login via browser")
    print("  auth status                   Check auth status")
    print("  auth logout                   Remove saved auth")
    print()
    print("  Global flags:")
    print("    --json                        Output as JSON")
    print()
    print("  help                          Show this help")
    print("  exit / quit / Ctrl-D          Exit REPL")
    print()


def _run_repl(ctx: click.Context) -> None:
    import random
    import time

    _skin.print_banner()
    _print_repl_help()

    pt_session = _skin.create_prompt_session()
    last_cmd_time: float = 0  # track inter-command timing

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

        # Inter-command delay — avoids machine-speed request bursts in REPL
        now = time.time()
        if last_cmd_time > 0:
            elapsed = now - last_cmd_time
            min_gap = max(0.5, random.gauss(1.0, 0.3))
            if elapsed < min_gap:
                time.sleep(min_gap - elapsed)

        try:
            cli.main(args=args, standalone_mode=False)
        except SystemExit:
            pass
        except Exception as exc:
            if ctx.obj.get("json") and isinstance(exc, LinkedinError):
                import json as _json
                click.echo(_json.dumps(exc.to_dict()))
            else:
                _skin.error(str(exc))
        finally:
            last_cmd_time = time.time()


def main():
    cli()


if __name__ == "__main__":
    main()
