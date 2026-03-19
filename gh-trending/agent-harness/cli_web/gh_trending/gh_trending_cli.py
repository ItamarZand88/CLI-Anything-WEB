"""cli-web-gh-trending — CLI entry point for GitHub Trending."""

from __future__ import annotations

import shlex

import click

from cli_web.gh_trending.commands.developers import developers_group
from cli_web.gh_trending.commands.repos import repos_group
from cli_web.gh_trending.core.exceptions import AppError
from cli_web.gh_trending.utils.repl_skin import ReplSkin

_skin = ReplSkin(app="gh_trending", version="1.0.0")


# ---------------------------------------------------------------------------- main CLI


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON (applies to all commands).")
@click.version_option("1.0.0", prog_name="cli-web-gh-trending")
@click.pass_context
def cli(ctx, json_mode):
    """cli-web-gh-trending — GitHub Trending repositories and developers.

    Run without arguments to enter interactive REPL mode.
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode

    if ctx.invoked_subcommand is None:
        _run_repl(ctx)


cli.add_command(repos_group)
cli.add_command(developers_group)


# ---------------------------------------------------------------------------- REPL


def _print_repl_help() -> None:
    _skin.info("Available commands:")
    print()
    print("  repos list [OPTIONS]")
    print("    -l, --language TEXT         Filter by programming language (python, js, etc.)")
    print("    -s, --since RANGE           Time range: daily (default), weekly, monthly")
    print("    -L, --spoken-language CODE  Filter by spoken language (ISO 639-1, e.g. zh)")
    print("    --json                      Output as JSON")
    print()
    print("  developers list [OPTIONS]")
    print("    -l, --language TEXT         Filter by programming language")
    print("    -s, --since RANGE           Time range: daily, weekly, monthly")
    print("    --json                      Output as JSON")
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
