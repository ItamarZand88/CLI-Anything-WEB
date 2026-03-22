#!/usr/bin/env python3
"""Pipeline phase state manager — track progress across all 4 phases.

Prevents re-running expensive phases when later phases fail. Each phase
records its status, output files, and timestamps. Supports --force to
clear and re-run a completed phase.

Usage:
    # Check pipeline state
    python phase-state.py status <app-dir>

    # Mark a phase as complete
    python phase-state.py complete <app-dir> --phase capture \
        --output traffic-capture/raw-traffic.json

    # Mark a phase as failed
    python phase-state.py fail <app-dir> --phase testing \
        --error "3 tests failed" --error-type retryable

    # Reset a phase (force re-run)
    python phase-state.py reset <app-dir> --phase methodology

    # Check if a phase should be skipped (already complete)
    python phase-state.py check <app-dir> --phase capture
    # Exit code 0 = skip (already done), 1 = run (not done)
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = "phase-state.json"
PHASES = ["capture", "methodology", "testing", "standards"]


def _state_path(app_dir: str) -> Path:
    return Path(app_dir) / STATE_FILE


def _load(app_dir: str) -> dict:
    p = _state_path(app_dir)
    if not p.exists():
        return {
            "app_dir": str(Path(app_dir).resolve()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "phases": {phase: {"status": "pending"} for phase in PHASES},
        }
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(app_dir: str, state: dict) -> None:
    p = _state_path(app_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def cmd_status(args: argparse.Namespace) -> None:
    state = _load(args.app_dir)
    phases = state.get("phases", {})

    result = {
        "app_dir": state.get("app_dir"),
        "phases": {},
        "current_phase": None,
        "next_action": None,
    }

    for phase in PHASES:
        info = phases.get(phase, {"status": "pending"})
        result["phases"][phase] = info

        if info["status"] == "pending" and result["current_phase"] is None:
            result["current_phase"] = phase
        elif info["status"] == "failed":
            result["current_phase"] = phase

    # Determine next action
    current = result["current_phase"]
    if current is None:
        result["next_action"] = "All phases complete! CLI is ready."
    elif phases.get(current, {}).get("status") == "failed":
        error_type = phases[current].get("error_type", "unknown")
        if error_type == "retryable":
            result["next_action"] = f"Retry {current} phase (previous attempt failed with retryable error)"
        else:
            result["next_action"] = f"Fix {current} phase failure, then use --force to re-run"
    else:
        result["next_action"] = f"Run {current} phase"

    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_complete(args: argparse.Namespace) -> None:
    state = _load(args.app_dir)
    state["phases"][args.phase] = {
        "status": "done",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "output": args.output,
        "notes": args.notes,
    }
    _save(args.app_dir, state)
    print(f"Phase '{args.phase}' marked complete.")


def cmd_fail(args: argparse.Namespace) -> None:
    state = _load(args.app_dir)
    state["phases"][args.phase] = {
        "status": "failed",
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "error": args.error,
        "error_type": args.error_type or "unknown",
    }
    _save(args.app_dir, state)
    print(f"Phase '{args.phase}' marked as failed ({args.error_type}).")


def cmd_reset(args: argparse.Namespace) -> None:
    state = _load(args.app_dir)
    state["phases"][args.phase] = {"status": "pending"}
    _save(args.app_dir, state)
    print(f"Phase '{args.phase}' reset to pending.")


def cmd_check(args: argparse.Namespace) -> None:
    """Exit 0 if phase is done (skip), exit 1 if needs running."""
    state = _load(args.app_dir)
    phase_info = state.get("phases", {}).get(args.phase, {})
    if phase_info.get("status") == "done" and not args.force:
        print(json.dumps({
            "skip": True,
            "reason": f"Phase '{args.phase}' already completed at {phase_info.get('completed_at')}",
            "output": phase_info.get("output"),
        }))
        sys.exit(0)
    else:
        print(json.dumps({
            "skip": False,
            "reason": f"Phase '{args.phase}' needs to run (status: {phase_info.get('status', 'pending')})",
        }))
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline phase state manager")
    sub = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = sub.add_parser("status", help="Show pipeline state")
    p_status.add_argument("app_dir", help="App directory")
    p_status.set_defaults(func=cmd_status)

    # complete
    p_complete = sub.add_parser("complete", help="Mark phase as complete")
    p_complete.add_argument("app_dir", help="App directory")
    p_complete.add_argument("--phase", required=True, choices=PHASES)
    p_complete.add_argument("--output", help="Output file/directory path")
    p_complete.add_argument("--notes", help="Additional notes")
    p_complete.set_defaults(func=cmd_complete)

    # fail
    p_fail = sub.add_parser("fail", help="Mark phase as failed")
    p_fail.add_argument("app_dir", help="App directory")
    p_fail.add_argument("--phase", required=True, choices=PHASES)
    p_fail.add_argument("--error", required=True, help="Error description")
    p_fail.add_argument("--error-type", choices=["retryable", "fatal", "unknown"], default="unknown")
    p_fail.set_defaults(func=cmd_fail)

    # reset
    p_reset = sub.add_parser("reset", help="Reset phase to pending (force re-run)")
    p_reset.add_argument("app_dir", help="App directory")
    p_reset.add_argument("--phase", required=True, choices=PHASES)
    p_reset.set_defaults(func=cmd_reset)

    # check
    p_check = sub.add_parser("check", help="Check if phase should be skipped")
    p_check.add_argument("app_dir", help="App directory")
    p_check.add_argument("--phase", required=True, choices=PHASES)
    p_check.add_argument("--force", action="store_true", help="Force re-run even if done")
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
