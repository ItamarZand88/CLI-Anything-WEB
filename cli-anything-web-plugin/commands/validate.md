---
name: cli-anything-web:validate
description: Validate a cli-anything-web CLI against the tiered quality checklist (Tier 1 critical / Tier 2 comprehensive). Reports per-category and per-tier results.
argument-hint: <app-path>
allowed-tools: Bash(*), Read, Write, Edit
---

## CRITICAL: Read the Conventions First

**Before validating, read `${CLAUDE_PLUGIN_ROOT}/skills/shared/CONVENTIONS.md`.** It is the single source of truth for every rule the checklist enforces (HARNESS.md is the navigational overview that indexes it).

# CLI-Anything-Web: Validate Standards

Read the methodology overview:
@${CLAUDE_PLUGIN_ROOT}/HARNESS.md

Target: $ARGUMENTS

## Process

> **Skills used:** `standards` (tiered checklist validation)

1. Parse the target path to extract `<app>` name
2. Resolve the `agent-harness/` root and `cli_web/<app>/` package path
3. **Tier 1 fail-fast first** — critical checks must all pass before anything else:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/validate-checklist.py \
     <app>/agent-harness --app-name <app> --auth-type <auth-type> --tier1-only
   ```
   Non-zero exit = Tier 1 failures. Fix them and re-run before continuing.
4. **Full checklist run** (both tiers; Tier 2 failures are warnings unless `--strict`):
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/validate-checklist.py \
     <app>/agent-harness --app-name <app> --auth-type <auth-type>
   ```
5. **Run the smoke test** for post-install validation:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/smoke-test.py cli-web-<app> --auth-type <auth-type>
   ```
6. Review remaining judgment-based checks manually per the standards skill
7. Print the report in the format shown at the bottom
8. Exit with summary: PASS if no Tier 1 failures (report Tier 2 failures as warnings), FAIL otherwise

## Prerequisites

- [ ] `npx @playwright/cli@latest --version` succeeds (playwright-cli available)

## Validation Checklist

Invoke the `standards` skill which runs the complete tiered checklist
across 11 categories:

1. Directory Structure (6 checks)
2. Required Files (13 checks)
3. CLI Implementation (9 checks)
4. Core Modules (8 checks)
5. Test Standards (8 checks)
6. Documentation (3 checks)
7. PyPI Packaging (5 checks)
8. Code Quality (8 checks)
9. REPL Quality (3 checks)
10. Error Handling & Resilience (8 checks)
11. UX Patterns (4 checks)

Every check is marked **[T1]** (critical — blocks publish) or **[T2]**
(comprehensive — warning) in
`standards/references/quality-checklist.md`.

## Report Format

Print results in this exact format:

```
CLI-Anything-Web Validation Report
App: <app>
Path: <path>/agent-harness/cli_web/<app>

Directory Structure   (X/6 checks passed)
Required Files        (X/13 files present)
CLI Implementation    (X/9 standards met)
Core Modules          (X/8 standards met)
Test Standards        (X/8 standards met)
Documentation         (X/3 standards met)
PyPI Packaging        (X/5 standards met)
Code Quality          (X/8 checks passed)
REPL Quality          (X/3 checks passed)
Error Handling        (X/8 checks passed)
UX Patterns           (X/4 checks passed)

Tier 1 (critical):      X passed, Y failed
Tier 2 (comprehensive): X passed, Y failed

Overall: PASS|PASS WITH WARNINGS|FAIL
```

For each FAIL, print a detail line below the category:
```
  FAIL [T1|T2]: <check description> — <actionable fix suggestion>
```
