"""Main CLI entry point for cli-web-notebooklm."""

import sys

import click

from cli_web.notebooklm import __version__
from cli_web.notebooklm.commands.auth_cmd import auth
from cli_web.notebooklm.commands.notebooks import notebooks
from cli_web.notebooklm.commands.sources import sources
from cli_web.notebooklm.commands.chat import chat
from cli_web.notebooklm.commands.artifacts import artifacts


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON")
@click.version_option(__version__, prog_name="cli-web-notebooklm")
@click.pass_context
def cli(ctx, json_mode):
    """Agent-native CLI for Google NotebookLM.

    Manage notebooks, sources, chat, and studio artifacts from the command line.
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode

    if ctx.invoked_subcommand is None:
        _run_repl(ctx)


def _run_repl(ctx):
    """Run the interactive REPL."""
    from cli_web.notebooklm.utils.repl_skin import ReplSkin

    skin = ReplSkin("notebooklm", version=__version__)
    skin.print_banner()

    pt_session = skin.create_prompt_session()

    commands = {
        "notebooks list": "List all notebooks",
        "notebooks get --id <id>": "Get notebook details",
        "sources list --notebook-id <id>": "List sources",
        "chat history --notebook-id <id>": "View chat history",
        "chat suggested --notebook-id <id>": "Get suggested questions",
        "artifacts list --notebook-id <id>": "List studio artifacts",
        "auth status": "Check auth status",
        "auth login": "Log in",
        "help": "Show this help",
        "quit": "Exit",
    }

    while True:
        try:
            line = skin.get_input(pt_session)
        except (EOFError, KeyboardInterrupt):
            skin.print_goodbye()
            break

        if not line:
            continue

        if line in ("quit", "exit", "q"):
            skin.print_goodbye()
            break

        if line == "help":
            skin.help(commands)
            continue

        # Parse and dispatch to Click commands
        args = line.split()
        if ctx.obj.get("json"):
            args.append("--json")

        try:
            cli.main(args=args, standalone_mode=False, **ctx.params)
        except SystemExit:
            pass
        except click.exceptions.UsageError as e:
            skin.error(str(e))
        except Exception as e:
            skin.error(str(e))


# Register command groups
cli.add_command(auth)
cli.add_command(notebooks)
cli.add_command(sources)
cli.add_command(chat)
cli.add_command(artifacts)


if __name__ == "__main__":
    cli()
