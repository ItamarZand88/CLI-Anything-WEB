---
name: web-harness:validate
description: Validate a web-harness CLI against WEB-HARNESS.md standards and best practices.
argument-hint: <app-path>
allowed-tools: Bash(*), Read, Write, Edit
---

## CRITICAL: Read WEB-HARNESS.md First

**Before validating, read `${CLAUDE_PLUGIN_ROOT}/WEB-HARNESS.md`.** It is the single source of truth for all validation checks below. Every check in this command maps to a requirement in WEB-HARNESS.md.

# Web-Harness: Validate Standards

Read the methodology SOP:
@${CLAUDE_PLUGIN_ROOT}/WEB-HARNESS.md

Target: $ARGUMENTS

## Validation Checklist

### Structure
- [ ] `<app>/agent-harness/` directory exists
- [ ] `<APP>.md` SOP document exists
- [ ] `setup.py` with proper namespace config
- [ ] `cli_web/` namespace package (NO `__init__.py`)
- [ ] `cli_web/<app>/` sub-package (HAS `__init__.py`)
- [ ] `__main__.py` for `python -m` support

### Core Modules
- [ ] `client.py` — centralized HTTP client
- [ ] `auth.py` — authentication management
- [ ] `session.py` — state and undo/redo
- [ ] `<app>_cli.py` — main entry point

### CLI Standards
- [ ] `--json` flag on every command
- [ ] `--help` on every command and subcommand
- [ ] REPL mode when run without arguments
- [ ] `repl_skin.py` present for consistent REPL
- [ ] Branded banner in REPL

### Auth
- [ ] `auth login` command
- [ ] `auth status` command
- [ ] Token stored securely (not in code)
- [ ] Token refresh if applicable
- [ ] Graceful auth failure messages

### Tests
- [ ] `tests/` directory with `TEST.md`
- [ ] Unit tests with mocked HTTP
- [ ] E2E tests with fixtures
- [ ] CLI subprocess tests
- [ ] Tests FAIL (not skip) on missing auth

### Output
- [ ] JSON output parseable by agents
- [ ] Human-readable tables for interactive use
- [ ] Error messages include actionable guidance

### Installability
- [ ] `pip install -e .` works
- [ ] `which cli-web-<app>` finds the command
- [ ] `cli-web-<app> --help` shows all commands
- [ ] `cli-web-<app> --json` mode works

## Report

Report each check as PASS ✅ or FAIL ❌ with details on failures.
