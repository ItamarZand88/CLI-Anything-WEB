"""Main CLI entry point for cli-web-notebooklm."""
import shlex
import sys

# Force UTF-8 output on Windows to handle emoji/Hebrew/Unicode content
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

import click

from .commands.notebooks import notebooks
from .commands.sources import sources
from .commands.chat import chat
from .commands.artifacts import artifacts
from .core.auth import (
    login_browser, login_from_cookies_json, get_auth_status,
)
from .core.client import NotebookLMClient
from .core.exceptions import AuthError, NotebookLMError
from .utils.output import print_json, print_user, error, handle_error
from .utils.repl_skin import ReplSkin

APP_NAME = "notebooklm"
VERSION = "0.1.0"

_skin = ReplSkin(APP_NAME, version=VERSION)


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """cli-web-notebooklm — NotebookLM CLI.

    Run without a subcommand to enter interactive REPL mode.
    """
    if ctx.invoked_subcommand is None:
        _run_repl()


def _run_repl():
    """Interactive REPL mode."""
    _skin.print_banner()
    _skin.info("Type 'help' for available commands, 'quit' to exit.")

    while True:
        try:
            line = input(_skin.prompt()).strip()
        except (EOFError, KeyboardInterrupt):
            _skin.print_goodbye()
            sys.exit(0)

        if not line:
            continue
        if line in ("quit", "exit", "q"):
            _skin.print_goodbye()
            sys.exit(0)
        if line in ("help", "?"):
            _print_repl_help()
            continue

        args = shlex.split(line)
        try:
            main.main(args, standalone_mode=False, prog_name="cli-web-notebooklm")
        except SystemExit:
            pass
        except click.UsageError as e:
            _skin.error(str(e))
        except Exception as e:
            _skin.error(str(e))


def _print_repl_help():
    _skin.info("Available commands:")
    print()
    print("  Context:")
    print("    use <notebook-id>                              Set current notebook (persists)")
    print("    status                                         Show current context + auth")
    print()
    print("  Notebooks:")
    print("    notebooks list                                 List all notebooks")
    print("    notebooks create --title <title>               Create a notebook")
    print("    notebooks get <id>                             Get details (partial ID OK)")
    print("    notebooks rename <id> --title <t>              Rename (partial ID OK)")
    print("    notebooks delete <id> --confirm                Delete (partial ID OK)")
    print()
    print("  Sources (--notebook optional if context set):")
    print("    sources list [--notebook <id>]                 List sources")
    print("    sources add-url [--notebook <id>] --url <url>  Add URL source")
    print("    sources add-text [--notebook <id>] --title <t> Add text source")
    print("    sources get <source-id> [--notebook <id>]      Get source (partial ID OK)")
    print("    sources delete <source-id> --confirm           Delete source")
    print()
    print("  Chat:")
    print("    chat ask [--notebook <id>] --query <q>         Ask question")
    print()
    print("  Artifacts:")
    print("    artifacts generate --type <t> [--wait] [--output f] Generate artifact")
    print("      types: audio, video, mindmap, study-guide, briefing, faq,")
    print("             quiz, infographic, slide-deck, data-table")
    print("    artifacts list                                   List all with status")
    print("    artifacts download <id> -o <file>                Download completed")
    print("    artifacts generate-notes                         Generate study notes")
    print("    artifacts list-audio-types                       List audio types")
    print()
    print("  Account:")
    print("    whoami                                         Show current user")
    print("    auth login                                     Login via browser")
    print("    auth status                                    Check auth status")
    print("  quit                                             Exit REPL")


# ── Register command groups ───────────────────────────────────────────────────

main.add_command(notebooks)
main.add_command(sources)
main.add_command(chat)
main.add_command(artifacts)


# ── Auth commands ─────────────────────────────────────────────────────────────

@main.group()
def auth():
    """Manage authentication."""
    pass


