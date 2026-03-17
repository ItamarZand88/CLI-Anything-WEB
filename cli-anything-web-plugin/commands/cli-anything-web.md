---
name: cli-anything-web
description: Generate a complete agent-native CLI for any web app by recording and analyzing network traffic via playwright-cli. Runs the full 8-phase pipeline with optional reconnaissance.
argument-hint: <url>
allowed-tools: Bash(*), Read, Write, Edit, mcp__chrome-devtools__*
---

## CRITICAL: Read HARNESS.md First

**Before doing anything else, you MUST read `${CLAUDE_PLUGIN_ROOT}/HARNESS.md`.** It defines the complete methodology, all phases, and implementation standards. Every phase below follows HARNESS.md. Do not improvise — follow the harness specification.

# CLI-Anything-Web: Full Pipeline

Read the methodology SOP first:
@${CLAUDE_PLUGIN_ROOT}/HARNESS.md

Target URL: $ARGUMENTS

## Prerequisites Check

### Step 1: Check playwright-cli availability
!`npx @playwright/cli@latest --version 2>&1 && echo "PLAYWRIGHT_OK" || echo "PLAYWRIGHT_FAIL"`

**If PLAYWRIGHT_OK** → use playwright-cli for all operations (primary path).

**If PLAYWRIGHT_FAIL** → fall back to chrome-devtools MCP:
- Tell user: "playwright-cli not available. Falling back to chrome-devtools MCP."
- Launch debug Chrome: !`bash "${CLAUDE_PLUGIN_ROOT}/scripts/launch-chrome-debug.sh" $ARGUMENTS`
- If first time, ask user to log in. Wait for confirmation.
- If MCP not connected: tell user "Type `/mcp`, find **chrome-devtools**, click **Reconnect**."
- Use `mcp__chrome-devtools__*` tools for all operations.

### NEVER use `mcp__claude-in-chrome__*` tools — blocked, cannot capture request bodies.

## Execution Plan

Run ALL 8 phases in sequence for the target web app.
Extract the app name from the URL (e.g., `monday.com` → `monday`, `notion.so` → `notion`).

### Phase 1 — Record (Traffic Capture)

Follow HARNESS.md Phase 1 exactly. Key steps:
1. Check playwright-cli → MCP fallback if unavailable
2. `tracing-start` → systematic exploration (READ + WRITE ops) → `tracing-stop`
3. `parse-trace.py` → `raw-traffic.json`
4. **Verify trace contains WRITE operations** before proceeding

See HARNESS.md for the full exploration checklist and commands.

### Phase 2 — Analyze
> Follow HARNESS.md Phase 2. Parse `raw-traffic.json`, identify protocol type, map endpoints.

### Phase 3 — Design
> Follow HARNESS.md Phase 3. Map endpoints → Click command groups. Design auth + REPL.

### Phase 4 — Implement
> Follow HARNESS.md Phase 4. **Dispatch parallel subagents** for command modules.

### Phase 5 — Plan Tests
> Follow HARNESS.md Phase 5. Write TEST.md Part 1 BEFORE any test code.

### Phase 6 — Test
> Follow HARNESS.md Phase 6. **Auth MUST be configured first.** Parallel subagents for test files.

### Phase 7 — Document
> Follow HARNESS.md Phase 7. Append TEST.md Part 2 (results).

### Phase 8 — Publish and Verify
> Follow HARNESS.md Phase 8. **Must include WRITE smoke test** — not just reads.

## Success Criteria

The command succeeds when:
1. All core modules are implemented and functional (`client.py`, `auth.py`, `session.py`, `models.py`)
2. CLI supports both one-shot commands and REPL mode
3. `--json` output mode works for all commands
4. All tests pass (100% pass rate)
5. Subprocess tests use `_resolve_cli()` and pass with `CLI_WEB_FORCE_INSTALLED=1`
6. TEST.md contains both plan (Part 1) and results (Part 2)
7. README.md documents installation and usage
8. `setup.py` is created and local installation works
9. CLI is available in PATH as `cli-web-<app>`

## Output Structure

```
<app-name>/
└── agent-harness/
    ├── <APP>.md               # API map, data model, auth scheme
    ├── setup.py               # PyPI config (find_namespace_packages)
    └── cli_web/               # Namespace package (NO __init__.py)
        └── <app>/             # Sub-package
            ├── __init__.py    # Required — marks as sub-package
            ├── README.md
            ├── <app>_cli.py   # Main CLI entry point
            ├── __main__.py
            ├── core/
            │   ├── client.py
            │   ├── auth.py
            │   ├── session.py
            │   └── models.py
            ├── utils/
            │   ├── repl_skin.py
            │   ├── output.py
            │   └── config.py
            └── tests/
                ├── TEST.md
                ├── test_core.py
                └── test_e2e.py
```

## Progress Tracking

After each phase, report status in this format:

```
┌─────────┬────────┬────────────────────────────────────────────┐
│ Phase   │ Status │ Description                                │
├─────────┼────────┼────────────────────────────────────────────┤
│ Phase 1 │ ...    │ Record — Traffic Capture                   │
│ Phase 2 │ ...    │ Analyze — API Discovery                    │
│ Phase 3 │ ...    │ Design — CLI Architecture                  │
│ Phase 4 │ ...    │ Implement — Code Generation                │
│ Phase 5 │ ...    │ Plan Tests — TEST.md Part 1                │
│ Phase 6 │ ...    │ Test — Write Tests                         │
│ Phase 7 │ ...    │ Document — Update TEST.md                  │
│ Phase 8 │ ...    │ Publish — Install to PATH                  │
└─────────┴────────┴────────────────────────────────────────────┘
```
