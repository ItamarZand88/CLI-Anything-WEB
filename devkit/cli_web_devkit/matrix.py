"""Emit the GitHub Actions test matrix from registry.json.

Replaces the hand-maintained matrix in ``.github/workflows/tests.yml``:
adding a CLI to the registry automatically adds it to CI.

The output is a JSON *array* of ``{name, dir, pkg}`` objects so the
workflow can use it as one matrix axis and cross it with others
(e.g. Python versions)::

    strategy:
      matrix:
        python: ["3.10", "3.12"]
        cli: ${{ fromJSON(needs.matrix.outputs.clis) }}
"""

from __future__ import annotations

import json
from pathlib import Path

from .registry import Registry


def build_matrix(root: Path) -> list[dict[str, str]]:
    registry = Registry.load(root / "registry.json")
    return [{"name": e.app_dir, "dir": e.directory, "pkg": e.package} for e in registry.clis]


def render_matrix(root: Path) -> str:
    """Single-line JSON suitable for ``$GITHUB_OUTPUT``."""
    return json.dumps(build_matrix(root), separators=(",", ":"))
