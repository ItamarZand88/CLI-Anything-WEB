#!/usr/bin/env python3
"""Pipeline orchestrator — one-stop status and next-action guidance.

The 4-phase pipeline (capture → methodology → testing → standards) is executed
by skills invoked inside Claude Code. This orchestrator does NOT run the skills
itself; instead, it reads the current pipeline state and prints:

1. The per-phase status (pending / in-progress / done / failed)
2. The current phase and the script/skill that advances it
3. Copy-paste commands for the next action

It also exposes two fully-automated sub-phases that don't need a Claude turn:
- `parse` runs parse-trace.py → analyze-traffic.py on a traces directory
- `validate` runs validate-checklist.py + smoke-test.py

Usage:
    # Show full pipeline status + next action
    python run-pipeline.py status <app-dir>

    # Run the scriptable parse step (Phase 1 tail)
    python run-pipeline.py parse <app-dir> --traces-dir .playwright-cli/traces/

    # Run the scriptable validation step (Phase 4 tail)
    python run-pipeline.py validate <app-dir> --cli-name cli-web-foo
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from plugin_paths import get_scripts_dir  # noqa: E402
from state_utils import load_json_state  # noqa: E402

PHASES = ["capture", "methodology", "testing", "standards"]

# Human-readable next-action guidance per phase. Skills are the primary
# execution units; scripts are scriptable sub-steps.
_NEXT_ACTION = {
    "capture": {
        "skill": "capture",
        "script": "parse-trace.py / analyze-traffic.py",
        "how": "Invoke the capture skill, then `run-pipeline.py parse`",
    },
    "methodology": {
        "skill": "methodology",
        "script": "scaffold-cli.py",
        "how": "Invoke the methodology skill (it calls scaffold-cli.py)",
    },
    "testing": {
        "skill": "testing",
        "script": "generate-test-docs.py",
        "how": "Invoke the testing skill (it calls generate-test-docs.py)",
    },
    "standards": {
        "skill": "standards",
        "script": "validate-checklist.py / smoke-test.py",
        "how": "Invoke the standards skill, then `run-pipeline.py validate`",
    },
}


def _read_phase_state(app_dir: Path) -> dict:
    """Load phase-state.json if present; return a pending-default shape otherwise."""
    state_file = app_dir / "phase-state.json"
    default = {"phases": {p: {"status": "pending"} for p in PHASES}}
    return load_json_state(state_file, default=default)


def _first_incomplete_phase(phases: dict) -> str | None:
    """Return the first phase that is not `done`, or None if all are done."""
    for phase in PHASES:
        if phases.get(phase, {}).get("status") != "done":
            return phase
    return None


def cmd_status(args: argparse.Namespace) -> None:
    app_dir = Path(args.app_dir).resolve()
    state = _read_phase_state(app_dir)
    phases = state.get("phases", {})
    current = _first_incomplete_phase(phases)

    report = {
        "app_dir": str(app_dir),
        "phases": {p: phases.get(p, {"status": "pending"}) for p in PHASES},
        "current_phase": current,
        "next_action": None,
    }

    if current is None:
        report["next_action"] = {
            "summary": "Pipeline complete — all 4 phases done.",
            "skill": None,
            "script": None,
        }
    else:
        info = dict(_NEXT_ACTION[current])
        info["summary"] = f"Run the {current} phase."
        report["next_action"] = info

    print(json.dumps(report, indent=2, ensure_ascii=False))


def _run(cmd: list[str]) -> int:
    """Run a subprocess, stream its output, return exit code."""
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.call(cmd)


def cmd_parse(args: argparse.Namespace) -> None:
    """Scriptable Phase-1 tail: parse traces → raw-traffic.json + analysis."""
    scripts = get_scripts_dir()
    output = Path(args.app_dir) / "traffic-capture" / "raw-traffic.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    rc = _run([
        sys.executable, str(scripts / "parse-trace.py"),
        args.traces_dir,
        "--output", str(output),
    ])
    if rc != 0:
        sys.exit(rc)

    # parse-trace.py auto-invokes analyze-traffic.py when possible;
    # no separate call needed.
    print(f"\nDone. Raw traffic: {output}")
    print(f"Analysis: {output.parent / 'traffic-analysis.json'}")


def cmd_validate(args: argparse.Namespace) -> None:
    """Scriptable Phase-4 tail: validate-checklist + smoke-test."""
    scripts = get_scripts_dir()
    app_dir = Path(args.app_dir).resolve()

    rc = _run([
        sys.executable, str(scripts / "validate-checklist.py"),
        str(app_dir),
    ])
    if rc != 0 and not args.keep_going:
        sys.exit(rc)

    if args.cli_name:
        rc = _run([
            sys.executable, str(scripts / "smoke-test.py"),
            args.cli_name,
        ])
        if rc != 0 and not args.keep_going:
            sys.exit(rc)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline orchestrator — status view + scriptable sub-steps."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="Show pipeline state + next action")
    p_status.add_argument("app_dir", help="App directory (e.g., hackernews)")
    p_status.set_defaults(func=cmd_status)

    p_parse = sub.add_parser("parse", help="Run parse-trace.py + analyze-traffic.py")
    p_parse.add_argument("app_dir", help="App directory")
    p_parse.add_argument(
        "--traces-dir",
        required=True,
        help="Path to .playwright-cli/traces/ directory",
    )
    p_parse.set_defaults(func=cmd_parse)

    p_validate = sub.add_parser("validate", help="Run validate-checklist.py + smoke-test.py")
    p_validate.add_argument("app_dir", help="App directory")
    p_validate.add_argument(
        "--cli-name",
        help="CLI binary name (e.g. cli-web-foo); required for smoke-test",
    )
    p_validate.add_argument(
        "--keep-going",
        action="store_true",
        help="Don't stop on first failure",
    )
    p_validate.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
