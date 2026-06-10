"""Fleet canary: run registered read-only commands against live sites.

Target sites change under the fleet (new anti-bot protection, markup
changes, API moves). Each registry entry may declare ``canary`` — a list
of argv suffixes that are safe, read-only, auth-free, and expected to
produce a valid ``--json`` envelope. A scheduled workflow runs them and
opens an issue when a CLI breaks, closing the loop that ``/refine`` opens.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .registry import Registry, RegistryEntry


@dataclass
class CanaryResult:
    cli: str
    argv: list[str]
    ok: bool
    detail: str = ""


@dataclass
class CanaryReport:
    results: list[CanaryResult] = field(default_factory=list)

    @property
    def failures(self) -> list[CanaryResult]:
        return [r for r in self.results if not r.ok]

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": not self.failures,
            "total": len(self.results),
            "failed": len(self.failures),
            "results": [asdict(r) for r in self.results],
        }


def _parse_json_output(stdout: str) -> object:
    """Parse CLI --json output, tolerating leading spinner/log noise."""
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        pass
    lines = stdout.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith(("{", "[")):
            return json.loads("\n".join(lines[i:]))
    raise json.JSONDecodeError("no JSON object found", stdout, 0)


def _check_envelope(stdout: str) -> str | None:
    """Return an error description, or None if the output is healthy.

    Pre-v2.1 fleet CLIs emit bare JSON arrays/objects rather than the
    ``{"success": true, "data": ...}`` envelope (CONVENTIONS.md §Exit Codes
    fleet note); the canary asks "is the site still serving us data", so any
    valid JSON that is not an error envelope counts as healthy.
    """
    try:
        payload = _parse_json_output(stdout)
    except json.JSONDecodeError as exc:
        return f"output is not JSON: {exc}"
    if not isinstance(payload, dict):
        return None  # legacy bare-array output
    if payload.get("error"):
        return f"CLI returned error envelope: {payload.get('code')}: {payload.get('message')}"
    if "success" in payload and (payload.get("success") is not True or "data" not in payload):
        return f"not a success envelope: keys={sorted(payload)}"
    return None


def _run_one(entry: RegistryEntry, argv: list[str], timeout: float) -> CanaryResult:
    binary = shutil.which(entry.name)
    if binary is None:
        return CanaryResult(entry.name, argv, False, "CLI not installed (not on PATH)")
    try:
        proc = subprocess.run(
            [binary, *argv],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CanaryResult(entry.name, argv, False, f"timed out after {timeout}s")
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip()
        return CanaryResult(entry.name, argv, False, f"exit {proc.returncode}: {detail[:300]}")
    problem = _check_envelope(proc.stdout)
    if problem:
        return CanaryResult(entry.name, argv, False, problem)
    return CanaryResult(entry.name, argv, True)


def run_canaries(
    root: Path, names: list[str] | None = None, timeout: float = 120.0
) -> CanaryReport:
    registry = Registry.load(root / "registry.json")
    entries = registry.clis if not names else [registry.entry(n) for n in names]
    report = CanaryReport()
    for entry in entries:
        for argv in entry.canary:
            report.results.append(_run_one(entry, list(argv), timeout))
    return report
