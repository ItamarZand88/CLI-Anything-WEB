#!/usr/bin/env python3
"""Smoke test a cli-web-* CLI after implementation.

Validates that the CLI binary works, responds to --help and --version,
and that --json output is valid JSON without protocol leaks.

Usage:
    python smoke-test.py cli-web-hackernews
    python smoke-test.py cli-web-hackernews --auth-type none
    python smoke-test.py cli-web-hackernews --auth-type cookie --skip-auth
    python smoke-test.py cli-web-hackernews --json
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys


# Protocol leak patterns (from standards/SKILL.md)
LEAK_PATTERNS = [
    (r'"wrb\.fr"', "Google batchexecute protocol leak (wrb.fr)"),
    (r'"af\.httprm"', "Google batchexecute protocol leak (af.httprm)"),
    (r'\[\s*\[\s*\[\s*"wrb', "Raw batchexecute array structure"),
    (r'"SNlM0e"', "CSRF token leak in output"),
    (r'"FdrFJe"', "Session ID leak in output"),
]


def run_cli(cli_cmd: list[str], args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run CLI with args, return (exit_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            cli_cmd + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except FileNotFoundError:
        return -2, "", "CLI binary not found"


def check_json_valid(output: str) -> tuple[bool, str]:
    """Check if output is valid JSON."""
    output = output.strip()
    if not output:
        return False, "Empty output"
    try:
        json.loads(output)
        return True, ""
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"


def check_leaks(output: str) -> list[str]:
    """Check for protocol leak patterns in output."""
    found = []
    for pattern, description in LEAK_PATTERNS:
        if re.search(pattern, output):
            found.append(description)
    return found


class SmokeTest:
    def __init__(self, cli_name: str, auth_type: str, skip_auth: bool):
        self.cli_name = cli_name
        self.auth_type = auth_type
        self.skip_auth = skip_auth
        self.has_auth = auth_type != "none" and not skip_auth
        self.results: list[dict] = []
        self.cli_cmd: list[str] = []

    def _record(self, name: str, passed: bool, detail: str = ""):
        self.results.append({
            "name": name,
            "status": "pass" if passed else "fail",
            "detail": detail,
        })

    def resolve_cli(self) -> bool:
        """Find the CLI binary."""
        path = shutil.which(self.cli_name)
        if path:
            self.cli_cmd = [path]
            self._record("CLI binary found", True, path)
            return True

        # Try python -m
        module = self.cli_name.replace("cli-web-", "cli_web.").replace("-", "_")
        module += "." + self.cli_name.split("-")[-1].replace("-", "_") + "_cli"
        test_code, _, _ = run_cli([sys.executable, "-m", module], ["--help"])
        if test_code == 0:
            self.cli_cmd = [sys.executable, "-m", module]
            self._record("CLI binary found", True, f"python -m {module}")
            return True

        self._record("CLI binary found", False, f"{self.cli_name} not in PATH and python -m failed")
        return False

    @staticmethod
    def _parse_commands_from_help(help_output: str) -> list[str]:
        """Extract subcommand names from Click --help output."""
        commands = []
        in_commands = False
        for line in help_output.splitlines():
            if re.match(r"^\s*Commands:", line, re.IGNORECASE):
                in_commands = True
                continue
            if in_commands:
                m = re.match(r"^\s+(\w[\w-]*)", line)
                if m:
                    commands.append(m.group(1))
                elif line.strip() == "":
                    break
        return commands

    def check_help(self):
        """Check --help works."""
        code, out, err = run_cli(self.cli_cmd, ["--help"])
        passed = code == 0 and len(out) > 10
        self._record("--help responds", passed, f"exit={code}, output={len(out)} chars")
        self._help_output = out if passed else ""

    def check_version(self):
        """Check --version works."""
        code, out, err = run_cli(self.cli_cmd, ["--version"])
        passed = code == 0 and out.strip()
        self._record("--version responds", passed, out.strip() if passed else f"exit={code}")

    def check_auth_status(self):
        """Check auth status command (if applicable)."""
        if not self.has_auth:
            self.results.append({"name": "Auth status", "status": "skip", "detail": "No auth"})
            return

        code, out, err = run_cli(self.cli_cmd, ["auth", "status", "--json"])
        if code in (0, 1):  # 0=logged in, 1=not logged in (both valid)
            valid, msg = check_json_valid(out)
            if valid:
                self._record("Auth status --json", True)
            else:
                self._record("Auth status --json", False, msg)
        else:
            self._record("Auth status --json", False, f"exit={code}, stderr={err[:200]}")

    def discover_commands(self) -> list[str]:
        """Discover available subcommands from cached --help output."""
        return self._parse_commands_from_help(getattr(self, "_help_output", ""))

    def check_command_json(self, cmd: str):
        """Check that a command with --json returns valid JSON."""
        # Try the command with --help first to discover subcommands
        code, help_out, _ = run_cli(self.cli_cmd, [cmd, "--help"])
        if code != 0:
            self._record(f"{cmd} --json", False, f"--help failed (exit={code})")
            return

        # Check if this is a group with subcommands
        subcmds = self._parse_commands_from_help(help_out)

        if subcmds:
            # Test first subcommand
            subcmd = subcmds[0]
            code, out, err = run_cli(self.cli_cmd, [cmd, subcmd, "--json"], timeout=15)
        else:
            code, out, err = run_cli(self.cli_cmd, [cmd, "--json"], timeout=15)

        if code == -1:
            self._record(f"{cmd} --json", False, "Timeout (15s)")
            return

        if not out.strip():
            self._record(f"{cmd} --json", False, "Empty output")
            return

        valid, msg = check_json_valid(out)
        if not valid:
            # Some commands may output tables without --json producing JSON
            self._record(f"{cmd} --json", False, msg)
            return

        # Check for leaks
        leaks = check_leaks(out)
        if leaks:
            self._record(f"{cmd} --json", False, f"Protocol leaks: {leaks}")
        else:
            self._record(f"{cmd} --json", True)

    def run_all(self):
        """Run all smoke tests."""
        if not self.resolve_cli():
            return

        self.check_help()
        self.check_version()
        self.check_auth_status()

        # Discover and test commands
        commands = self.discover_commands()
        # Skip 'auth' (tested separately) and limit to first 5
        test_cmds = [c for c in commands if c != "auth"][:5]
        for cmd in test_cmds:
            self.check_command_json(cmd)

    def print_summary(self) -> int:
        """Print colored summary. Returns number of failures."""
        print(f"\nSmoke Test: {self.cli_name}")
        print(f"{'='*50}")

        failures = 0
        for r in self.results:
            if r["status"] == "pass":
                icon = "\033[32m PASS\033[0m"
            elif r["status"] == "fail":
                icon = "\033[31m FAIL\033[0m"
                failures += 1
            else:
                icon = "\033[33m SKIP\033[0m"

            detail = f" — {r['detail']}" if r["detail"] else ""
            print(f"  [{icon}] {r['name']}{detail}")

        total = len(self.results)
        skipped = sum(1 for r in self.results if r["status"] == "skip")
        applicable = total - skipped
        passed = sum(1 for r in self.results if r["status"] == "pass")

        print(f"\n  {passed}/{applicable} passed", end="")
        if skipped:
            print(f" ({skipped} skipped)", end="")
        print()
        return failures

    def to_json(self) -> str:
        passed = sum(1 for r in self.results if r["status"] == "pass")
        failed = sum(1 for r in self.results if r["status"] == "fail")
        return json.dumps({
            "cli_name": self.cli_name,
            "passed": passed,
            "failed": failed,
            "results": self.results,
        }, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Smoke test a cli-web-* CLI.")
    parser.add_argument("cli_name", help="CLI command name (e.g., cli-web-hackernews)")
    parser.add_argument("--auth-type", default="cookie",
                        choices=["none", "cookie", "api-key", "google-sso"])
    parser.add_argument("--skip-auth", action="store_true",
                        help="Skip auth-related checks")
    parser.add_argument("--json", dest="json_mode", action="store_true",
                        help="Output as JSON")

    args = parser.parse_args()

    st = SmokeTest(args.cli_name, args.auth_type, args.skip_auth)
    st.run_all()

    if args.json_mode:
        print(st.to_json())
    else:
        failures = st.print_summary()
        sys.exit(1 if failures > 0 else 0)


if __name__ == "__main__":
    main()
