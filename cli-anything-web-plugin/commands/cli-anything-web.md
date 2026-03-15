---
name: cli-anything-web
description: Generate a complete agent-native CLI for any web app by recording and analyzing network traffic via Chrome DevTools MCP. Runs the full 8-phase pipeline.
argument-hint: <url>
allowed-tools: Bash(*), Read, Write, Edit, mcp__chrome-devtools__*
---

## CRITICAL: Read CLI-ANYTHING-WEB.md First

**Before doing anything else, you MUST read `${CLAUDE_PLUGIN_ROOT}/CLI-ANYTHING-WEB.md`.** It defines the complete methodology, all phases, and implementation standards. Every phase below follows CLI-ANYTHING-WEB.md. Do not improvise — follow the harness specification.

# CLI-Anything-Web: Full Pipeline

Read the methodology SOP first:
@${CLAUDE_PLUGIN_ROOT}/CLI-ANYTHING-WEB.md

Target URL: $ARGUMENTS

## Prerequisites Check

Verify Chrome DevTools MCP is available:
!`which npx && echo "npx: OK" || echo "npx: MISSING"`

## Execution Plan

Run ALL 8 phases in sequence for the target web app.
Extract the app name from the URL (e.g., `monday.com` → `monday`, `notion.so` → `notion`).

### Phase 1 — Record (Traffic Capture)

1. Use chrome-devtools-mcp to open the target URL:
   - chrome-devtools-mcp auto-launches Chrome on first tool call
   - Call `navigate_page` with the target URL
   - If the page shows a login screen, STOP and ask the user to log in manually
   - Wait for user confirmation before proceeding

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
2. Implement `client.py` — HTTP client with auth injection
3. Implement `auth.py` — token storage and refresh
4. Implement command files — one per resource
5. Implement `<app>_cli.py` — main entry point
6. Copy `repl_skin.py` from: `${CLAUDE_PLUGIN_ROOT}/scripts/repl_skin.py`
7. Create `setup.py` with `cli-web-<app>` entry point

### Phase 5 — Plan Tests (TEST.md Part 1)

1. Write `tests/TEST.md` with test plan BEFORE writing test code
2. Plan test inventory, unit tests per module, E2E scenarios
3. Define realistic workflow scenarios (auth flow, CRUD round-trip, pagination)

### Phase 6 — Test (Write Tests)

1. Create `test_core.py` — unit tests with mocked HTTP
2. Create `test_e2e.py` — integration tests with captured fixtures
3. Store response fixtures in `tests/fixtures/`
4. Write TEST.md with test plan

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
