#!/usr/bin/env python3
"""Capture checkpoint manager — save/restore capture session state.

Prevents duplicate work when capture sessions are interrupted or skills
are re-invoked. Tracks step progress, trace IDs, auth status, and
assessment findings.

Usage:
    # Save current state
    python capture-checkpoint.py save <app-dir> --step post-auth \
        --trace-id trace-1234 --auth-saved --assessment '{"framework":"vite"}'

    # Restore / check state
    python capture-checkpoint.py restore <app-dir>

    # Clear state (start fresh)
    python capture-checkpoint.py clear <app-dir>

    # Update a specific field
    python capture-checkpoint.py update <app-dir> --step full-capture --trace-id trace-5678
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CHECKPOINT_FILE = ".capture-state.json"

# Ordered capture steps — each step implies all previous are complete
STEPS = [
    "setup",           # Browser opened, session started
    "assessment",      # Site fingerprint complete (framework, protection, iframes, auth)
    "post-auth",       # User logged in, auth state saved (skipped if no-auth)
    "tracing",         # Trace started, exploration in progress
    "full-capture",    # Trace stopped, all exploration done
    "parsed",          # parse-trace.py ran, raw-traffic.json produced
    "complete",        # Phase 1 done, ready for Phase 2
]


def _checkpoint_path(app_dir: str) -> Path:
    return Path(app_dir) / "traffic-capture" / CHECKPOINT_FILE


def _load(app_dir: str) -> dict | None:
    p = _checkpoint_path(app_dir)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(app_dir: str, state: dict) -> None:
    p = _checkpoint_path(app_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"Checkpoint saved: {p}")


def cmd_save(args: argparse.Namespace) -> None:
    existing = _load(args.app_dir) or {}
    state = {
        "app_dir": str(Path(args.app_dir).resolve()),
        "step": args.step or existing.get("step", "setup"),
        "created_at": existing.get("created_at", datetime.now(timezone.utc).isoformat()),
        "session_name": args.session or existing.get("session_name"),
        "url": args.url or existing.get("url"),
        "auth_saved": args.auth_saved or existing.get("auth_saved", False),
        "auth_file": args.auth_file or existing.get("auth_file"),
        "traces": existing.get("traces", []),
        "assessment": existing.get("assessment", {}),
        "site_profile": args.site_profile or existing.get("site_profile"),
        "raw_traffic_json": existing.get("raw_traffic_json"),
        "notes": args.notes or existing.get("notes"),
    }

    # Add trace if provided
    if args.trace_id:
        trace_entry = {
            "id": args.trace_id,
            "status": args.trace_status or "active",
            "purpose": args.trace_purpose or "capture",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        # Update existing trace or add new
        updated = False
        for i, t in enumerate(state["traces"]):
            if t["id"] == args.trace_id:
                state["traces"][i].update(trace_entry)
                updated = True
                break
        if not updated:
            state["traces"].append(trace_entry)

    # Parse assessment JSON if provided
    if args.assessment:
        try:
            state["assessment"] = json.loads(args.assessment)
        except json.JSONDecodeError:
            print(f"Warning: could not parse assessment JSON: {args.assessment}", file=sys.stderr)

    _save(args.app_dir, state)


def cmd_restore(args: argparse.Namespace) -> None:
    state = _load(args.app_dir)
    if not state:
        print(json.dumps({"exists": False, "message": "No checkpoint found. Starting fresh."}))
        sys.exit(0)

    step = state.get("step", "setup")
    step_index = STEPS.index(step) if step in STEPS else -1

    # Build resume guidance
    resume = {
        "exists": True,
        "step": step,
        "step_index": step_index,
        "total_steps": len(STEPS),
        "completed_steps": STEPS[:step_index + 1] if step_index >= 0 else [],
        "next_step": STEPS[step_index + 1] if step_index < len(STEPS) - 1 else "done",
        "session_name": state.get("session_name"),
        "url": state.get("url"),
        "auth_saved": state.get("auth_saved", False),
        "site_profile": state.get("site_profile"),
        "active_traces": [t for t in state.get("traces", []) if t.get("status") == "active"],
        "assessment": state.get("assessment", {}),
        "updated_at": state.get("updated_at"),
    }

    # Add human-readable guidance
    if step == "setup":
        resume["guidance"] = "Session started but assessment not done. Run site fingerprint."
    elif step == "assessment":
        if not state.get("auth_saved") and state.get("assessment", {}).get("needs_auth"):
            resume["guidance"] = "Assessment done. Auth required — ask user to log in."
        else:
            resume["guidance"] = "Assessment done. Start full traffic capture."
    elif step == "post-auth":
        resume["guidance"] = "Auth saved. Start full traffic capture."
    elif step == "tracing":
        resume["guidance"] = "Trace is active. Continue exploring or stop trace."
    elif step == "full-capture":
        resume["guidance"] = "Trace stopped. Run parse-trace.py."
    elif step == "parsed":
        resume["guidance"] = "Traffic parsed. Close browser and proceed to Phase 2."
    elif step == "complete":
        resume["guidance"] = "Phase 1 complete. Invoke methodology skill for Phase 2."

    print(json.dumps(resume, indent=2, ensure_ascii=False))


def cmd_update(args: argparse.Namespace) -> None:
    state = _load(args.app_dir)
    if not state:
        print("No checkpoint found. Use 'save' first.", file=sys.stderr)
        sys.exit(1)

    if args.step:
        state["step"] = args.step
    if args.trace_id:
        for t in state.get("traces", []):
            if t["id"] == args.trace_id and args.trace_status:
                t["status"] = args.trace_status
    if args.auth_saved:
        state["auth_saved"] = True
    if args.auth_file:
        state["auth_file"] = args.auth_file
    if args.raw_traffic_json:
        state["raw_traffic_json"] = args.raw_traffic_json
    if args.site_profile:
        state["site_profile"] = args.site_profile
    if args.notes:
        state["notes"] = args.notes

    _save(args.app_dir, state)


def cmd_clear(args: argparse.Namespace) -> None:
    p = _checkpoint_path(args.app_dir)
    if p.exists():
        p.unlink()
        print(f"Checkpoint cleared: {p}")
    else:
        print("No checkpoint to clear.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture checkpoint manager")
    sub = parser.add_subparsers(dest="command", required=True)

    # save
    p_save = sub.add_parser("save", help="Save checkpoint state")
    p_save.add_argument("app_dir", help="App directory (e.g., stitch)")
    p_save.add_argument("--step", choices=STEPS, help="Current step")
    p_save.add_argument("--session", help="Playwright-cli session name")
    p_save.add_argument("--url", help="Target URL")
    p_save.add_argument("--trace-id", help="Trace file ID")
    p_save.add_argument("--trace-status", choices=["active", "stopped", "failed"], default="active")
    p_save.add_argument("--trace-purpose", help="Trace purpose (probe/capture)")
    p_save.add_argument("--auth-saved", action="store_true", help="Auth state has been saved")
    p_save.add_argument("--auth-file", help="Path to auth state file")
    p_save.add_argument("--assessment", help="Assessment findings as JSON string")
    p_save.add_argument("--site-profile", help="Site profile classification")
    p_save.add_argument("--notes", help="Free-text notes")
    p_save.set_defaults(func=cmd_save)

    # restore
    p_restore = sub.add_parser("restore", help="Restore/check checkpoint state")
    p_restore.add_argument("app_dir", help="App directory")
    p_restore.set_defaults(func=cmd_restore)

    # update
    p_update = sub.add_parser("update", help="Update specific fields")
    p_update.add_argument("app_dir", help="App directory")
    p_update.add_argument("--step", choices=STEPS, help="Update current step")
    p_update.add_argument("--trace-id", help="Trace ID to update")
    p_update.add_argument("--trace-status", choices=["active", "stopped", "failed"])
    p_update.add_argument("--auth-saved", action="store_true")
    p_update.add_argument("--auth-file", help="Path to auth state file")
    p_update.add_argument("--raw-traffic-json", help="Path to raw-traffic.json")
    p_update.add_argument("--site-profile", help="Site profile classification")
    p_update.add_argument("--notes", help="Free-text notes")
    p_update.set_defaults(func=cmd_update)

    # clear
    p_clear = sub.add_parser("clear", help="Clear checkpoint (start fresh)")
    p_clear.add_argument("app_dir", help="App directory")
    p_clear.set_defaults(func=cmd_clear)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
