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
    status: str = "ok"  # "ok" | "blocked" | "broken"


@dataclass
class CanaryReport:
    results: list[CanaryResult] = field(default_factory=list)

    @property
    def failures(self) -> list[CanaryResult]:
        return [r for r in self.results if not r.ok]

    @property
    def broken(self) -> list[CanaryResult]:
        """Actionable failures — the CLI's own logic/parsing broke."""
        return [r for r in self.results if r.status == "broken"]

    @property
    def blocked(self) -> list[CanaryResult]:
        """Non-actionable failures — the target bot-blocked/rate-limited our IP."""
        return [r for r in self.results if r.status == "blocked"]

    def to_dict(self) -> dict[str, object]:
        return {
            # A target blocking a hosted-runner IP is diagnostic context, not
            # fleet breakage. Keep JSON semantics aligned with the CLI exit
            # code, which fails only when actionable `broken` results exist.
            "ok": not self.broken,
            "total": len(self.results),
            "failed": len(self.failures),
            "broken": len(self.broken),
            "blocked": len(self.blocked),
            "results": [asdict(r) for r in self.results],
        }


# Anti-bot / rate-limit / transient signatures. When a canary fails with one of
# these, the target blocked our (datacenter) runner IP or throttled us — the CLI
# still works for real users, so this is NOT actionable via /refine and must not
# masquerade as "site breakage". Everything else is a real logic/parse break.
_BLOCKED_MARKERS = (
    "403",
    "429",
    "502",
    "503",
    "cloudflare",
    "just a moment",
    "not a bot",
    "bm-verify",
    "anubis",
    "captcha",
    "datadome",
    "perimeterx",
    "akamai",
    "rate limit",
    "rate_limited",
    "auth_expired",
    "server_error",
    "challenge",
    "verify you are human",
    "access denied",
    "forbidden",
    "too many requests",
    "timed out",
)


def _classify_failure(*signals: str) -> str:
    """Classify a failure as 'blocked' (anti-bot/transient) or 'broken' (logic)."""
    haystack = " ".join(signals).lower()
    return "blocked" if any(marker in haystack for marker in _BLOCKED_MARKERS) else "broken"


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

    The canary asks one question: "is the site still serving us data?" — so
    any valid JSON that is not an *error* response counts as healthy. It does
    not police envelope style: the fleet's dominant success shape is
    ``{"success": true, <domain fields>}`` (suggestions, locations, items…),
    a handful wrap payloads as ``{"success": true, "data": ...}``, and pre-v2.1
    CLIs emit bare arrays/objects. All three are live-site-healthy. Envelope
    conformance is the contract test's job (``cli-web-devkit contract``), not
    this live smoke — enforcing it here turns ordinary style drift into
    false "site breakage" alerts.

    Rejected: non-JSON output, an ``{"error": true}`` envelope, or an explicit
    ``{"success": false}``.
    """
    try:
        payload = _parse_json_output(stdout)
    except json.JSONDecodeError as exc:
        return f"output is not JSON: {exc}"
    if not isinstance(payload, dict):
        return None  # legacy bare-array output
    if payload.get("error"):
        return f"CLI returned error envelope: {payload.get('code')}: {payload.get('message')}"
    if "success" in payload and payload.get("success") is not True:
        return (
            f"not a success envelope (success={payload.get('success')!r}): keys={sorted(payload)}"
        )
    return None


def _run_one(entry: RegistryEntry, argv: list[str], timeout: float) -> CanaryResult:
    binary = shutil.which(entry.name)
    if binary is None:
        return CanaryResult(entry.name, argv, False, "CLI not installed (not on PATH)", "broken")
    try:
        proc = subprocess.run(
            [binary, *argv],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CanaryResult(entry.name, argv, False, f"timed out after {timeout}s", "blocked")
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip()
        detail = f"exit {proc.returncode}: {detail[:300]}"
        return CanaryResult(entry.name, argv, False, detail, _classify_failure(detail))
    problem = _check_envelope(proc.stdout)
    if problem:
        # A non-JSON body is usually an anti-bot interstitial, not a logic break —
        # classify on the problem text plus a slice of the raw output.
        status = _classify_failure(problem, proc.stdout[:300])
        return CanaryResult(entry.name, argv, False, problem, status)
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
