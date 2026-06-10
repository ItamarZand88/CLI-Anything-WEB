"""Fleet contract assertions.

These encode the externally-observable contract every cli-web-* CLI must
honor (HARNESS.md "Critical Rules" + the standards skill's smoke checks).
Used by the repo-level contract suite (``tests/contract/``) and available
to per-CLI E2E tests.
"""

from __future__ import annotations

import json
import re

from .fixtures import run_cli

# Raw protocol artifacts that must never appear in user-facing output.
PROTOCOL_LEAK_PATTERNS = (
    "wrb.fr",
    "af.httprm",
    ")]}'",
    "batchexecute",
    "__NEXT_DATA__",
)


def assert_no_protocol_leaks(text: str) -> None:
    for pattern in PROTOCOL_LEAK_PATTERNS:
        assert pattern not in text, f"protocol leak {pattern!r} in CLI output"


def assert_help_works(cmd: list[str]) -> str:
    """``<cli> --help`` exits 0 and prints usage."""
    proc = run_cli(cmd, "--help")
    assert proc.returncode == 0, f"--help exited {proc.returncode}: {proc.stderr[:300]}"
    assert "Usage" in proc.stdout or "Commands" in proc.stdout, (
        f"--help output looks wrong: {proc.stdout[:200]!r}"
    )
    return proc.stdout


def assert_version_works(cmd: list[str]) -> str:
    """``<cli> --version`` exits 0 and prints a semver-ish version."""
    proc = run_cli(cmd, "--version")
    assert proc.returncode == 0, f"--version exited {proc.returncode}: {proc.stderr[:300]}"
    assert re.search(r"\d+\.\d+", proc.stdout), f"no version in output: {proc.stdout!r}"
    return proc.stdout


def assert_repl_starts_and_exits(cmd: list[str]) -> str:
    """Piping ``exit`` into the bare CLI starts the REPL and exits cleanly."""
    proc = run_cli(cmd, input_text="exit\n", timeout=90.0)
    assert proc.returncode == 0, (
        f"REPL did not exit cleanly (rc={proc.returncode}): {proc.stderr[:300]}"
    )
    return proc.stdout


def assert_json_envelope(stdout: str) -> dict[str, object]:
    """Output parses as JSON and matches the success/error envelope."""
    payload: dict[str, object] = json.loads(stdout)
    assert isinstance(payload, dict), f"JSON output is not an object: {type(payload)}"
    if payload.get("error"):
        assert "code" in payload and "message" in payload, (
            f"error envelope missing code/message: {payload}"
        )
    else:
        assert payload.get("success") is True and "data" in payload, (
            f"success envelope missing success/data: {payload}"
        )
    return payload
