"""cli-web-chatgpt — CLI for ChatGPT web interface."""

import sys

if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
if sys.stderr and sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

import shlex

import click

from .commands.account import me, models
from .commands.auth_cmd import auth_group
from .commands.chat import chat_group
from .commands.conversations import conversations_group
from .commands.images import images_group
from .utils.repl_skin import ReplSkin

_skin = ReplSkin("chatgpt", version="0.1.0")


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.pass_context
def cli(ctx, json_mode: bool) -> None:
    """CLI for ChatGPT — ask questions, generate images, manage conversations."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode

    if ctx.invoked_subcommand is None:
        _run_repl(ctx)


# Register command groups and standalone commands
cli.add_command(chat_group)
cli.add_command(conversations_group)
cli.add_command(images_group)
cli.add_command(auth_group)
cli.add_command(me)
cli.add_command(models)


def _print_repl_help() -> None:
    _skin.info("Available commands:")
    print("  chat ask <question>           Ask ChatGPT a question")
    print("    --model <slug>              Model (e.g. gpt-5-4-thinking)")
    print("    --conversation <id>         Continue existing conversation")
    print("  chat image <prompt>           Generate an image")
    print("    --style <name>              Apply a style")
    print("    --output <path>             Save image to file")
    print("    --conversation <id>         Continue existing conversation")
    print("  conversations list            List recent conversations")
    print("    --limit <n>                 Number to show (default: 20)")
    print("    --archived / --starred      Filter")
    print("  conversations get <id>        View a conversation")
    print("  images list                   List recently generated images")
    print("  images download <file_id>     Download a generated image")
    print("    --conversation <id>         (required) Conversation containing the image")
    print("    --output <path>             Output file path")
    print("  images styles                 List available image styles")
    print("  models                        List available models")
    print("  me                            Show current user info")
    print("  auth login                    Login via browser")
    print("  auth status                   Check auth status")
    print("  auth logout                   Remove stored credentials")
    print()
    print("  help                          Show this help")
    print("  exit / quit                   Exit REPL")


def _run_repl(ctx) -> None:
    _skin.print_banner()

    while True:
        try:
            line = input(_skin.prompt()).strip()
        except (EOFError, KeyboardInterrupt):
            _skin.print_goodbye()
            break

        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            _skin.print_goodbye()
            break
        if line.lower() in ("help", "?"):
            _print_repl_help()
            continue

        try:
            args = shlex.split(line)
        except ValueError as exc:
            _skin.error(f"Parse error: {exc}")
            continue

        repl_args = ["--json"] + args if ctx.obj.get("json") else args

        try:
            cli.main(args=repl_args, standalone_mode=False)
        except SystemExit:
            pass
        except click.exceptions.UsageError as exc:
            _skin.error(str(exc))
        except Exception as exc:
            _skin.error(f"{type(exc).__name__}: {exc}")


def main():
    cli()


if __name__ == "__main__":
    main()
