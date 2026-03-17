---
name: cli-anything-web:test
description: Run tests for a cli-anything-web CLI and update TEST.md with results.
argument-hint: <app-path>
allowed-tools: Bash(*), Read, Write, Edit
---

# CLI-Anything-Web: Test Runner

> **Skills used:** `testing` (Phases 5-7)

Read the methodology overview:
@${CLAUDE_PLUGIN_ROOT}/HARNESS.md

Target: $ARGUMENTS

## Process

This command invokes the `testing` skill for Phases 5-7.

1. **Verify auth is working FIRST** — this is mandatory before any E2E test:
   ```
   cli-web-<app> auth login              # playwright-cli (recommended)
   cli-web-<app> auth login --cookies-json <file>  # manual fallback
   cli-web-<app> auth status
   ```
   Auth status MUST show live validation succeeded. If it fails:
   - Ensure playwright-cli is available (`npx @playwright/cli@latest --version`)
   - Fix auth before running any tests
   - Do NOT proceed with "auth not configured" — that is a broken test

2. Locate test directory: `<app>/agent-harness/cli_web/<app>/tests/`
3. Run full test suite:
   ```
   cd <app>/agent-harness
   python3 -m pytest cli_web/<app>/tests/ -v --tb=short 2>&1
   ```
4. If installed, also run subprocess tests:
   ```
   CLI_WEB_FORCE_INSTALLED=1 python3 -m pytest cli_web/<app>/tests/ -v -s -k subprocess 2>&1
   ```
   After running, verify the subprocess backend was used:
   - Check output for `[_resolve_cli] Using installed command:` — this confirms
     the installed package is being tested, not the source fallback
   - If this line is absent, the installed CLI was not found in PATH
4. Parse test output: count passed, failed, skipped, errors
5. Update `TEST.md` with results in standard format
6. If failures exist, analyze and suggest fixes

See the `testing` skill for detailed testing patterns and the
`standards` skill for quality checks.

## TEST.md Format

```markdown
# Test Results — cli-web-<app>

## Summary
- **Total**: X tests
- **Passed**: X
- **Failed**: X
- **Date**: YYYY-MM-DD

## Unit Tests (test_core.py)
<list of test results>

## E2E Tests (test_e2e.py)
<list of test results>

## CLI Subprocess Tests
<list of test results>
```

## Failure Handling

If any tests fail:
1. **Show the failures** — print the full pytest output with failure details
2. **Do NOT update TEST.md** — TEST.md should only contain passing results
3. **Analyze and suggest fixes** — provide specific guidance for each failure
4. **Offer to re-run** — ask the user if they want to fix and re-test

## End-User Smoke Test

After all pytest tests pass, run a manual smoke test as an end user would:

```bash
# 1. Auth (must work standalone)
cli-web-<app> auth login

# 2. Status (must show valid)
cli-web-<app> auth status

# 3. READ test (must return real data)
cli-web-<app> --json <first-resource> list

# 4. WRITE test (must succeed — THIS IS THE MOST IMPORTANT STEP)
# For CRUD apps:
cli-web-<app> --json <resource> create --name "smoke-test"
# For generation apps:
cli-web-<app> --json <resource> generate --prompt "test" --wait
```

**Step 4 is critical.** If you only test reads and skip writes, the CLI may appear
to work but fail when users try to create/generate anything. This is the #1 gap —
the agent declares "done" after a successful `list` without ever testing `create`.

If any of these fail, the tests are NOT truly passing — fix before declaring done.
