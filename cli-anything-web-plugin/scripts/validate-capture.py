#!/usr/bin/env python3
"""Validate a Phase-1 capture before handing off to Phase 2 (methodology).

Reads raw-traffic.json and traffic-analysis.json for a CLI app and runs the
checks that should be verified before marking capture complete. Bad captures
produce broken generated CLIs — this script catches the common failure modes:

- Sparse capture (too few entries; user browsed too little)
- Unknown protocol (analyzer couldn't classify — missing or scrambled traffic)
- No WRITE operations (CRUD site without any POST/PUT/DELETE captured)
- Truncated bodies (response_body missing on large responses)
- Dominant error responses (mostly 4xx/5xx means capture was broken)

Usage:
    # Strict mode — fails on any issue (exit code 1):
    python validate-capture.py <app-dir>

    # Read-only site (skip WRITE-op check):
    python validate-capture.py <app-dir> --read-only

    # Custom threshold:
    python validate-capture.py <app-dir> --min-entries 30

    # JSON report for agent consumption:
    python validate-capture.py <app-dir> --json

Exit codes:
    0 = all checks passed (or only warnings)
    1 = at least one blocking failure
    2 = traffic files missing / malformed
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Check:
    name: str
    status: str  # "pass" | "warn" | "fail"
    detail: str = ""


@dataclass
class Report:
    app_dir: str
    checks: list[Check] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.checks.append(Check(name=name, status=status, detail=detail))

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if c.status == "fail"]

    @property
    def warned(self) -> list[Check]:
        return [c for c in self.checks if c.status == "warn"]

    def to_dict(self) -> dict:
        return {
            "app_dir": self.app_dir,
            "overall": "fail" if self.failed else ("warn" if self.warned else "pass"),
            "checks": [{"name": c.name, "status": c.status, "detail": c.detail} for c in self.checks],
        }


# --- Individual checks -----------------------------------------------------

def check_entry_count(entries: list[dict], min_entries: int, report: Report) -> None:
    count = len(entries)
    if count == 0:
        report.add("entry_count", "fail", "raw-traffic.json is empty")
    elif count < min_entries:
        report.add(
            "entry_count", "fail",
            f"only {count} entries (< {min_entries}); browsing was too shallow",
        )
    else:
        report.add("entry_count", "pass", f"{count} entries captured")


def check_protocol_identified(analysis: dict, report: Report) -> None:
    protocol = (analysis.get("protocol") or {}).get("protocol", "unknown")
    confidence = (analysis.get("protocol") or {}).get("confidence", 0)
    if protocol == "unknown":
        report.add("protocol", "fail", "protocol=unknown; analyzer could not classify traffic")
    elif confidence < 50:
        report.add("protocol", "warn", f"protocol={protocol} but low confidence ({confidence}%)")
    else:
        report.add("protocol", "pass", f"protocol={protocol} (confidence={confidence}%)")


def check_write_operations(entries: list[dict], read_only: bool, report: Report) -> None:
    if read_only:
        report.add("write_ops", "pass", "read-only site (skipped)")
        return

    write_methods = {"POST", "PUT", "PATCH", "DELETE"}
    writes = [
        e for e in entries
        if (e.get("method") or "").upper() in write_methods
    ]
    if not writes:
        report.add(
            "write_ops", "fail",
            "no POST/PUT/PATCH/DELETE captured; either browse and submit a form, "
            "or pass --read-only if this is intentional",
        )
    else:
        methods = sorted({(e.get("method") or "").upper() for e in writes})
        report.add("write_ops", "pass", f"{len(writes)} write ops ({', '.join(methods)})")


def check_body_fidelity(entries: list[dict], report: Report) -> None:
    """Warn if too many API responses have no body (likely truncation)."""
    api_like = [
        e for e in entries
        if (e.get("status") or 0) < 400
        and (e.get("method") or "").upper() in ("GET", "POST", "PUT", "PATCH")
        and _looks_like_api(e)
    ]
    if not api_like:
        report.add("body_fidelity", "warn", "no API-like responses to sample")
        return

    with_body = [e for e in api_like if e.get("response_body") not in (None, "", "[binary content]")]
    ratio = len(with_body) / len(api_like)
    if ratio < 0.3:
        report.add(
            "body_fidelity", "warn",
            f"only {int(ratio * 100)}% of API responses have bodies; possible truncation "
            f"(consider --mitmproxy mode for large payloads)",
        )
    else:
        report.add("body_fidelity", "pass", f"{int(ratio * 100)}% of API responses have bodies")


def _looks_like_api(entry: dict) -> bool:
    mime = (entry.get("mime_type") or "").lower()
    return (
        "json" in mime
        or "xml" in mime
        or "graphql" in (entry.get("url") or "").lower()
    )


def check_error_rate(entries: list[dict], report: Report) -> None:
    """Fail if captured traffic is dominated by errors — usually means auth failure."""
    if not entries:
        return
    errors = [e for e in entries if (e.get("status") or 0) >= 400]
    ratio = len(errors) / len(entries)
    if ratio > 0.5:
        report.add(
            "error_rate", "fail",
            f"{int(ratio * 100)}% of responses are 4xx/5xx; capture likely had auth or "
            f"rate-limit failure",
        )
    elif ratio > 0.25:
        report.add("error_rate", "warn", f"{int(ratio * 100)}% error rate (elevated)")
    else:
        report.add("error_rate", "pass", f"{int(ratio * 100)}% error rate")


def check_endpoint_diversity(entries: list[dict], report: Report) -> None:
    """Sparse capture: only 1-2 distinct paths = browsing didn't exercise enough."""
    paths = set()
    for e in entries:
        url = e.get("url") or ""
        if not url:
            continue
        path = url.split("?")[0].split("#")[0]
        paths.add(path)
    if len(paths) < 3:
        report.add(
            "endpoint_diversity", "fail",
            f"only {len(paths)} distinct URL paths; explore more of the app UI",
        )
    elif len(paths) < 8:
        report.add("endpoint_diversity", "warn", f"only {len(paths)} distinct paths (thin)")
    else:
        report.add("endpoint_diversity", "pass", f"{len(paths)} distinct paths")


