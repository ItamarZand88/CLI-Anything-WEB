"""Main CLI entry point for cli-web-suno.

Usage:
    cli-web-suno [--json] <command> <subcommand> [options]
    cli-web-suno                    # Enter REPL mode
"""

import click

from cli_web.suno.commands.auth import auth_group
from cli_web.suno.commands.songs import songs
from cli_web.suno.commands.explore import explore
from cli_web.suno.commands.projects import projects
from cli_web.suno.commands.billing import billing
from cli_web.suno.commands.prompts import prompts


@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, default=False, help="Output as JSON")
@click.pass_context
def cli(ctx, use_json):
    """cli-web-suno: Agent-native CLI for Suno AI Music Generator.

    Generate AI music, manage your library, and explore trending content.
    Run without a command to enter REPL mode.
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = use_json

    if ctx.invoked_subcommand is None:
        _enter_repl(ctx)


def _enter_repl(ctx):
    """Enter interactive REPL mode."""
    try:
        from cli_web.suno.utils.repl_skin import start_repl
        start_repl(cli)
    except ImportError:
        # Fallback simple REPL
        click.echo("cli-web-suno REPL (type 'help' for commands, 'exit' to quit)")
        click.echo()
        while True:
            try:
                line = input("suno> ").strip()
            except (EOFError, KeyboardInterrupt):
                click.echo()
                break
            if not line:
                continue
            if line in ("exit", "quit", "q"):
                break
            if line == "help":
                click.echo(ctx.get_help())
                continue
            # Parse and invoke the command
            args = line.split()
            try:
                cli.main(args, standalone_mode=False, **{"obj": ctx.obj})
            except SystemExit:
                pass
            except click.exceptions.UsageError as e:
                click.echo(f"Error: {e}")
            except Exception as e:
                click.echo(f"Error: {e}")


# Register command groups
cli.add_command(auth_group, "auth")
cli.add_command(songs, "songs")
cli.add_command(explore, "explore")
cli.add_command(projects, "projects")
cli.add_command(billing, "billing")
cli.add_command(prompts, "prompts")


if __name__ == "__main__":
    cli()
