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

**If PLAYWRIGHT_FAIL** -> fall back to chrome-devtools MCP:
- Tell user: "playwright-cli not available. Falling back to chrome-devtools MCP."
- Launch debug Chrome: !`bash "${CLAUDE_PLUGIN_ROOT}/scripts/launch-chrome-debug.sh" $ARGUMENTS`
- If MCP not connected: tell user to `/mcp` -> Reconnect
- Use `mcp__chrome-devtools__*` tools

### NEVER use `mcp__claude-in-chrome__*` tools -- blocked.

## Process

Invoke the `cli-anything-web-capture` skill for Phase 1 traffic recording.
The capture skill handles everything: site assessment, setup, trace, explore, parse.

## Interactive Mode

Ask the user at each major section:
- "I see a boards section. Should I explore it? (create/read/update/delete)"
- "I found a settings area. Should I capture these endpoints too?"

This gives the user control over what gets recorded.
