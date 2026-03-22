---
name: cli-anything-web:record
description: Record network traffic from a web app without generating a CLI. Useful for initial exploration or adding more coverage data.
argument-hint: <url> [--duration <minutes>]
allowed-tools: Bash(*), Read, Write, mcp__chrome-devtools__*
---

# CLI-Anything-Web: Record Traffic Only

Read the methodology overview:
@${CLAUDE_PLUGIN_ROOT}/HARNESS.md

Target URL: $ARGUMENTS

## Prerequisites

### Step 1: Check playwright-cli availability
!`npx @playwright/cli@latest --version 2>&1 && echo "PLAYWRIGHT_OK" || echo "PLAYWRIGHT_FAIL"`

**If PLAYWRIGHT_OK** -> use playwright-cli for recording.

**If PLAYWRIGHT_FAIL** -> If playwright-cli is not available, see HARNESS.md for the MCP fallback path.

### NEVER use `mcp__claude-in-chrome__*` tools -- blocked.

## Process

Invoke the `capture` skill for Phase 1 traffic recording.
The capture skill handles everything: site assessment, setup, trace, explore, parse.

**Difference from `/cli-anything-web`:** This command records traffic ONLY — it does not
generate a CLI. Use this when you want to explore a site's API surface before committing
to full CLI generation, or when adding coverage data to an existing capture.

## Interactive Mode

Ask the user at each major section:
- "I see a boards section. Should I explore it? (create/read/update/delete)"
- "I found a settings area. Should I capture these endpoints too?"

This gives the user control over what gets recorded.

## Output

Traffic is saved to `<app>/traffic-capture/raw-traffic.json`. To generate a CLI
from this data later, run `/cli-anything-web <url>`.
