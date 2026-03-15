---
name: web-harness:test
description: Run tests for a web-harness CLI and update TEST.md with results.
argument-hint: <app-path>
allowed-tools: Bash(*), Read, Write, Edit
---

## CRITICAL: Read CLI-ANYTHING-WEB.md First

**Before running tests, read `${CLAUDE_PLUGIN_ROOT}/CLI-ANYTHING-WEB.md`.** It defines the test standards, expected structure, and what constitutes a passing test suite.

# Web-Harness: Test Runner

Read the methodology SOP:
@${CLAUDE_PLUGIN_ROOT}/CLI-ANYTHING-WEB.md

Target: $ARGUMENTS

## Process

1. Locate test directory: `<app>/agent-harness/cli_web/<app>/tests/`
2. Run full test suite:
   ```
   cd <app>/agent-harness
   python3 -m pytest cli_web/<app>/tests/ -v --tb=short 2>&1
   ```
3. If installed, also run subprocess tests:
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

## TEST.md Format

```markdown
# Test Results — cli-web-<app>

## Summary
- **Total**: X tests
- **Passed**: X ✅
- **Failed**: X ❌
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
