#!/usr/bin/env python3
"""Single-source-of-truth sync for shared, app-agnostic CLI files.

Some files in every generated CLI are byte-for-byte identical and contain no
per-app logic — the REPL skin is the prime example (parameterised entirely via
``ReplSkin(app=...)``). To keep each CLI directory fully standalone we still
ship a physical copy in every CLI, but those copies are generated from ONE
canonical source so they can never drift.

Usage::

    python scripts/sync-shared.py            # copy canonical -> every CLI
    python scripts/sync-shared.py --check     # CI: fail if any copy is stale

Exit code 0 when in sync, 1 when a copy is missing or differs (--check).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Canonical source -> per-CLI relative destination (within cli_web/<pkg>/).
SHARED_FILES = {
    REPO_ROOT / "cli-anything-web-plugin" / "scripts" / "repl_skin.py":
        Path("utils") / "repl_skin.py",
    REPO_ROOT / "cli-anything-web-plugin" / "shared" / "exceptions.py":
        Path("core") / "exceptions.py",
}

NON_CLI_DIRS = {
    "assets", "docs", "scripts", "cli-anything-web-plugin",
    ".git", ".github", ".claude", ".claude-plugin", ".playwright",
}


def cli_packages() -> list[Path]:
    """Return each CLI's package dir: <app>/agent-harness/cli_web/<pkg>/."""
    pkgs: list[Path] = []
    for child in sorted(REPO_ROOT.iterdir()):
        if not child.is_dir() or child.name in NON_CLI_DIRS or child.name.startswith("."):
            continue
        cli_web = child / "agent-harness" / "cli_web"
        if not cli_web.is_dir():
            continue
        pkg = cli_web / child.name.replace("-", "_")
        if pkg.is_dir():
            pkgs.append(pkg)
    return pkgs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report stale copies and exit 1 instead of writing")
    args = ap.parse_args()

    pkgs = cli_packages()
    stale: list[str] = []
    written = 0

    for canonical, rel_dest in SHARED_FILES.items():
        if not canonical.exists():
            print(f"ERROR canonical source missing: {canonical}")
            return 1
        source = canonical.read_bytes()
        for pkg in pkgs:
            dest = pkg / rel_dest
            current = dest.read_bytes() if dest.exists() else None
            if current == source:
                continue
            rel = dest.relative_to(REPO_ROOT)
            if args.check:
                stale.append(f"{'missing' if current is None else 'stale  '} {rel}")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(source)
                written += 1
                print(f"synced {rel}")

    if args.check:
        if stale:
            for s in stale:
                print(f"ERROR {s}")
            print(f"\n✗ {len(stale)} shared file(s) out of sync — run: python scripts/sync-shared.py")
            return 1
        print(f"✓ all shared files in sync across {len(pkgs)} CLIs")
        return 0

    print(f"\n✓ synced {written} file(s) across {len(pkgs)} CLIs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
