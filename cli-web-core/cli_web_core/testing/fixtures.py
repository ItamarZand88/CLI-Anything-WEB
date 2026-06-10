"""Subprocess test helpers — the canonical ``_resolve_cli`` pattern.

Every generated CLI's E2E suite re-implements these three helpers today;
this module is the single home for them (HARNESS.md "E2E tests include
subprocess tests via _resolve_cli()").
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Any


def resolve_cli(cli_name: str) -> list[str]:
    """Locate the installed CLI binary, or fall back to ``python -m ...``.

    If ``CLI_WEB_FORCE_INSTALLED=1`` is set, raise if the binary is not on
    PATH instead of falling back (used to make CI prove the entry point).
    """
    forced = os.environ.get("CLI_WEB_FORCE_INSTALLED") == "1"
    path = shutil.which(cli_name)
    if path:
        return [path]
    if forced:
        raise RuntimeError(
            f"CLI_WEB_FORCE_INSTALLED=1 but {cli_name!r} not found on PATH. "
            "Run `pip install -e .` in agent-harness/ before running subprocess tests."
        )
    module = cli_name.replace("cli-web-", "cli_web.").replace("-", "_")
    return [sys.executable, "-m", module]


def run_cli(
    cmd: list[str],
    *args: str,
    input_text: str | None = None,
    timeout: float = 60.0,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a CLI subprocess with sane defaults (text mode, captured output)."""
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        [*cmd, *args],
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=full_env,
        check=False,
    )


def parse_json_output(stdout: str) -> Any:
    """Parse CLI ``--json`` output, tolerating leading spinner/log noise.

    Finds the first line starting with ``{`` or ``[`` and parses from there.
    """
    stripped = stdout.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    lines = stripped.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith(("{", "[")):
            return json.loads("\n".join(lines[i:]))
    raise ValueError(f"No JSON found in output: {stripped[:200]!r}")