# --- Entry point -----------------------------------------------------------

def load_capture(app_dir: Path) -> tuple[list[dict], dict]:
    """Return (entries, analysis). Raises FileNotFoundError if files missing."""
    raw = app_dir / "traffic-capture" / "raw-traffic.json"
    analysis = app_dir / "traffic-capture" / "traffic-analysis.json"
    if not raw.exists():
        raise FileNotFoundError(f"raw-traffic.json not found at {raw}")
    entries = json.loads(raw.read_text(encoding="utf-8"))
    analysis_data = json.loads(analysis.read_text(encoding="utf-8")) if analysis.exists() else {}
    return entries, analysis_data


def validate(app_dir: Path, read_only: bool, min_entries: int) -> Report:
    entries, analysis = load_capture(app_dir)
    report = Report(app_dir=str(app_dir))

    check_entry_count(entries, min_entries, report)
    check_endpoint_diversity(entries, report)
    check_protocol_identified(analysis, report)
    check_write_operations(entries, read_only, report)
    check_body_fidelity(entries, report)
    check_error_rate(entries, report)

    return report


def print_human(report: Report) -> None:
    total = len(report.checks)
    passed = sum(1 for c in report.checks if c.status == "pass")
    for c in report.checks:
        marker = {"pass": "[PASS]", "warn": "[WARN]", "fail": "[FAIL]"}[c.status]
        line = f"{marker} {c.name}"
        if c.detail:
            line += f"  —  {c.detail}"
        print(line)
    print()
    print(f"{passed}/{total} checks passed", end="")
    if report.warned:
        print(f", {len(report.warned)} warning(s)", end="")
    if report.failed:
        print(f", {len(report.failed)} failure(s)", end="")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a Phase-1 capture before handing off to methodology."
    )
    parser.add_argument("app_dir", type=Path, help="App directory (e.g., hackernews)")
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Skip the WRITE-op requirement (for genuinely read-only sites)",
    )
    parser.add_argument(
        "--min-entries",
        type=int,
        default=15,
        help="Minimum entries required (default: 15)",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON report")
    args = parser.parse_args()

    try:
        report = validate(args.app_dir, args.read_only, args.min_entries)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as exc:
        print(f"error: malformed traffic JSON: {exc}", file=sys.stderr)
        sys.exit(2)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print_human(report)

    sys.exit(1 if report.failed else 0)


if __name__ == "__main__":
    main()
