---
name: web-harness:record
description: Record network traffic from a web app without generating a CLI. Useful for initial exploration or adding more coverage data.
argument-hint: <url> [--duration <minutes>]
allowed-tools: Bash(*), Read, Write, mcp__chrome-devtools__*
---

## CRITICAL: Read WEB-HARNESS.md First

**Before doing anything else, you MUST read `${CLAUDE_PLUGIN_ROOT}/WEB-HARNESS.md`.** Phase 1 of the methodology defines the complete recording process. Follow it exactly.

# Web-Harness: Record Traffic Only

Read the methodology SOP:
@${CLAUDE_PLUGIN_ROOT}/WEB-HARNESS.md

Target URL: $ARGUMENTS

## Process

This command runs Phase 1 only — traffic recording without CLI generation.
Useful for:
- Initial exploration of an unfamiliar web app
- Adding more traffic data before refining
- Recording specific workflows

1. chrome-devtools-mcp auto-launches Chrome on first tool call. Call `navigate_page` with the target URL.
2. If login required — ask user to authenticate manually
3. Systematically exercise the app features
4. Capture all API traffic via `list_network_requests` + `get_network_request`
5. Filter: keep API calls, discard static assets
6. Save to `<app>/traffic-capture/raw-traffic.json`
7. Print summary: total requests captured, endpoints discovered, auth type detected

## Interactive Mode

Ask the user at each major section:
- "I see a boards section. Should I explore it? (create/read/update/delete)"
- "I found a settings area. Should I capture these endpoints too?"

This gives the user control over what gets recorded.
