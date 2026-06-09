"""``cli-web-devkit`` — fleet tooling entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .canary import run_canaries
from .docs import generate as generate_docs
from .gaps import analyze as analyze_gaps
from .matrix import render_matrix
from .paths import repo_root
from .registry import validate as validate_registry
from .spec import validate_file as validate_spec_file
from .sync import drift, resync


def _cmd_registry_validate(args: argparse.Namespace) -> int:
    problems = validate_registry(args.root)
    if problems:
        print("registry.json validation FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("registry.json OK")
    return 0


def _cmd_matrix(args: argparse.Namespace) -> int:
    print(render_matrix(args.root))
    return 0


def _cmd_docs(args: argparse.Namespace) -> int:
    fresh = generate_docs(args.root, check=args.check)
    if args.check:
        if fresh:
            print("README.md fleet sections are up to date")
            return 0
        print(
            "README.md fleet sections are STALE — run: cli-web-devkit docs",
            file=sys.stderr,
        )
        return 1
    print("README.md regenerated" if not fresh else "README.md already up to date")
    return 0


def _cmd_drift(args: argparse.Namespace) -> int:
    items = drift(args.root)
    bad = [i for i in items if i.status in ("drifted", "missing")]
    for item in items:
        if args.verbose or item.status != "ok":
            detail = f"  ({item.detail})" if item.detail else ""
            print(f"{item.status.upper():9} {item.cli:24} {item.file}{detail}")
    print(f"\n{len(items) - len(bad)} ok, {len(bad)} drifted/missing")
    return 1 if bad else 0


def _cmd_canary(args: argparse.Namespace) -> int:
    import json as _json

    report = run_canaries(args.root, names=args.app or None, timeout=args.timeout)
    if args.json_out:
        print(_json.dumps(report.to_dict(), indent=2))
    else:
        for r in report.results:
            mark = "PASS" if r.ok else "FAIL"
            detail = f"  ({r.detail})" if r.detail else ""
            print(f"{mark}  {r.cli:24} {' '.join(r.argv)}{detail}")
        print(
            f"\n{len(report.results) - len(report.failures)} passed, {len(report.failures)} failed"
        )
    return 1 if report.failures else 0


def _cmd_gaps(args: argparse.Namespace) -> int:
    import json as _json

    report = analyze_gaps(args.root, args.app)
    print(_json.dumps(report.to_dict(), indent=2))
    return 1 if (report.unimplemented_endpoints or report.unexposed_methods) else 0


def _cmd_spec_validate(args: argparse.Namespace) -> int:
    problems = validate_spec_file(Path(args.spec))
    if problems:
        print("api-spec validation FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("api-spec OK")
    return 0


def _cmd_resync(args: argparse.Namespace) -> int:
    changed = resync(args.root, apps=args.app or None)
    if changed:
        print(f"resynced {len(changed)} file(s):")
        for path in changed:
            print(f"  {path}")
    else:
        print("fleet already in sync")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli-web-devkit", description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repo root (auto-detected from cwd by default)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_reg = sub.add_parser("registry", help="Registry operations")
    reg_sub = p_reg.add_subparsers(dest="registry_command", required=True)
    p_val = reg_sub.add_parser("validate", help="Validate registry.json against the fleet")
    p_val.set_defaults(func=_cmd_registry_validate)

    p_matrix = sub.add_parser("matrix", help="Emit GitHub Actions test matrix JSON")
    p_matrix.set_defaults(func=_cmd_matrix)

    p_drift = sub.add_parser("drift", help="Detect vendored shared files diverging from canon")
    p_drift.add_argument("--verbose", action="store_true", help="Also list in-sync files")
    p_drift.set_defaults(func=_cmd_drift)

    p_resync = sub.add_parser("resync", help="Rewrite vendored shared files from canon")
    p_resync.add_argument(
        "--app",
        action="append",
        help="Limit to specific app(s); default: whole fleet + plugin copy",
    )
    p_resync.set_defaults(func=_cmd_resync)

    p_canary = sub.add_parser("canary", help="Run registered live-site canary commands")
    p_canary.add_argument("--app", action="append", help="Limit to specific app(s)")
    p_canary.add_argument("--json", action="store_true", dest="json_out", help="JSON report")
    p_canary.add_argument("--timeout", type=float, default=120.0)
    p_canary.set_defaults(func=_cmd_canary)

    p_docs = sub.add_parser("docs", help="Regenerate README fleet sections from registry.json")
    p_docs.add_argument("--check", action="store_true", help="Fail if README is stale")
    p_docs.set_defaults(func=_cmd_docs)

    p_gaps = sub.add_parser("gaps", help="Captured-vs-implemented-vs-exposed gap report")
    p_gaps.add_argument("app", help="App directory name (e.g. hackernews)")
    p_gaps.set_defaults(func=_cmd_gaps)

    p_spec = sub.add_parser("spec", help="api-spec.json operations")
    spec_sub = p_spec.add_subparsers(dest="spec_command", required=True)
    p_spec_val = spec_sub.add_parser("validate", help="Validate an api-spec.json file")
    p_spec_val.add_argument("spec", help="Path to api-spec.json")
    p_spec_val.set_defaults(func=_cmd_spec_validate)

    args = parser.parse_args(argv)
    if args.root is None:
        args.root = repo_root(Path.cwd())
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
