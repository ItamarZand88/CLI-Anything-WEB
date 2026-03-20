"""cli-web-unsplash — CLI for Unsplash photo search and discovery."""

from __future__ import annotations

import shlex
import sys

# Windows UTF-8 fix
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

import click

from .commands.collections import collections
from .commands.photos import photos
from .commands.topics import topics
from .commands.users import users
from .utils.repl_skin import ReplSkin

_skin = ReplSkin("unsplash", version="0.1.0")


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.option("--version", is_flag=True, help="Show version.")
@click.pass_context
def cli(ctx, json_mode, version):
    """Unsplash photo search and discovery CLI."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode
    if version:
        click.echo("cli-web-unsplash 0.1.0")
        return
    if ctx.invoked_subcommand is None:
        _repl(ctx)


cli.add_command(photos)
cli.add_command(topics)
cli.add_command(collections)
cli.add_command(users)


def _print_repl_help():
    """Print REPL help listing all commands and key options."""
    _skin.info("Available commands:")
    print()
    print("  photos search <query>     [--orientation landscape|portrait|squarish]")
    print("                            [--color <color>] [--order-by relevant|latest]")
    print("                            [--page N] [--per-page N]")
    print("  photos get <photo_id>     Get photo details by ID")
    print("  photos random             [--query <q>] [--orientation <o>] [--count N]")
    print("  photos download <photo_id> [--size raw|full|regular|small|thumb] [-o path]")
    print("  photos stats <photo_id>   Photo view/download statistics")
    print()
    print("  topics list               [--order-by featured|latest|oldest|position]")
    print("  topics get <slug>         Topic details")
    print("  topics photos <slug>      [--page N] [--per-page N] [--order-by latest|oldest|popular]")
    print()
    print("  collections search <q>    [--page N] [--per-page N]")
    print("  collections get <id>      Collection details")
    print("  collections photos <id>   [--page N] [--per-page N]")
    print()
    print("  users search <query>      [--page N] [--per-page N]")
    print("  users get <username>      User profile")
    print("  users photos <username>   [--page N] [--per-page N] [--order-by latest|popular|views]")
    print("  users collections <user>  [--page N] [--per-page N]")
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


if __name__ == "__main__":
    main()