@auth.command("login")
@click.option("--cookies-json", default=None, help="Import cookies from a JSON file")
def auth_login(cookies_json):
    """Log in to NotebookLM via browser (Google account required)."""
    try:
        if cookies_json:
            login_from_cookies_json(cookies_json)
        else:
            login_browser()
    except AuthError as e:
        error(str(e))


@auth.command("status")
@click.option("--json", "as_json", is_flag=True, default=False)
def auth_status(as_json):
    """Show current authentication status."""
    status = get_auth_status()
    if as_json:
        print_json(status)
    else:
        valid = status.get("valid", False)
        configured = status.get("configured", False)
        msg = status.get("message", "")
        if not configured:
            click.echo("Not configured. Run: cli-web-notebooklm auth login")
        elif valid:
            click.echo(f"[OK] Authenticated -- {msg}")
            click.echo(f"  Cookies: {status.get('cookie_count', 0)}")
            click.echo(f"  Session: {status.get('session_id', 'N/A')}")
        else:
            click.echo(f"[FAIL] Auth invalid -- {msg}")


@auth.command("refresh")
def auth_refresh():
    """Re-extract CSRF and session tokens from NotebookLM homepage.

    This refreshes tokens when they've rotated but cookies are still valid.
    If cookies themselves have expired, run 'auth login' instead.
    """
    try:
        from .core.auth import load_cookies, fetch_tokens, _save_auth
        cookies = load_cookies()
        csrf, session_id, build_label = fetch_tokens(cookies)
        # Save the refreshed session info
        from .core.auth import AUTH_DIR
        import json
        session_file = AUTH_DIR / "session.json"
        session_file.write_text(json.dumps({
            "at": csrf, "f_sid": session_id, "bl": build_label,
        }), encoding="utf-8")
        click.echo(f"[OK] Tokens refreshed -- session {session_id[:8]}...")
    except AuthError as e:
        error(f"{e}\n\nTokens AND cookies expired. Run: cli-web-notebooklm auth login")


# ── Context commands ─────────────────────────────────────────────────────────

@main.command("use")
@click.argument("notebook_id")
def use_notebook(notebook_id):
    """Set the current notebook context (persists across sessions)."""
    from .utils.helpers import handle_errors, set_context_value
    with handle_errors():
        client = NotebookLMClient()
        nb = client.get_notebook(notebook_id)
        set_context_value("notebook_id", nb.id)
        set_context_value("notebook_title", nb.title)
        # Also update in-memory session
        from .core.session import get_session
        get_session().set_notebook(nb.id, nb.title)
        _skin.success(f"Now using: {nb.display_title()} ({nb.id})")


@main.command("status")
@click.option("--json", "as_json", is_flag=True, default=False)
def show_status(as_json):
    """Show current context (selected notebook, auth status)."""
    from .utils.helpers import handle_errors, get_context_value
    with handle_errors(json_mode=as_json):
        context = {
            "notebook_id": get_context_value("notebook_id"),
            "notebook_title": get_context_value("notebook_title"),
        }
        auth = get_auth_status()
        if as_json:
            print_json({**context, "auth": auth})
        else:
            nb_id = context["notebook_id"]
            nb_title = context["notebook_title"]
            if nb_id:
                click.echo(f"Notebook: {nb_title} ({nb_id})")
            else:
                click.echo("Notebook: (none selected — use: cli-web-notebooklm use <id>)")
            valid = auth.get("valid", False)
            click.echo(f"Auth:     {'OK' if valid else 'Not configured'} — {auth.get('message', '')}")


# ── Whoami ────────────────────────────────────────────────────────────────────

@main.command("whoami")
@click.option("--json", "as_json", is_flag=True, default=False)
def whoami(as_json):
    """Show current user information."""
    try:
        client = NotebookLMClient()
        user = client.get_user()
        if as_json:
            print_json({"email": user.email, "display_name": user.display_name, "avatar_url": user.avatar_url})
        else:
            print_user(user)
    except NotebookLMError as e:
        handle_error(e, as_json)
    except Exception as e:
        handle_error(e, as_json)


if __name__ == "__main__":
    main()
