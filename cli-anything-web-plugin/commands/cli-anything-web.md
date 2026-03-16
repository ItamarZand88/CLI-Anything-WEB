---
name: cli-anything-web
description: Generate a complete agent-native CLI for any web app by recording and analyzing network traffic via Chrome DevTools MCP. Runs the full 8-phase pipeline.
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

### CRITICAL: Do NOT use `mcp__claude-in-chrome__*` tools. NEVER. Not as a fallback, not as an alternative.

The `claude-in-chrome` extension CANNOT capture full request/response bodies which
are essential for Phase 1 traffic recording. If you use `claude-in-chrome`, the
generated CLI will be broken because you won't have the API payload data.

You MUST use `mcp__chrome-devtools__*` tools ONLY.

**Step 1: Launch Chrome debug profile:**
!`bash "${CLAUDE_PLUGIN_ROOT}/scripts/launch-chrome-debug.sh" $ARGUMENTS`
If first time, ask the user to log in. Wait for confirmation.

**Step 2: Check if `mcp__chrome-devtools__*` tools are available.**
If they are NOT available — STOP. Do not proceed. Do not fall back to claude-in-chrome.
Tell the user exactly this:

"I need the chrome-devtools MCP to capture API traffic, but it's not connected.
Please do these steps:
1. Make sure the debug Chrome is running (check if the Chrome window opened)
2. Type `/mcp` in the chat
3. Find **chrome-devtools** in the list
4. Click **Reconnect**
5. Tell me when it's ready"

Do NOT continue until the user confirms and `mcp__chrome-devtools__*` tools work.

!`which npx && echo "npx: OK" || echo "npx: MISSING"`

## Execution Plan

Run ALL 8 phases in sequence for the target web app.
Extract the app name from the URL (e.g., `monday.com` → `monday`, `notion.so` → `notion`).

### Phase 1 — Record (Traffic Capture)

1. Verify debug Chrome is running on port 9222 with user logged in.
   Use `mcp__chrome-devtools__*` tools:
   - Call `navigate_page` with the target URL
   - If login has expired — pause and ask user to re-authenticate

2. Systematically explore the app:
   - Navigate to each major section/page
   - Perform CRUD operations (create, read, update, delete)
   - Exercise search, filter, and export features
   - After each action, call `list_network_requests` to capture traffic
   - Use `get_network_request(id)` for full request/response details

3. Filter captured traffic:
   - KEEP: API calls (JSON responses, `/api/`, GraphQL, RPC)
   - DISCARD: static assets, analytics, CDN, fonts, images
   - KEEP: auth-related requests (login, token refresh, session)

4. Save raw traffic to `<app>/traffic-capture/raw-traffic.json`

### Phase 2 — Analyze (API Discovery)

1. Parse the captured traffic
2. Group by endpoint base path
3. Identify: methods, URL patterns, params, body schemas, auth scheme
4. Detect entity types and relationships
5. Write `<app>/agent-harness/<APP>.md` — the software-specific SOP

### Phase 3 — Design (CLI Architecture)

1. Map endpoint groups → Click command groups
2. Map CRUD → subcommands (list, get, create, update, delete)
3. Design auth management (login, status, refresh)
4. Design session state and REPL
5. Document architecture in `<APP>.md`

### Phase 4 — Implement (Code Generation)

1. Create the package structure under `<app>/agent-harness/cli_web/<app>/`
2. **First (sequential):** Implement core modules — `client.py`, `auth.py`, `session.py`, `models.py`
   These are the foundation that command files import.
3. **Then (parallel subagents):** Dispatch one agent per command module — each is independent:
   ```
   Agent 1 → "Implement commands/notebooks.py"
   Agent 2 → "Implement commands/sources.py"
   Agent 3 → "Implement commands/chat.py"
   # All run concurrently
   ```
   Each agent gets: the `<APP>.md` API spec, `client.py` interface, its resource endpoints.
4. **Last (sequential):** Wire together — `<app>_cli.py`, `__main__.py`, `setup.py`, copy `repl_skin.py`

### Phase 5 — Plan Tests (TEST.md Part 1)

1. Write `tests/TEST.md` with test plan BEFORE writing test code
2. Plan test inventory, unit tests per module, E2E scenarios
3. Define realistic workflow scenarios (auth flow, CRUD round-trip, pagination)

### Phase 6 — Test (Write Tests)

1. **Parallel subagents** for independent test files:
   ```
   Agent 1 → "Write unit tests for client.py + auth.py in test_core.py"
   Agent 2 → "Write E2E fixture replay + live CRUD tests in test_e2e.py"
   ```
2. Integrate, store response fixtures in `tests/fixtures/`
3. Run all tests — ALL must pass with real auth

### Phase 7 — Document

1. Run tests: `cd <app>/agent-harness && python3 -m pytest cli_web/<app>/tests/ -v`
2. Update TEST.md with results
3. Write README.md with usage examples

### Phase 8 — Publish

1. Install: `cd <app>/agent-harness && pip install -e .`
2. Verify: `which cli-web-<app>`
3. Test: `cli-web-<app> --help`
4. Test JSON: `cli-web-<app> --json <first-command> list`

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
