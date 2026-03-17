---
name: cli-anything-web
description: Generate a complete agent-native CLI for any web app by recording and analyzing network traffic via playwright-cli. Runs the full 8-phase pipeline with optional reconnaissance.
argument-hint: <url>
allowed-tools: Bash(*), Read, Write, Edit, mcp__chrome-devtools__*
---

# CLI-Anything-Web: Full Pipeline

Read the methodology overview:
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

Run the full pipeline by invoking skills in sequence:

1. Check playwright-cli availability (see Prerequisites above)
2. Invoke `cli-anything-web-capture` skill -- Phase 1 site assessment + traffic recording
3. Invoke `cli-anything-web-methodology` skill -- Phases 2-4 analyze/design/implement
4. Invoke `cli-anything-web-testing` skill -- Phases 5-7 test planning/writing/documentation
5. Invoke `cli-anything-web-standards` skill -- Phase 8 publish and verify

Each skill handles its phases completely and invokes the next when done.
See HARNESS.md for the pipeline overview and critical rules.

Extract the app name from the URL (e.g., `monday.com` → `monday`, `notion.so` → `notion`).

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
