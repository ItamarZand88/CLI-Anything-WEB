"""Standalone registry validation entry point (used by pre-commit).

Runs without installing the package: ``python devkit/cli_web_devkit/registry_check.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    # Allow direct invocation as a script (pre-commit hook).
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cli_web_devkit.paths import repo_root
from cli_web_devkit.registry import validate


def main() -> int:
    root = repo_root(Path.cwd())
    problems = validate(root)
    if problems:
        print("registry.json validation FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("registry.json OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
