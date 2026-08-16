"""Load and validate ``registry.json`` — the fleet's source of truth.

The registry drives the CI test matrix, docs generation, and contract
tests, so its accuracy is enforced both ways:

* every registry entry must point at a real ``<dir>/agent-harness`` package
* every ``*/agent-harness`` directory in the repo must have a registry entry
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = (
    "name",
    "website",
    "protocol",
    "auth",
    "directory",
    "namespace",
    "commands",
    "install",
)


@dataclass
class RegistryEntry:
    name: str
    website: str
    protocol: str
    auth: str
    directory: str
    namespace: str
    commands: list[str]
    install: str
    # Optional: read-only command invocations (arg lists) safe to run on a
    # schedule against the live site to detect breakage. No-auth CLIs only.
    canary: list[list[str]] = field(default_factory=list)
    # Optional presentation fields (description, skill, display_website, ...).
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def package(self) -> str:
        """Python sub-package name, e.g. ``gh_trending``."""
        return self.namespace.removeprefix("cli_web.")

    @property
    def app_dir(self) -> str:
        """Top-level app directory, e.g. ``gh-trending``."""
        return self.directory.split("/", 1)[0]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> RegistryEntry:
        missing = [f for f in REQUIRED_FIELDS if f not in raw]
        if missing:
            raise ValueError(
                f"registry entry {raw.get('name', '<unnamed>')!r} missing fields: {missing}"
            )
        extra = {k: v for k, v in raw.items() if k not in REQUIRED_FIELDS and k != "canary"}
        return cls(
            **{f: raw[f] for f in REQUIRED_FIELDS}, canary=raw.get("canary", []), extra=extra
        )


@dataclass
class Registry:
    version: str
    clis: list[RegistryEntry] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> Registry:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            version=raw.get("version", "0"),
            clis=[RegistryEntry.from_dict(e) for e in raw.get("clis", [])],
        )

    def entry(self, name: str) -> RegistryEntry:
        for e in self.clis:
            if e.name == name or e.app_dir == name or e.package == name:
                return e
        raise KeyError(name)


def validate(root: Path) -> list[str]:
    """Return a list of problems (empty list == valid)."""
    problems: list[str] = []
    try:
        registry = Registry.load(root / "registry.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"registry.json unreadable: {exc}"]

    seen_dirs: set[str] = set()
    for e in registry.clis:
        seen_dirs.add(e.app_dir)
        harness = root / e.directory
        if not harness.is_dir():
            problems.append(f"{e.name}: directory {e.directory!r} does not exist")
            continue
        pkg_dir = harness / "cli_web" / e.package
        if not pkg_dir.is_dir():
            problems.append(f"{e.name}: package dir {pkg_dir.relative_to(root)} does not exist")
        if not e.name.startswith("cli-web-"):
            problems.append(f"{e.name}: name must start with 'cli-web-'")
        if not e.namespace.startswith("cli_web."):
            problems.append(f"{e.name}: namespace must start with 'cli_web.'")
        if (
            not e.install.startswith("pip install ")
            or e.name not in e.install
            or " -e " in e.install
        ):
            problems.append(
                f"{e.name}: install must be a public PyPI command for {e.name!r}, got {e.install!r}"
            )
        if not e.commands:
            problems.append(f"{e.name}: commands list is empty")
        for field_name in ("description", "site_icon", "site_category", "site_tags"):
            if not e.extra.get(field_name):
                problems.append(f"{e.name}: missing public site metadata {field_name!r}")
        readme_candidates = (pkg_dir / "README.md", harness / "README.md")
        package_readme = next((path for path in readme_candidates if path.is_file()), None)
        if package_readme is None:
            problems.append(f"{e.name}: package README is missing")
        else:
            readme_text = package_readme.read_text(encoding="utf-8")
            setup_commands = [e.install, *e.extra.get("post_install", [])]
            missing_setup = [command for command in setup_commands if command not in readme_text]
            if missing_setup:
                problems.append(
                    f"{e.name}: package README is missing setup commands {missing_setup!r}"
                )

    for harness in sorted(root.glob("*/agent-harness")):
        app_dir = harness.parent.name
        if app_dir not in seen_dirs:
            problems.append(f"unregistered CLI: {app_dir}/agent-harness has no registry.json entry")

    return problems
