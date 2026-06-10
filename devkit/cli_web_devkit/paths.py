"""Repo-root discovery for fleet tooling."""

from __future__ import annotations

from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    """Walk upward from *start* (default: this file) to the repo root.

    The root is identified by the presence of ``registry.json``.
    """
    cur = (start or Path(__file__)).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / "registry.json").is_file():
            return candidate
    raise FileNotFoundError(
        "Could not locate repo root (no registry.json found above "
        f"{(start or Path(__file__)).resolve()})"
    )
