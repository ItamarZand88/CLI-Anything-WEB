"""Unified REPL skin for cli-web-suno.

Provides a branded interactive prompt with command completion.
"""

import shlex
import sys

import click


BANNER = r"""
  ____                    ____ _     ___
 / ___| _   _ _ __   ___ / ___| |   |_ _|
 \___ \| | | | '_ \ / _ \ |   | |    | |
  ___) | |_| | | | | (_) | |___| |___ | |
 |____/ \__,_|_| |_|\___/ \____|_____|___|

  AI Music Generator CLI
  Type 'help' for commands, 'exit' to quit.
"""


def start_repl(cli_group):
    """Start the interactive REPL."""
    click.echo(click.style(BANNER, fg="magenta"))

    ctx_obj = {"json": False}

    while True:
        try:
            line = input(click.style("suno", fg="magenta") + "> ").strip()
        except (EOFError, KeyboardInterrupt):
            click.echo("\nBye!")
            break

        if not line:
            continue
        if line in ("exit", "quit", "q"):
            click.echo("Bye!")
            break
        if line == "help":
            try:
                cli_group.main(["--help"], standalone_mode=False, obj=ctx_obj)
            except SystemExit:
                pass
            continue

        # Handle --json toggle
        if line == "json on":
            ctx_obj["json"] = True
            click.echo("JSON output: ON")
            continue
        if line == "json off":
            ctx_obj["json"] = False
            click.echo("JSON output: OFF")
            continue

        try:
            args = shlex.split(line)
        except ValueError as e:
            click.echo(f"Parse error: {e}")
            continue

        # Inject --json flag if enabled
        if ctx_obj["json"] and "--json" not in args:
            args = ["--json"] + args

        try:
            cli_group.main(args, standalone_mode=False, obj=ctx_obj)
        except SystemExit:
            pass
        except click.exceptions.UsageError as e:
            click.echo(f"Error: {e}")
        except Exception as e:
            click.echo(f"Error: {e}")
