"""``doctor`` — self-diagnosis for cli-web-* CLIs.

CANONICAL SOURCE: cli-web-core/cli_web_core/doctor.py
Vendored into every generated CLI at cli_web/<app>/utils/doctor.py by
`cli-web-devkit resync`. Do not edit vendored copies by hand.

Checks the local environment a support thread would ask about first:
installation, Python version, config directory, auth material (when the
CLI has an auth module), and optional dependencies. Read-only — never
mutates state, never touches the network.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class DoctorCheck:
    name: str
    status: str  # "ok" | "warn" | "fail"
    detail: str = ""


def _check_entry_point(app_name: str) -> DoctorCheck:
    binary = f"cli-web-{app_name}"
    path = shutil.which(binary)
    if path:
        return DoctorCheck("entry point", "ok", path)
    return DoctorCheck(
        "entry point",
        "warn",
        f"{binary} not on PATH — run `pip install -e .` in agent-harness/ "
        f"(python -m fallback still works)",
    )


def _check_python() -> DoctorCheck:
    # Intentional runtime guard: direct-source runs bypass pip's
    # python_requires, so the interpreter check must live here.
    if sys.version_info >= (3, 10):  # noqa: UP036
        return DoctorCheck("python", "ok", sys.version.split()[0])
    return DoctorCheck("python", "fail", f"{sys.version.split()[0]} < 3.10 (unsupported)")


def _config_dir(app_name: str) -> Path:
    return Path.home() / ".config" / f"cli-web-{app_name}"


def _check_config_dir(app_name: str) -> DoctorCheck:
    cfg = _config_dir(app_name)
    if not cfg.exists():
        return DoctorCheck("config dir", "ok", f"{cfg} (not created yet — created on first use)")
    if os.access(cfg, os.W_OK):
        return DoctorCheck("config dir", "ok", str(cfg))
    return DoctorCheck("config dir", "fail", f"{cfg} is not writable")


def _has_auth_module(pkg: str) -> bool:
    try:
        return importlib.util.find_spec(f"cli_web.{pkg}.core.auth") is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _check_auth(app_name: str, pkg: str) -> list[DoctorCheck]:
    if not _has_auth_module(pkg):
        return [DoctorCheck("auth", "ok", "no auth module — public site, nothing to configure")]

    checks: list[DoctorCheck] = []
    if importlib.util.find_spec("playwright") is None:
        checks.append(
            DoctorCheck(
                "playwright",
                "warn",
                "not installed — `auth login` (browser flow) unavailable; "
                "pip install playwright && playwright install chromium",
            )
        )
    else:
        checks.append(DoctorCheck("playwright", "ok", "installed"))

    env_var = f"CLI_WEB_{app_name.upper().replace('-', '_')}_AUTH_JSON"
    if os.environ.get(env_var):
        checks.append(DoctorCheck("auth source", "ok", f"using env var {env_var}"))
        return checks

    auth_file = _config_dir(app_name) / "auth.json"
    if not auth_file.is_file():
        checks.append(
            DoctorCheck(
                "auth file",
                "warn",
                f"{auth_file} missing — run: cli-web-{app_name} auth login (or set {env_var})",
            )
        )
        return checks

    checks.append(DoctorCheck("auth file", "ok", str(auth_file)))
    if os.name == "posix":  # st_mode permission bits are meaningless on Windows
        mode = stat.S_IMODE(auth_file.stat().st_mode)
        if mode & 0o077:
            checks.append(
                DoctorCheck(
                    "auth file permissions",
                    "warn",
                    f"{oct(mode)} — should be 600; run: chmod 600 {auth_file}",
                )
            )
        else:
            checks.append(DoctorCheck("auth file permissions", "ok", oct(mode)))
    try:
        json.loads(auth_file.read_text(encoding="utf-8"))
        checks.append(DoctorCheck("auth file format", "ok", "valid JSON"))
    except (OSError, json.JSONDecodeError) as exc:
        checks.append(DoctorCheck("auth file format", "fail", f"unreadable: {exc}"))

    return checks


def _check_optional_deps() -> list[DoctorCheck]:
    checks = []
    if importlib.util.find_spec("prompt_toolkit") is None:
        checks.append(
            DoctorCheck("prompt_toolkit", "ok", "not installed — REPL uses plain input()")
        )
    else:
        checks.append(DoctorCheck("prompt_toolkit", "ok", "installed (REPL autocomplete on)"))
    return checks


def _check_browser_runtime(app_name: str) -> list[DoctorCheck]:
    """Verify browser payloads required by public browser-backed CLIs."""
    if app_name == "gai":
        if importlib.util.find_spec("playwright") is None:
            return [DoctorCheck("chromium browser", "fail", "playwright is not installed")]
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                executable = Path(playwright.chromium.executable_path)
            if executable.is_file():
                return [DoctorCheck("chromium browser", "ok", str(executable))]
            return [
                DoctorCheck(
                    "chromium browser",
                    "fail",
                    "payload missing — run: python -m playwright install chromium",
                )
            ]
        except Exception as exc:
            return [DoctorCheck("chromium browser", "fail", str(exc))]

    if app_name in {"unsplash", "futbin"}:
        if importlib.util.find_spec("camoufox") is None:
            return [DoctorCheck("camoufox browser", "fail", "camoufox is not installed")]
        try:
            from camoufox.pkgman import camoufox_path

            # Doctor is diagnostic and must never download a browser or write
            # to the cache as a side effect of checking the local setup.
            executable = Path(camoufox_path(download_if_missing=False))
            if executable.exists():
                return [DoctorCheck("camoufox browser", "ok", str(executable))]
            return [
                DoctorCheck(
                    "camoufox browser",
                    "fail",
                    "payload missing — run: python -m camoufox fetch",
                )
            ]
        except Exception as exc:
            return [DoctorCheck("camoufox browser", "fail", str(exc))]

    return []


def run_doctor(app_name: str, pkg: str) -> list[DoctorCheck]:
    checks = [
        _check_python(),
        _check_entry_point(app_name),
        _check_config_dir(app_name),
        *_check_auth(app_name, pkg),
        *_check_browser_runtime(app_name),
        *_check_optional_deps(),
    ]
    return checks


def register_doctor_command(cli: Any, app_name: str, pkg: str | None = None) -> None:
    """Attach a ``doctor`` command to a cli-web-* Click group."""
    import click

    resolved_pkg = pkg or app_name.replace("-", "_")

    @cli.command("doctor")
    @click.option("--json", "json_mode", is_flag=True, help="Output as JSON.")
    @click.pass_context
    def doctor(ctx: Any, json_mode: bool) -> None:
        """Diagnose this CLI's local setup (install, auth, dependencies)."""
        if not json_mode:  # honor the group-level --json flag (ctx.obj["json"])
            obj = ctx.find_root().obj
            json_mode = bool(obj.get("json")) if isinstance(obj, dict) else False
        checks = run_doctor(app_name, resolved_pkg)
        failed = [c for c in checks if c.status == "fail"]
        if json_mode:
            click.echo(
                json.dumps(
                    {
                        "success": not failed,
                        "data": {
                            "checks": [asdict(c) for c in checks],
                            "ok": not failed,
                        },
                    },
                    indent=2,
                )
            )
        else:
            marks = {"ok": "✓", "warn": "⚠", "fail": "✗"}
            for c in checks:
                detail = f"  {c.detail}" if c.detail else ""
                click.echo(f" {marks[c.status]} {c.name}:{detail}")
            click.echo()
            click.echo("all good" if not failed else f"{len(failed)} problem(s) found")
        if failed:
            raise SystemExit(1)
