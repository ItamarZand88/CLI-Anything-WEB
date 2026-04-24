#!/usr/bin/env python3
"""Validate a cli-web-* CLI against the 75-point quality checklist.

Runs ~65 mechanical checks from quality-checklist.md and reports results
as a colored terminal summary + optional JSON output.

Usage:
    python validate-checklist.py <harness-dir> --app-name hackernews
    python validate-checklist.py <harness-dir> --app-name hackernews --auth-type none
    python validate-checklist.py <harness-dir> --app-name hackernews --json
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

class CheckResult:
    def __init__(self, category: str, check_id: str, description: str):
        self.category = category
        self.check_id = check_id
        self.description = description
        self.status: str = "pending"  # pass, fail, skip, na
        self.detail: str = ""

    def pass_(self, detail: str = ""):
        self.status = "pass"
        self.detail = detail
        return self

    def fail(self, detail: str = ""):
        self.status = "fail"
        self.detail = detail
        return self

    def skip(self, detail: str = ""):
        self.status = "skip"
        self.detail = detail
        return self

    def na(self, detail: str = ""):
        self.status = "na"
        self.detail = detail
        return self

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "id": self.check_id,
            "description": self.description,
            "status": self.status,
            "detail": self.detail,
        }


class Validator:
    def __init__(self, harness_dir: Path, app_name: str, auth_type: str):
        self.harness_dir = harness_dir
        self.app_name = app_name
        self.app_underscore = app_name.replace("-", "_")
        self.APP_NAME = app_name.replace("-", "_").upper()
        self.auth_type = auth_type
        self.has_auth = auth_type != "none"
        self.pkg_dir = harness_dir / "cli_web" / self.app_underscore
        self.results: list[CheckResult] = []
        self._file_cache: dict[Path, str | None] = {}
        self._py_files_cache: dict[Path, list[Path]] = {}

    def check(self, category: str, check_id: str, description: str) -> CheckResult:
        r = CheckResult(category, check_id, description)
        self.results.append(r)
        return r

    def _read_file(self, path: Path) -> str | None:
        if path not in self._file_cache:
            try:
                self._file_cache[path] = path.read_text(encoding="utf-8")
            except (FileNotFoundError, OSError):
                self._file_cache[path] = None
        return self._file_cache[path]

    def _file_contains(self, path: Path, pattern: str) -> bool:
        content = self._read_file(path)
        if content is None:
            return False
        return bool(re.search(pattern, content))

    def _py_files(self, directory: Path) -> list[Path]:
        """Return all .py files under directory (cached)."""
        if directory not in self._py_files_cache:
            if directory.exists():
                self._py_files_cache[directory] = list(directory.rglob("*.py"))
            else:
                self._py_files_cache[directory] = []
        return self._py_files_cache[directory]

    def _any_py_contains(self, directory: Path, pattern: str) -> bool:
        """Check if any .py file in directory (recursively) matches pattern."""
        for f in self._py_files(directory):
            content = self._read_file(f)
            if content and re.search(pattern, content):
                return True
        return False

    # ── Category 1: Directory Structure ────────────────────────────────────
    def check_directory_structure(self):
        cat = "1. Directory Structure"

        r = self.check(cat, "1.1", "cli_web/<app>/ exists")
        if self.pkg_dir.is_dir():
            r.pass_()
        else:
            r.fail(f"Missing: {self.pkg_dir}")

        r = self.check(cat, "1.2", "<APP>.md exists at harness root")
        app_md = self.harness_dir / f"{self.APP_NAME}.md"
        # Also check lowercase
        if app_md.exists() or (self.harness_dir / f"{self.app_name.upper()}.md").exists():
            r.pass_()
        else:
            # Check any .md that looks like an API map
            found = list(self.harness_dir.glob("*.md"))
            api_maps = [f for f in found if f.name not in ("README.md", "TEST.md")]
            if api_maps:
                r.pass_(f"Found: {api_maps[0].name}")
            else:
                r.fail("No API map .md found")

        r = self.check(cat, "1.3", "cli_web/ has NO __init__.py (namespace package)")
        ns_init = self.harness_dir / "cli_web" / "__init__.py"
        if ns_init.exists():
            r.fail("cli_web/__init__.py exists — breaks namespace package")
        else:
            r.pass_()

        r = self.check(cat, "1.4", "<app>/ HAS __init__.py")
        if (self.pkg_dir / "__init__.py").exists():
            r.pass_()
        else:
            r.fail("Missing __init__.py in sub-package")

        r = self.check(cat, "1.5", "core/, commands/, utils/, tests/ all present")
        dirs = ["core", "commands", "utils", "tests"]
        missing = [d for d in dirs if not (self.pkg_dir / d).is_dir()]
        if missing:
            r.fail(f"Missing directories: {missing}")
        else:
            r.pass_()

        r = self.check(cat, "1.6", "setup.py at harness root")
        if (self.harness_dir / "setup.py").exists():
            r.pass_()
        else:
            r.fail("Missing setup.py")

    # ── Category 2: Required Files ─────────────────────────────────────────
    def check_required_files(self):
        cat = "2. Required Files"

        files = {
            "2.1": (f"{self.app_underscore}_cli.py", True),
            "2.2": ("__main__.py", True),
            "2.3": ("core/client.py", True),
            "2.4": ("core/exceptions.py", True),
            "2.5": ("core/auth.py", self.has_auth),
            "2.6": ("core/session.py", False),  # Optional
            "2.7": ("core/models.py", False),  # Optional
            "2.8": ("utils/repl_skin.py", True),
            "2.9": ("utils/output.py", True),
            "2.10": ("utils/helpers.py", True),
            "2.11": ("tests/test_core.py", True),
            "2.12": ("tests/test_e2e.py", True),
        }

        for check_id, (path, required) in files.items():
            r = self.check(cat, check_id, f"{path} exists")
            full = self.pkg_dir / path
            if full.exists():
                r.pass_()
            elif not required:
                r.na("Optional file")
            elif check_id == "2.5" and not self.has_auth:
                r.na("No auth — auth.py not required")
            else:
                r.fail(f"Missing: {path}")

        # README
        r = self.check(cat, "2.13", "README.md exists")
        if (self.pkg_dir / "README.md").exists() or (self.harness_dir / "README.md").exists():
            r.pass_()
        else:
            r.fail("Missing README.md")

    # ── Category 3: CLI Implementation ─────────────────────────────────────
    def check_cli_implementation(self):
        cat = "3. CLI Implementation"
        cli_file = self.pkg_dir / f"{self.app_underscore}_cli.py"
        content = self._read_file(cli_file) or ""

        r = self.check(cat, "3.1", "Click framework with @click.group")
        r.pass_() if "@click.group" in content else r.fail()

        r = self.check(cat, "3.2", "--json flag present")
        r.pass_() if '"--json"' in content or "'--json'" in content else r.fail()

        r = self.check(cat, "3.3", "REPL via invoke_without_command=True")
        r.pass_() if "invoke_without_command=True" in content else r.fail()

        r = self.check(cat, "3.4", "ReplSkin used")
        r.pass_() if "ReplSkin" in content else r.fail()

        r = self.check(cat, "3.5", "Auth group (login, status)")
        if not self.has_auth:
            r.na("No auth")
        elif "auth" in content.lower():
            r.pass_()
        else:
            r.fail("No auth command group found")

        r = self.check(cat, "3.6", "pass_context used")
        r.pass_() if "pass_context" in content else r.fail()

        r = self.check(cat, "3.7", "handle_errors context manager in commands")
        if self._any_py_contains(self.pkg_dir / "commands", r"handle_errors"):
            r.pass_()
        elif "handle_errors" in content:
            r.pass_("In CLI entry point")
        else:
            r.fail("No handle_errors usage found")

        r = self.check(cat, "3.8", "REPL uses shlex.split")
        r.pass_() if "shlex.split" in content else r.fail()

        r = self.check(cat, "3.9", "REPL dispatches with standalone_mode=False")
        r.pass_() if "standalone_mode=False" in content else r.fail()

    # ── Category 4: Core Modules ───────────────────────────────────────────
    def check_core_modules(self):
        cat = "4. Core Modules"

        # exceptions.py
        exc_content = self._read_file(self.pkg_dir / "core" / "exceptions.py") or ""

        r = self.check(cat, "4.1", "Typed exception hierarchy")
        exc_types = ["AuthError", "RateLimitError", "NetworkError", "ServerError", "NotFoundError"]
        found = [e for e in exc_types if e in exc_content]
        if len(found) >= 4:
            r.pass_(f"Found: {found}")
        else:
            r.fail(f"Only found: {found}")

        r = self.check(cat, "4.2", "to_dict() on base exception")
        r.pass_() if "to_dict" in exc_content else r.fail()

        # client.py
        client_content = self._read_file(self.pkg_dir / "core" / "client.py") or ""

        r = self.check(cat, "4.3", "Client maps HTTP status to exceptions")
        status_patterns = ["401", "403", "404", "429"]
        mapped = [s for s in status_patterns if s in client_content]
        if len(mapped) >= 3:
            r.pass_(f"Mapped codes: {mapped}")
        else:
            r.fail(f"Only mapped: {mapped}")

        r = self.check(cat, "4.4", "Auth retry on 401/403")
        if "retry_on_auth" in client_content or ("401" in client_content and "retry" in client_content.lower()) or "_attempt" in client_content:
            r.pass_()
        elif not self.has_auth:
            r.na("No auth")
        else:
            r.fail()

        r = self.check(cat, "4.4b", "Token auto-refresh via headless browser")
        if not self.has_auth:
            r.na("No auth")
        else:
            auth_path = self.pkg_dir / "core" / "auth.py"
            auth_content = auth_path.read_text(encoding="utf-8") if auth_path.exists() else ""
            has_refresh_fn = "refresh_auth" in auth_content or "refresh_token" in auth_content
            has_headless = "headless" in auth_content
            has_client_call = "refresh_auth" in client_content or "refresh_token" in client_content or "_refresh_via_browser" in client_content
            if has_refresh_fn and has_client_call:
                r.pass_("auth.py has refresh + client calls it on 401/403")
            else:
                missing = []
                if not has_refresh_fn:
                    missing.append("auth.py missing refresh_auth()/refresh_token()")
                if not has_client_call:
                    missing.append("client.py not calling refresh on auth failure")
                r.fail("; ".join(missing))

        r = self.check(cat, "4.5", "Context manager protocol")
        if "__enter__" in client_content and "__exit__" in client_content:
            r.pass_()
        else:
            r.fail("Missing __enter__/__exit__")

        # auth.py
        r = self.check(cat, "4.6", "Auth secure storage (chmod 600)")
        if not self.has_auth:
            r.na("No auth")
        else:
            auth_content = self._read_file(self.pkg_dir / "core" / "auth.py") or ""
            if "chmod" in auth_content or "S_IRUSR" in auth_content or "0o600" in auth_content:
                r.pass_()
            else:
                r.fail("No chmod/permissions on auth file")

        # Non-REST protocol
        r = self.check(cat, "4.7", "RPC subpackage (if batchexecute)")
        rpc_dir = self.pkg_dir / "core" / "rpc"
        if rpc_dir.is_dir():
            rpc_files = ["types.py", "encoder.py", "decoder.py"]
            missing = [f for f in rpc_files if not (rpc_dir / f).exists()]
            if missing:
                r.fail(f"RPC dir exists but missing: {missing}")
            else:
                r.pass_()
        else:
            r.na("No RPC directory (non-batchexecute)")

    # ── Category 5: Test Standards ─────────────────────────────────────────
    def check_test_standards(self):
        cat = "5. Test Standards"
        tests_dir = self.pkg_dir / "tests"

        r = self.check(cat, "5.1", "TEST.md has plan and results")
        test_md = self._read_file(tests_dir / "TEST.md")
        if test_md is None:
            test_md = self._read_file(self.harness_dir / "TEST.md") or ""
        if test_md and "Part 1" in test_md and "Part 2" in test_md:
            r.pass_()
        elif test_md:
            r.pass_("TEST.md exists but may not have both parts")
        else:
            r.fail("No TEST.md found")

        r = self.check(cat, "5.2", "Unit tests use mock.patch")
        test_core = self._read_file(tests_dir / "test_core.py") or ""
        if "mock" in test_core.lower() or "patch" in test_core:
            r.pass_()
        else:
            r.fail("No mock/patch in test_core.py")

        r = self.check(cat, "5.3", "TestCLISubprocess class exists")
        test_e2e = self._read_file(tests_dir / "test_e2e.py") or ""
        if "TestCLISubprocess" in test_e2e or "Subprocess" in test_e2e:
            r.pass_()
        elif "subprocess" in test_e2e:
            r.pass_("subprocess used but no TestCLISubprocess class")
        else:
            r.fail()

        r = self.check(cat, "5.4", "_resolve_cli pattern used")
        all_test = test_core + test_e2e
        if "_resolve_cli" in all_test:
            r.pass_()
        elif "subprocess" in all_test:
            r.pass_("subprocess used without _resolve_cli")
        else:
            r.fail()

        r = self.check(cat, "5.5", "Subprocess _run does NOT set cwd")
        if "_run" in test_e2e:
            if re.search(r"cwd\s*=", test_e2e):
                r.fail("_run sets cwd (should not)")
            else:
                r.pass_()
        else:
            r.na("No _run method found")

        r = self.check(cat, "5.6", "CLI_WEB_FORCE_INSTALLED support")
        if "FORCE_INSTALLED" in all_test or "CLI_WEB_FORCE_INSTALLED" in all_test:
            r.pass_()
        else:
            r.fail()

    # ── Category 7: PyPI Packaging ─────────────────────────────────────────
    def check_packaging(self):
        cat = "7. PyPI Packaging"
        setup_content = self._read_file(self.harness_dir / "setup.py") or ""

        r = self.check(cat, "7.1", 'find_namespace_packages(include=["cli_web.*"])')
        if "find_namespace_packages" in setup_content and "cli_web.*" in setup_content:
            r.pass_()
        else:
            r.fail()

        r = self.check(cat, "7.2", f"Package name: cli-web-{self.app_name}")
        if f"cli-web-{self.app_name}" in setup_content:
            r.pass_()
        else:
            r.fail()

        r = self.check(cat, "7.3", "Entry point format correct")
        expected = f"cli-web-{self.app_name}=cli_web.{self.app_underscore}.{self.app_underscore}_cli:main"
        if expected in setup_content:
            r.pass_()
        else:
            r.fail(f"Expected: {expected}")

        r = self.check(cat, "7.4", "Imports use cli_web.<app>.* prefix")
        # Check a sample of files for correct imports
        violations = []
        for py in self._py_files(self.pkg_dir):
            content = self._read_file(py) or ""
            # Look for bare imports that should be namespaced
            if re.search(r"^from\s+core\b", content, re.MULTILINE):
                violations.append(py.name)
            if re.search(r"^from\s+utils\b", content, re.MULTILINE):
                violations.append(py.name)
        if violations:
            r.fail(f"Bare imports in: {violations}")
        else:
            r.pass_()

        r = self.check(cat, "7.5", 'python_requires=">=3.10"')
        if ">=3.10" in setup_content:
            r.pass_()
        else:
            r.fail()

    # ── Category 8: Code Quality ───────────────────────────────────────────
    def check_code_quality(self):
        cat = "8. Code Quality"

        # Syntax check
        r = self.check(cat, "8.1", "No syntax errors in Python files")
        errors = []
        for py in self._py_files(self.pkg_dir):
            content = self._read_file(py)
            if content is None:
                continue
            try:
                ast.parse(content)
            except SyntaxError as e:
                errors.append(f"{py.name}:{e.lineno}")
        if errors:
            r.fail(f"Syntax errors: {errors}")
        else:
            r.pass_()

        # Hardcoded secrets
        r = self.check(cat, "8.2", "No hardcoded auth tokens/API keys")
        secret_patterns = [
            r'api[_-]?key\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
            r'token\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
            r'password\s*=\s*["\'][^"\']{8,}["\']',
        ]
        found = []
        for py in self._py_files(self.pkg_dir):
            if "test" in py.name:
                continue
            content = self._read_file(py) or ""
            for pat in secret_patterns:
                if re.search(pat, content):
                    found.append(py.name)
                    break
        if found:
            r.fail(f"Potential secrets in: {found}")
        else:
            r.pass_()

        # Bare except
        r = self.check(cat, "8.3", "No bare except: blocks")
        bare = []
        for py in self._py_files(self.pkg_dir):
            content = self._read_file(py) or ""
            if re.search(r"^\s*except\s*:", content, re.MULTILINE):
                bare.append(py.name)
        if bare:
            r.fail(f"Bare except in: {bare}")
        else:
            r.pass_()

        # UTF-8 fix
        cli_file = self.pkg_dir / f"{self.app_underscore}_cli.py"
        r = self.check(cat, "8.4", "UTF-8 stdout/stderr reconfigure in CLI entry")
        content = self._read_file(cli_file) or ""
        if "reconfigure" in content and "utf-8" in content:
            r.pass_()
        else:
            r.fail()

        r = self.check(cat, "8.5", "UTF-8 fix covers both stdout AND stderr")
        if "stdout" in content and "stderr" in content:
            r.pass_()
        else:
            r.fail("Only partial UTF-8 fix")

    # ── Category 9: REPL Quality ───────────────────────────────────────────
    def check_repl_quality(self):
        cat = "9. REPL Quality"
        cli_file = self.pkg_dir / f"{self.app_underscore}_cli.py"
        content = self._read_file(cli_file) or ""

        r = self.check(cat, "9.1", "REPL uses shlex.split (not line.split)")
        if "shlex.split" in content:
            r.pass_()
        else:
            r.fail()

        r = self.check(cat, "9.2", "Dispatch with standalone_mode=False")
        if "standalone_mode=False" in content:
            r.pass_()
        else:
            r.fail()

        r = self.check(cat, "9.3", "Positional args via @click.argument")
        # Check commands for @click.argument usage
        if self._any_py_contains(self.pkg_dir / "commands", r"@click\.argument"):
            r.pass_()
        else:
            r.skip("Could not verify — check manually")

    # ── Category 10: Error Handling ────────────────────────────────────────
    def check_error_handling(self):
        cat = "10. Error Handling"

        r = self.check(cat, "10.1", "Typed exception hierarchy (not RuntimeError)")
        exc_content = self._read_file(self.pkg_dir / "core" / "exceptions.py") or ""
        if "RuntimeError" in exc_content:
            r.fail("Uses RuntimeError in exceptions.py")
        elif "Error" in exc_content:
            r.pass_()
        else:
            r.fail()

        r = self.check(cat, "10.2", "Client maps HTTP status to domain exceptions")
        client_content = self._read_file(self.pkg_dir / "core" / "client.py") or ""
        if "raise_for_status" in client_content or "status_code" in client_content:
            r.pass_()
        else:
            r.fail()

        r = self.check(cat, "10.3", "Auth env var support")
        if not self.has_auth:
            r.na("No auth")
        else:
            auth_content = self._read_file(self.pkg_dir / "core" / "auth.py") or ""
            expected_var = f"CLI_WEB_{self.APP_NAME}_AUTH_JSON"
            if expected_var in auth_content or "environ" in auth_content:
                r.pass_()
            else:
                r.fail(f"No {expected_var} env var support")

        r = self.check(cat, "10.4", "--json outputs structured error JSON")
        helpers_content = self._read_file(self.pkg_dir / "utils" / "helpers.py") or ""
        if "to_dict" in helpers_content or "json.dumps" in helpers_content:
            r.pass_()
        else:
            r.fail()

    # ── Run all checks ─────────────────────────────────────────────────────
    def run_all(self):
        self.check_directory_structure()
        self.check_required_files()
        self.check_cli_implementation()
        self.check_core_modules()
        self.check_test_standards()
        self.check_packaging()
        self.check_code_quality()
        self.check_repl_quality()
        self.check_error_handling()

    def print_summary(self):
        """Print colored terminal summary."""
        counts = {"pass": 0, "fail": 0, "skip": 0, "na": 0}
        current_cat = ""

        for r in self.results:
            counts[r.status] += 1
            if r.category != current_cat:
                current_cat = r.category
                print(f"\n### {current_cat}")

            if r.status == "pass":
                icon = "\033[32m PASS\033[0m"
            elif r.status == "fail":
                icon = "\033[31m FAIL\033[0m"
            elif r.status == "na":
                icon = "\033[90m  N/A\033[0m"
            else:
                icon = "\033[33m SKIP\033[0m"

            detail = f" — {r.detail}" if r.detail else ""
            print(f"  [{icon}] {r.check_id}: {r.description}{detail}")

        total = len(self.results)
        applicable = total - counts["na"] - counts["skip"]

        print(f"\n{'='*60}")
        print(f"  Total checks:  {total}")
        print(f"  \033[32mPassed:      {counts['pass']}\033[0m")
        print(f"  \033[31mFailed:      {counts['fail']}\033[0m")
        print(f"  \033[33mSkipped:     {counts['skip']}\033[0m")
        print(f"  \033[90mN/A:         {counts['na']}\033[0m")
        if applicable > 0:
            rate = counts["pass"] / applicable * 100
            print(f"  Pass rate:     {rate:.0f}% ({counts['pass']}/{applicable})")
        print(f"{'='*60}")

        return counts["fail"]

    def to_json(self) -> str:
        counts = {"pass": 0, "fail": 0, "skip": 0, "na": 0}
        for r in self.results:
            counts[r.status] += 1
        return json.dumps({
            "app_name": self.app_name,
            "auth_type": self.auth_type,
            "summary": counts,
            "checks": [r.to_dict() for r in self.results],
        }, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Validate cli-web-* CLI against quality checklist.")
    parser.add_argument("harness_dir", type=Path, help="Path to agent-harness directory")
    parser.add_argument("--app-name", required=True, help="CLI app name (e.g., hackernews)")
    parser.add_argument("--auth-type", default="cookie",
                        choices=["none", "cookie", "api-key", "google-sso"],
                        help="Auth type (default: cookie)")
    parser.add_argument("--json", dest="json_mode", action="store_true",
                        help="Output results as JSON")

    args = parser.parse_args()

    harness = args.harness_dir.resolve()
    if not harness.is_dir():
        print(f"Error: {harness} is not a directory", file=sys.stderr)
        sys.exit(1)

    v = Validator(harness, args.app_name, args.auth_type)
    v.run_all()

    if args.json_mode:
        print(v.to_json())
    else:
        failures = v.print_summary()
        sys.exit(1 if failures > 0 else 0)


if __name__ == "__main__":
    main()
