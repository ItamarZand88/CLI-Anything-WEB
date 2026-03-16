---
name: cli-anything-web:validate
description: Validate a cli-anything-web CLI against HARNESS.md standards and best practices. Reports 8-category N/N check results.
argument-hint: <app-path>
allowed-tools: Bash(*), Read, Write, Edit
---

## CRITICAL: Read HARNESS.md First

**Before validating, read `${CLAUDE_PLUGIN_ROOT}/HARNESS.md`.** It is the single source of truth for all validation checks below. Every check in this command maps to a requirement in HARNESS.md.

# CLI-Anything-Web: Validate Standards

Read the methodology SOP:
@${CLAUDE_PLUGIN_ROOT}/HARNESS.md

Target: $ARGUMENTS

## Process

1. Parse the target path to extract `<app>` name
2. Resolve the `agent-harness/` root and `cli_web/<app>/` package path
3. Run all 8 categories of checks below
4. Print the report in the format shown at the bottom
5. Exit with summary: PASS if all 50 checks pass, FAIL otherwise

## Prerequisites

- [ ] `npx @playwright/cli@latest --version` succeeds (playwright-cli available)

## Category 1: Directory Structure (6 checks)

*(checked against `agent-harness/` root)*

- [ ] `agent-harness/cli_web/<app>/` exists
- [ ] `agent-harness/<APP>.md` exists (software-specific SOP at harness root)
- [ ] `cli_web/` has NO `__init__.py` (namespace package)
- [ ] `<app>/` HAS `__init__.py`
- [ ] `core/`, `commands/`, `utils/`, `tests/` all present inside `cli_web/<app>/` (one atomic check)
- [ ] `setup.py` at `agent-harness/` root

## Category 2: Required Files (13 checks)

*(checked against `cli_web/<app>/`)*

- [ ] `README.md`
- [ ] `<app>_cli.py`
- [ ] `__main__.py`
- [ ] `core/client.py`
- [ ] `core/auth.py`
- [ ] `core/session.py`
- [ ] `core/models.py`
- [ ] `utils/repl_skin.py`
- [ ] `utils/output.py`
- [ ] `utils/config.py`
- [ ] `tests/TEST.md`
- [ ] `tests/test_core.py`
- [ ] `tests/test_e2e.py`

## Category 3: CLI Implementation Standards (6 checks)

- [ ] Uses Click framework with command groups (grep for `@click.group`)
- [ ] `--json` flag on every command (grep for `--json`)
- [ ] REPL mode — grep `<app>_cli.py` for `invoke_without_command=True`
- [ ] `repl_skin.py` used for banner, prompt, messages (grep for `ReplSkin`)
- [ ] `auth` command group with `login`, `status`, `refresh` subcommands
- [ ] Global session state (`pass_context=True` or module-level session object)

## Category 4: Core Module Standards (4 checks)

- [ ] `client.py`: has centralized auth header injection, exponential backoff, JSON parsing
- [ ] `auth.py`: has login, refresh, expiry check, secure storage
- [ ] `session.py`: has Session class with undo/redo stack
- [ ] `models.py`: has typed response models

## Category 5: Test Standards (8 checks)

- [ ] `TEST.md` has both plan (Part 1) and results (Part 2)
- [ ] Unit tests use `unittest.mock.patch` for HTTP — no real network calls
- [ ] E2E fixture tests replay captured responses from `tests/fixtures/`
- [ ] E2E live tests require auth — FAIL (not skip) without it
- [ ] `test_e2e.py` has `TestCLISubprocess` class
- [ ] Uses `_resolve_cli("cli-web-<app>")` — no hardcoded paths
- [ ] Subprocess `_run` does NOT set `cwd`
- [ ] Supports `CLI_WEB_FORCE_INSTALLED=1`

## Category 6: Documentation Standards (3 checks)

- [ ] `README.md`: has installation, auth setup, command reference, examples
- [ ] `<APP>.md`: has API map, data model, auth scheme, endpoint inventory
- [ ] No `HARNESS.md` inside app package (it lives in plugin root)

## Category 7: PyPI Packaging Standards (5 checks)

- [ ] `find_namespace_packages(include=["cli_web.*"])` in setup.py
- [ ] Package name: `cli-web-<app>`
- [ ] Entry point: `cli-web-<app>=cli_web.<app>.<app>_cli:main`
- [ ] All imports use `cli_web.<app>.*` prefix
- [ ] `python_requires=">=3.10"`

## Category 8: Code Quality (5 checks)

- [ ] No syntax errors, no import errors (`python3 -c "import cli_web.<app>"`)
- [ ] No hardcoded auth tokens or API keys in source
- [ ] No hardcoded API base URLs or credential values in source
- [ ] No bare `except:` blocks
- [ ] Error messages include actionable guidance

## Report Format

Print results in this exact format:

```
CLI-Anything-Web Validation Report
App: <app>
Path: <path>/agent-harness/cli_web/<app>

Directory Structure  (X/6 checks passed)
Required Files       (X/13 files present)
CLI Standards        (X/6 standards met)
Core Modules         (X/4 standards met)
Test Standards       (X/8 standards met)
Documentation        (X/3 standards met)
PyPI Packaging       (X/5 standards met)
Code Quality         (X/5 checks passed)

Overall: PASS|FAIL (X/50 checks)
```

For each FAIL, print a detail line below the category:
```
  FAIL: <check description> — <actionable fix suggestion>
```
