"""cli-web-capitoltrades — CLI entry point."""
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

from .commands.articles import articles
from .commands.buzz import buzz
from .commands.issuers import issuers
from .commands.politicians import politicians
from .commands.press import press
from .commands.trades import trades
from .utils.repl_skin import ReplSkin

_skin = ReplSkin(app="capitoltrades", version="0.1.0")


# ── Main CLI group ─────────────────────────────────────────────────────────────


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
@click.version_option("0.1.0", prog_name="cli-web-capitoltrades")
@click.pass_context
def cli(ctx, json_mode):
    """cli-web-capitoltrades — CLI for capitoltrades.com (US congressional stock trades).

    Run without arguments to enter interactive REPL mode.
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode

    if ctx.invoked_subcommand is None:
        _run_repl(ctx)


cli.add_command(trades)
cli.add_command(politicians)
cli.add_command(issuers)
cli.add_command(articles)
cli.add_command(buzz)
cli.add_command(press)


# ── REPL ───────────────────────────────────────────────────────────────────────


def _print_repl_help() -> None:
    _skin.info("Available commands:")
    print()
    print("  trades list [--page N] [--page-size N] [--politician ID] [--issuer ID]")
    print("              [--party republican|democrat|independent] [--chamber house|senate]")
    print("              [--tx-type buy|sell|exchange] [--sector NAME]")
    print("              [--size <1K|1K-15K|15K-50K|...|25M-50M]")
    print("              [--sort traded|pubDate|filedAfter|tradeSize] [--sort-direction asc|desc]")
    print("  trades get <trade_id>             Show a single trade")
    print("  trades by-ticker <SYM>            Find trades for a ticker (e.g. NVDA, AMGN)")
    print("  trades stats                      Overview stats (total trades, volume, etc.)")
    print()
    print("  politicians list [--page N] [--party republican|democrat|independent] [--chamber house|senate] [--state ST]")
    print("  politicians top [--by trades|volume] [--page-size N] [--party ...] [--chamber ...]")
    print("  politicians get <bioguide_id>     Show a single politician (e.g. Y000067)")
    print()
    print("  issuers list [--page N] [--sector NAME]")
    print("  issuers get <issuer_id>           Show a single issuer (e.g. 435544)")
    print("  issuers search <query> [--full]   Search via BFF (rich JSON: prices, stats)")
    print()
    print("  articles list [--page N]")
    print("  articles get <slug>               Show a single article")
    print()
    print("  buzz list [--page N]              List buzz items (curated news snippets)")
    print("  buzz get <slug>                   Show a single buzz item")
    print()
    print("  press list [--page N]             List press coverage items")
    print("  press get <slug>                  Show a single press item")
    print()
    print("  help                              Show this help")
    print("  exit / quit / Ctrl-D              Exit REPL")
    print()


def _run_repl(ctx: click.Context) -> None:
    _skin.print_banner()
    _print_repl_help()

    # prompt_toolkit needs a TTY; fall back to plain input() for piped stdin.
    if sys.stdin.isatty():
        pt_session = _skin.create_prompt_session()
    else:
        pt_session = None

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
        except click.exceptions.UsageError as exc:
            _skin.error(str(exc))
        except Exception as exc:
            _skin.error(str(exc))


def main():
    cli()


if __name__ == "__main__":
    main()
