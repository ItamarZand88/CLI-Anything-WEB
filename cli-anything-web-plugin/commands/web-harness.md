---
name: cli-anything-web:recon
description: Run reconnaissance on a web app to detect framework, API patterns, and protections before traffic capture.
argument-hint: <url>
allowed-tools: Bash(*), Read, Write, Edit
---

## CRITICAL: Read HARNESS.md First

**Before running recon, read `${CLAUDE_PLUGIN_ROOT}/HARNESS.md`.** Phase 1a defines the reconnaissance methodology.

# CLI-Anything-Web: Reconnaissance

Read the methodology SOP:
@${CLAUDE_PLUGIN_ROOT}/HARNESS.md

Target URL: $ARGUMENTS

## Process

This command runs Phase 1a only — reconnaissance without traffic capture.

### Step 1: Check playwright-cli
!`npx @playwright/cli@latest --version 2>&1 && echo "PLAYWRIGHT_OK" || echo "PLAYWRIGHT_FAIL"`

If PLAYWRIGHT_FAIL, tell the user to install Node.js.

### Step 2: Run the 5-step recon flow

1. Open browser: `npx @playwright/cli@latest -s=recon open $ARGUMENTS --headed --persistent`
2. Framework detection: run eval scripts from `web-reconnaissance` skill
3. Network probe: `tracing-start` → click 3-4 links → `tracing-stop` → parse trace
4. Protection check: run anti-bot eval script
5. Generate RECON-REPORT.md

### Step 3: Output

Save to `<app>/agent-harness/RECON-REPORT.md` and present findings to user.

### Step 4: Clean up

Close browser: `npx @playwright/cli@latest -s=recon close`

## When to Use

- Before first `/cli-anything-web` run on an unfamiliar site
- When you want to understand a site before committing to full traffic capture
- To detect SSR frameworks, protections, or unusual API patterns
