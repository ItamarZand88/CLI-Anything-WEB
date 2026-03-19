---
name: cli-anything-web:validate
description: Validate a cli-anything-web CLI against HARNESS.md standards and best practices. Reports 11-category N/N check results.
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

> **Skills used:** `standards` (75-check validation)

1. Parse the target path to extract `<app>` name
2. Resolve the `agent-harness/` root and `cli_web/<app>/` package path
3. Run all 11 categories of checks below
4. Print the report in the format shown at the bottom
5. Exit with summary: PASS if all 75 checks pass, FAIL otherwise

## Prerequisites

- [ ] `npx @playwright/cli@latest --version` succeeds (playwright-cli available)

## Validation Checklist

Invoke the `standards` skill which defines the complete 75-check
validation across 11 categories:

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

See `standards/references/quality-checklist.md` for the detailed checklist.

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

Overall: PASS|FAIL (X/75 checks)
```

For each FAIL, print a detail line below the category:
```
  FAIL: <check description> — <actionable fix suggestion>
```
