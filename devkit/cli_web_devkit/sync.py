"""Fleet sync: keep vendored shared files identical to their canonical source.

Distribution model ("vendoring with provenance"): generated CLIs must stay
installable with a bare ``pip install -e <dir>`` and no private index, so
framework-owned files are *copied* into each CLI rather than imported from
cli-web-core. This module makes that safe:

- ``cli-web-core`` holds the canonical bytes
- ``drift()`` reports any CLI whose vendored copy diverged
- ``resync()`` rewrites vendored copies from canon and records provenance
  in each CLI's ``.manifest.json``

A CLI may intentionally diverge by listing the file under ``overrides`` in
its manifest (with a reason); drift then reports it as ``override`` instead
of failing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .registry import Registry, RegistryEntry

MANIFEST_NAME = ".manifest.json"
MANIFEST_VERSION = 1

# Canonical source (relative to repo root) -> vendored path inside each CLI
# package dir (relative to <dir>/agent-harness/cli_web/<pkg>/).
SHARED_FILES: dict[str, str] = {
    "cli-web-core/cli_web_core/repl_skin.py": "utils/repl_skin.py",
    "cli-web-core/cli_web_core/mcp_server.py": "utils/mcp_server.py",
    "cli-web-core/cli_web_core/doctor.py": "utils/doctor.py",
}

# Non-CLI vendored copies that must also track canon (relative to repo root).
# The plugin keeps its own copies so scaffold-cli.py stays self-contained
# when the plugin is installed outside this monorepo.
EXTRA_VENDOR_TARGETS: dict[str, str] = {
    "cli-web-core/cli_web_core/repl_skin.py": "cli-anything-web-plugin/scripts/repl_skin.py",
    "cli-web-core/cli_web_core/mcp_server.py": "cli-anything-web-plugin/scripts/mcp_server.py",
    "cli-web-core/cli_web_core/doctor.py": "cli-anything-web-plugin/scripts/doctor.py",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pkg_dir(root: Path, entry: RegistryEntry) -> Path:
    return root / entry.directory / "cli_web" / entry.package


def manifest_path(root: Path, entry: RegistryEntry) -> Path:
    return root / entry.directory / MANIFEST_NAME


def load_manifest(root: Path, entry: RegistryEntry) -> dict[str, Any]:
    path = manifest_path(root, entry)
    if path.is_file():
        loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return loaded
    return {
        "manifest_version": MANIFEST_VERSION,
        "cli": entry.name,
        "generator": {"plugin_version": "unknown", "note": "backfilled by cli-web-devkit"},
        "profile": {"protocol": entry.protocol, "auth": entry.auth},
        "shared_files": {},
        "overrides": [],
    }


def save_manifest(root: Path, entry: RegistryEntry, manifest: dict[str, Any]) -> None:
    path = manifest_path(root, entry)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _override_reason(manifest: dict[str, Any], vendored_rel: str) -> str | None:
    for override in manifest.get("overrides", []):
        if override.get("file") == vendored_rel:
            return str(override.get("reason", "unspecified"))
    return None


@dataclass
class DriftItem:
    cli: str
    file: str
    status: str  # "ok" | "drifted" | "missing" | "override"
    detail: str = ""


def drift(root: Path) -> list[DriftItem]:
    """Compare every vendored shared file against its canonical source."""
    registry = Registry.load(root / "registry.json")
    items: list[DriftItem] = []

    for canon_rel, vendored_rel in SHARED_FILES.items():
        canon = root / canon_rel
        canon_hash = _sha256(canon)
        for entry in registry.clis:
            target = _pkg_dir(root, entry) / vendored_rel
            manifest = load_manifest(root, entry)
            if not target.is_file():
                items.append(DriftItem(entry.name, vendored_rel, "missing"))
                continue
            if _sha256(target) == canon_hash:
                items.append(DriftItem(entry.name, vendored_rel, "ok"))
                continue
            reason = _override_reason(manifest, vendored_rel)
            if reason:
                items.append(DriftItem(entry.name, vendored_rel, "override", reason))
            else:
                items.append(
                    DriftItem(entry.name, vendored_rel, "drifted", f"differs from {canon_rel}")
                )

    for canon_rel, target_rel in EXTRA_VENDOR_TARGETS.items():
        canon_hash = _sha256(root / canon_rel)
        target = root / target_rel
        if not target.is_file():
            items.append(DriftItem("(plugin)", target_rel, "missing"))
        elif _sha256(target) == canon_hash:
            items.append(DriftItem("(plugin)", target_rel, "ok"))
        else:
            items.append(DriftItem("(plugin)", target_rel, "drifted", f"differs from {canon_rel}"))

    return items


def resync(root: Path, apps: list[str] | None = None) -> list[str]:
    """Rewrite vendored shared files from canon. Returns changed paths.

    Files listed in a CLI's manifest ``overrides`` are left untouched.
    Every synced file's provenance (source, sha256) is recorded in the
    CLI's ``.manifest.json``.
    """
    registry = Registry.load(root / "registry.json")
    selected = registry.clis
    if apps:
        selected = [registry.entry(a) for a in apps]

    changed: list[str] = []
    for canon_rel, vendored_rel in SHARED_FILES.items():
        canon = root / canon_rel
        canon_bytes = canon.read_bytes()
        canon_hash = hashlib.sha256(canon_bytes).hexdigest()
        for entry in selected:
            manifest = load_manifest(root, entry)
            if _override_reason(manifest, vendored_rel):
                continue
            target = _pkg_dir(root, entry) / vendored_rel
            if not target.is_file() or _sha256(target) != canon_hash:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(canon_bytes)
                changed.append(str(target.relative_to(root)))
            manifest["shared_files"][vendored_rel] = {
                "source": canon_rel,
                "sha256": canon_hash,
                "synced_at": _utc_now(),
            }
            save_manifest(root, entry, manifest)

    if not apps:  # plugin-internal copies only sync on full-fleet runs
        for canon_rel, target_rel in EXTRA_VENDOR_TARGETS.items():
            canon_bytes = (root / canon_rel).read_bytes()
            target = root / target_rel
            if not target.is_file() or target.read_bytes() != canon_bytes:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(canon_bytes)
                changed.append(target_rel)

    return changed
