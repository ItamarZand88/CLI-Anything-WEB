"""Gap analysis: captured traffic vs implemented client vs exposed commands.

Deterministic core of the plugin's gap-analyzer skill (`/refine` entry
step). Compares three layers and reports mismatches:

1. **captured** — endpoints in ``traffic-capture/traffic-analysis.json``
2. **implemented** — public methods on ``core/client.py`` (AST, no imports)
3. **exposed** — Click commands in ``commands/*.py`` (AST)

Output is structured so an agent can act on each gap directly.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GapReport:
    captured_endpoints: list[str] = field(default_factory=list)
    client_methods: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    unimplemented_endpoints: list[str] = field(default_factory=list)
    unexposed_methods: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": {
                "captured_endpoints": len(self.captured_endpoints),
                "client_methods": len(self.client_methods),
                "commands": len(self.commands),
                "unimplemented_endpoints": len(self.unimplemented_endpoints),
                "unexposed_methods": len(self.unexposed_methods),
            },
            "unimplemented_endpoints": self.unimplemented_endpoints,
            "unexposed_methods": self.unexposed_methods,
            "captured_endpoints": self.captured_endpoints,
            "client_methods": self.client_methods,
            "commands": self.commands,
        }


def _endpoints_from_analysis(analysis_path: Path) -> list[str]:
    raw = json.loads(analysis_path.read_text(encoding="utf-8"))
    endpoints: list[str] = []
    for ep in raw.get("endpoints", []):
        if isinstance(ep, dict):
            method = ep.get("method", "GET")
            path = ep.get("path") or ep.get("url") or ""
            endpoints.append(f"{method} {path}")
        else:
            endpoints.append(str(ep))
    return sorted(set(endpoints))


def _public_methods(client_path: Path) -> list[str]:
    tree = ast.parse(client_path.read_text(encoding="utf-8"))
    methods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and not item.name.startswith("_"):
                    methods.append(item.name)
    return sorted(set(methods) - {"close"})


def _click_commands(commands_dir: Path) -> list[str]:
    found: list[str] = []
    for py in sorted(commands_dir.glob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for dec in node.decorator_list:
                call = dec if isinstance(dec, ast.Call) else None
                target = call.func if call else dec
                if isinstance(target, ast.Attribute) and target.attr == "command":
                    if call and call.args and isinstance(call.args[0], ast.Constant):
                        found.append(str(call.args[0].value))
                    else:
                        found.append(node.name)
    return sorted(set(found))


def _method_referenced_by_commands(method: str, commands_dir: Path) -> bool:
    needle = f".{method}("
    return any(needle in py.read_text(encoding="utf-8") for py in commands_dir.glob("*.py"))


def analyze(root: Path, app: str) -> GapReport:
    """Build a gap report for one app directory (e.g. ``hackernews``)."""
    app_dir = root / app
    harness_candidates = list(app_dir.glob("agent-harness/cli_web/*/"))
    if not harness_candidates:
        raise FileNotFoundError(f"no agent-harness package under {app_dir}")
    pkg = harness_candidates[0]

    report = GapReport()

    analysis = app_dir / "traffic-capture" / "traffic-analysis.json"
    if analysis.is_file():
        report.captured_endpoints = _endpoints_from_analysis(analysis)

    client = pkg / "core" / "client.py"
    if client.is_file():
        report.client_methods = _public_methods(client)

    commands_dir = pkg / "commands"
    if commands_dir.is_dir():
        report.commands = _click_commands(commands_dir)
        report.unexposed_methods = [
            m for m in report.client_methods if not _method_referenced_by_commands(m, commands_dir)
        ]

    if report.captured_endpoints and client.is_file():
        client_src = client.read_text(encoding="utf-8")
        for endpoint in report.captured_endpoints:
            path = endpoint.split(" ", 1)[-1]
            stem = path.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
            if stem and stem not in client_src:
                report.unimplemented_endpoints.append(endpoint)

    return report
