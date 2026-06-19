"""cli-web-youtube — CLI entry point for YouTube."""

from __future__ import annotations

import sys

# Windows UTF-8 fix
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass

import shlex

import click
from cli_web.youtube import __version__
from cli_web.youtube.commands.channel import channel_group
from cli_web.youtube.commands.search import search_group
from cli_web.youtube.commands.transcript import transcript_group
from cli_web.youtube.commands.trending import trending_group
from cli_web.youtube.commands.video import video_group
from cli_web.youtube.core.exceptions import YouTubeError
from cli_web.youtube.utils.repl_skin import ReplSkin

_skin = ReplSkin(app="youtube", version=__version__)


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.version_option(__version__, prog_name="cli-web-youtube")
@click.pass_context
def cli(ctx, json_mode):
    """cli-web-youtube — Search, browse, and explore YouTube from the command line.

    Run without arguments to enter interactive REPL mode.
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode

    if ctx.invoked_subcommand is None:
        _run_repl(ctx)


cli.add_command(search_group)
cli.add_command(video_group)
cli.add_command(trending_group)
cli.add_command(channel_group)
cli.add_command(transcript_group)


# ── REPL ──────────────────────────────────────────────────────


def _print_repl_help() -> None:
    _skin.info("Available commands:")
    print()
    print("  search videos <query> [OPTIONS]")
    print("    -l, --limit N              Max results (default 10)")
    print("    --json                     Output as JSON")
    print()
    print("  video get <id_or_url>        Video details")
    print("    --json                     Output as JSON")
    print()
    print("  trending list [OPTIONS]")
    print("    -c, --category now|music|gaming|movies")
    print("    -l, --limit N              Max results (default 20)")
    print("    --json                     Output as JSON")
    print()
    print("  channel get <handle>         Channel info + recent videos")
    print("    --json                     Output as JSON")
    print()
    print("  transcript get <id_or_url>   Video transcript (timestamped)")
    print("    -l, --lang CODE            Preferred language(s), in priority order")
    print("    -t, --translate CODE       Translate into a language")
    print("    --text-only                Plain text only (no timestamps)")
    print("    --json                     Output as JSON")
    print()
    print("  transcript list <id_or_url>  Available transcript languages")
    print("    --json                     Output as JSON")
    print()
    print("  help                         Show this help")
    print("  exit / quit / Ctrl-D         Exit REPL")
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

        if ctx.obj.get("json"):
            args = ["--json"] + args

        try:
            cli.main(args=args, standalone_mode=False)
        except SystemExit:
            pass
        except YouTubeError as exc:
            _skin.error(exc.message)
        except Exception as exc:
            _skin.error(str(exc))


def main():
    cli()


# MCP server mode — exposes every command as an MCP tool over stdio.
# Canonical adapter: cli-web-core/cli_web_core/mcp_server.py (vendored copy).
from cli_web.youtube import __version__ as _pkg_version  # noqa: E402
from cli_web.youtube.utils.doctor import register_doctor_command  # noqa: E402
from cli_web.youtube.utils.mcp_server import register_mcp_command  # noqa: E402

register_mcp_command(cli, app_name="youtube", version=_pkg_version)
register_doctor_command(cli, app_name="youtube", pkg="youtube")


if __name__ == "__main__":
    main()
