"""Keep the GitHub repo "About" description's CLI count in sync with the fleet.

The repo description embeds a count — ``... N CLIs and counting.`` — that must
match the number of CLIs in registry.json. GitHub repo metadata is not a file,
so this is enforced through the GitHub API (the ``gh`` CLI), not the README
marker mechanism used by ``docs``:

- ``about --check`` compares the count in the live description to the registry
  and fails on drift. Read-only — runs with the default Actions token.
- ``about --apply`` rewrites just the count in the live description, preserving
  the surrounding prose. Editing repo metadata needs a token with
  ``Administration: write`` — the default ``GITHUB_TOKEN`` cannot, so this is a
  local step (your ``gh`` login) or a PAT-backed CI job.

Only the count is templated; the prose is whatever the maintainer set, so a
reworded tagline survives ``--apply``.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .registry import Registry

# Match the count token in the description, e.g. "19 CLIs".
_COUNT_RE = re.compile(r"\b\d+\s+CLIs\b")


def fleet_count(root: Path) -> int:
    """Number of CLIs in the fleet — the single source of truth."""
    return len(Registry.load(root / "registry.json").clis)


def desired_description(description: str, count: int) -> str:
    """Return ``description`` with its ``<n> CLIs`` count set to ``count``.

    If the description has no count token, append the standard suffix.
    """
    if _COUNT_RE.search(description):
        return _COUNT_RE.sub(f"{count} CLIs", description, count=1)
    return f"{description.rstrip().rstrip('.')}. {count} CLIs and counting."


def _gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=False)


def live_description() -> str:
    """Fetch the repo's current GitHub description via ``gh``."""
    proc = _gh("repo", "view", "--json", "description", "-q", ".description")
    if proc.returncode != 0:
        raise RuntimeError(
            f"gh repo view failed ({proc.returncode}): {proc.stderr.strip() or 'is gh installed and authenticated?'}"
        )
    return proc.stdout.strip()


def apply_description(description: str) -> None:
    """Set the repo's GitHub description (needs Administration: write)."""
    proc = _gh("repo", "edit", "--description", description)
    if proc.returncode != 0:
        raise RuntimeError(f"gh repo edit failed ({proc.returncode}): {proc.stderr.strip()}")
