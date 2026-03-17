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

> **Skills used:** `standards` (50-check validation)

1. Parse the target path to extract `<app>` name
2. Resolve the `agent-harness/` root and `cli_web/<app>/` package path
3. Run all 8 categories of checks below
4. Print the report in the format shown at the bottom
5. Exit with summary: PASS if all 50 checks pass, FAIL otherwise

## Prerequisites

- [ ] `npx @playwright/cli@latest --version` succeeds (playwright-cli available)

## Validation Checklist

Invoke the `standards` skill which defines the complete 50-check
validation across 8 categories:

1. Directory Structure (6 checks)
2. Required Files (13 checks)
3. CLI Implementation Standards (6 checks)
4. Core Module Standards (4 checks)
5. Test Standards (8 checks)
6. Documentation Standards (3 checks)
7. PyPI Packaging Standards (5 checks)
8. Code Quality (5 checks)

See the `standards` skill for the detailed checklist and report format.

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
