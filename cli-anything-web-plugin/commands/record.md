---
name: cli-anything-web:record
description: Record network traffic from a web app without generating a CLI. Useful for initial exploration or adding more coverage data.
argument-hint: <url> [--recon-only] [--duration <minutes>]
allowed-tools: Bash(*), Read, Write, mcp__chrome-devtools__*
---

## CRITICAL: Read HARNESS.md First

**Before doing anything else, you MUST read `${CLAUDE_PLUGIN_ROOT}/HARNESS.md`.** Phase 1 of the methodology defines the complete recording process. Follow it exactly.

# CLI-Anything-Web: Record Traffic Only

Read the methodology SOP:
@${CLAUDE_PLUGIN_ROOT}/HARNESS.md

Target URL: $ARGUMENTS

## Prerequisites

### Step 1: Check playwright-cli availability
!`npx @playwright/cli@latest --version 2>&1 && echo "PLAYWRIGHT_OK" || echo "PLAYWRIGHT_FAIL"`

**If PLAYWRIGHT_OK** → use playwright-cli for recording.

**If PLAYWRIGHT_FAIL** → fall back to chrome-devtools MCP:
- Tell user: "playwright-cli not available. Falling back to chrome-devtools MCP."
- Launch debug Chrome: !`bash "${CLAUDE_PLUGIN_ROOT}/scripts/launch-chrome-debug.sh" $ARGUMENTS`
- If MCP not connected: tell user to `/mcp` → Reconnect
- Use `mcp__chrome-devtools__*` tools

### NEVER use `mcp__claude-in-chrome__*` tools — blocked.

## Reconnaissance (runs first)

If `--recon-only` is specified, run ONLY the recon flow:
1. Follow the `web-reconnaissance` skill's 5-step flow
2. Output `<app>/agent-harness/RECON-REPORT.md`
3. Done — no traffic capture

If full recording (no `--recon-only`):
1. Run recon first (Steps 1.1-1.5 from `web-reconnaissance` skill)
2. Show RECON-REPORT.md to user
3. Confirm recommended capture strategy
4. Proceed with traffic capture using the recommended approach

## Process

This command runs Phase 1 only — traffic recording without CLI generation.
Useful for:
- Initial exploration of an unfamiliar web app
- Adding more traffic data before refining
- Recording specific workflows

**If playwright-cli available (primary):**
1. Open browser: `npx @playwright/cli@latest -s=<app> open $ARGUMENTS --headed --persistent`
2. If login needed — ask user to log in, wait for confirmation
3. Start trace: `npx @playwright/cli@latest -s=<app> tracing-start`
4. Systematically explore: use `snapshot`, `click`, `fill`, `screenshot`
5. Stop trace: `npx @playwright/cli@latest -s=<app> tracing-stop`
6. Save auth: `npx @playwright/cli@latest -s=<app> state-save <app>-auth.json`
7. Parse: `python ${CLAUDE_PLUGIN_ROOT}/scripts/parse-trace.py .playwright-cli/traces/ --output <app>/traffic-capture/raw-traffic.json`
8. Close: `npx @playwright/cli@latest -s=<app> close`
9. Print summary: total requests captured, endpoints discovered

**If MCP fallback:**
1. Verify debug Chrome on port 9222
2. `navigate_page` with target URL
3. `list_network_requests` + `get_network_request` for traffic
4. Save to `<app>/traffic-capture/raw-traffic.json`

## Interactive Mode

Ask the user at each major section:
- "I see a boards section. Should I explore it? (create/read/update/delete)"
- "I found a settings area. Should I capture these endpoints too?"

This gives the user control over what gets recorded.
