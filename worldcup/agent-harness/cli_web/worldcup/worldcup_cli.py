"""cli-web-worldcup — CLI entry point."""

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

_skin = ReplSkin(app="worldcup", version="0.1.0", display_name="World Cup 2026")


# ── Main CLI group ─────────────────────────────────────────────────────────────


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.version_option("0.1.0", prog_name="cli-web-worldcup")
@click.pass_context
def cli(ctx, json_mode):
    """cli-web-worldcup — FIFA World Cup 2026 from the command line.

    Fixtures, nations, squads, group standings, and bookmaker odds — all
    read-only. Data from ESPN (no auth) and The Odds API (free key for odds).
    Run without arguments to enter interactive REPL mode.
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode

    if ctx.invoked_subcommand is None:
        _run_repl(ctx)


# ── Register command groups ─────────────────────────────────────────────────────
from .commands.fixtures import fixtures  # noqa: E402
from .commands.odds import odds  # noqa: E402
from .commands.players import players  # noqa: E402
from .commands.standings import standings  # noqa: E402
from .commands.teams import teams  # noqa: E402

cli.add_command(fixtures)
cli.add_command(teams)
cli.add_command(players)
cli.add_command(standings)
cli.add_command(odds)


# ── REPL ───────────────────────────────────────────────────────────────────────


def _print_repl_help() -> None:
    _skin.info("Available commands:")
    print()
    print("  fixtures list [--team MEX] [--dates ...]   World Cup matches")
    print("  fixtures get <event_id>                    One match's detail")
    print("  teams list                                 All 48 nations")
    print("  teams get <id|code|name>                   One nation")
    print("  players roster <id|code|name>              A nation's squad")
    print("  standings list [--group A]                 Group tables")
    print("  odds list [--regions us] [--api-key KEY]   Bookmaker odds")
    print("  doctor                                     Diagnose local setup")
    print("  help                                       Show this help")
    print("  exit / quit / Ctrl-D                       Exit REPL")
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
        except Exception as exc:
            _skin.error(str(exc))


# Fleet-standard utility commands (vendored adapters in utils/):
# `mcp-serve` exposes every command as MCP tools over stdio; `doctor`
# diagnoses install/auth setup. Both derive from the Click tree — no
# per-command wiring needed.
from cli_web.worldcup import __version__ as _pkg_version  # noqa: E402
from cli_web.worldcup.utils.doctor import register_doctor_command  # noqa: E402
from cli_web.worldcup.utils.mcp_server import register_mcp_command  # noqa: E402

register_mcp_command(cli, app_name="worldcup", version=_pkg_version, pkg="worldcup")
register_doctor_command(cli, app_name="worldcup", pkg="worldcup")


def main():
    cli()


if __name__ == "__main__":
    main()
