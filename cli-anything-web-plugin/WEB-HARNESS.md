# WEB-HARNESS.md — Methodology SOP

**Making Closed-Source Web Apps Agent-Native via Network Traffic Analysis**

This is the single source of truth for the web-harness pipeline.
All commands reference this document. It encodes proven patterns for
generating production-ready CLI interfaces from observed HTTP traffic.

---

## Core Philosophy

CLI-Anything generates CLIs from **source code**.
Web-Harness generates CLIs from **network traffic**.

The output is identical: a stateful Python CLI under `cli_web_<app>/`
with Click commands, `--json` output, REPL mode, undo/redo, session
management, and comprehensive tests. The difference is the input —
instead of reading `.py` / `.c` / `.js` source files, we observe
live HTTP requests flowing between the browser and the server.

### Design Principles (inherited from CLI-Anything)

1. **Authentic Integration** — The CLI sends real HTTP requests to real
   servers. No mocks, no reimplementations, no toy replacements.
2. **Dual Interaction** — Every CLI has REPL mode + subcommand mode.
3. **Agent-Native** — `--json` flag on every command. `--help` self-docs.
   Agents discover tools via `which cli-web-<app>`.
4. **Zero Compromise** — Tests fail (not skip) when auth is missing or
   endpoints are unreachable.
5. **Structured Output** — JSON for agents, human-readable tables for
   interactive use.

---

## 7-Phase Pipeline

### Phase 1 — Record (Traffic Capture)

**Goal:** Capture comprehensive HTTP traffic from the target web app.

**Process:**
1. chrome-devtools-mcp auto-launches Chrome on first tool call — no setup step needed
2. Call `navigate_page` with the target URL
3. If login required — pause and ask user to log in manually
4. Enable network monitoring (`list_network_requests`)
5. Systematically exercise the app:
   - Navigate all major sections
   - Create, read, update, delete entities
   - Use filters, search, export features
   - Trigger edge cases (errors, empty states)
6. For each user action, capture:
   - The request: method, URL, headers, body
   - The response: status, headers, body
   - The timing and sequence context
7. Use `get_network_request(id)` for full payload details
8. Use `evaluate_script` for fetch/XHR interception if needed
9. Store captured traffic in `<app>/traffic-capture/raw-traffic.json`

**Output:** `raw-traffic.json` — complete traffic dump.

**Critical rules:**
- Filter OUT: static assets (.js, .css, .png, fonts, analytics, CDN)
- Filter IN: API calls (typically `/api/`, GraphQL, RPC endpoints)
- Capture auth tokens/cookies for session management design
- Record the user action that triggered each request group

### Phase 2 — Analyze (API Discovery)

**Goal:** Map raw traffic to a structured API model.

**Process:**
1. Parse `raw-traffic.json`
2. Group requests by base path (e.g., `/api/v1/boards/`, `/api/v1/items/`)
3. For each endpoint group, identify:
   - HTTP method (GET/POST/PUT/DELETE/PATCH)
   - URL pattern (extract path parameters like `:id`)
   - Query parameters and their types
   - Request body schema (JSON fields, types, required/optional)
   - Response body schema
   - Authentication method (Bearer token, cookie, API key)
   - Rate limiting signals (429 responses, retry-after headers)
4. Detect data model:
   - Entity types (boards, items, users, projects...)
   - Relationships (board has many items, item belongs to board)
   - ID formats (UUID, numeric, slug)
5. Detect auth pattern:
   - Cookie-based sessions
   - Bearer/JWT tokens
   - OAuth refresh flow
   - API key headers
6. Write `<APP>.md` — software-specific SOP document

**Output:** `<APP>.md` with API map, data model, auth scheme.

### Phase 3 — Design (CLI Architecture)

**Goal:** Design the CLI command structure.

**Process:**
1. Map each API endpoint group to a Click command group:
   - `/api/v1/boards/*` → `boards` command group
   - `/api/v1/items/*` → `items` command group
2. Map CRUD operations to subcommands:
   - GET (list) → `boards list`
   - GET (single) → `boards get --id <id>`
   - POST → `boards create --name <name>`
   - PUT/PATCH → `boards update --id <id> --name <name>`
   - DELETE → `boards delete --id <id>`
3. Design auth management:
   - `auth login` — interactive login flow
   - `auth status` — show current session
   - `auth refresh` — refresh token if applicable
   - Store credentials in `~/.config/cli-web-<app>/auth.json`
4. Design session state:
   - Current workspace/project context
   - Undo/redo stack for mutating operations
   - Output format preferences
5. Design REPL commands:
   - Bare command → enters REPL
   - Branded banner via `repl_skin.py`
   - Context-aware prompt showing current entity

**Output:** Architecture spec in `<APP>.md`.

### Phase 4 — Implement (Code Generation)

**Goal:** Generate the complete Python CLI package.

**Package structure** (matches CLI-Anything convention):
```
<app>/
└── agent-harness/
    ├── <APP>.md                    # Software-specific SOP
    ├── setup.py                    # PyPI config (find_namespace_packages)
    └── cli_web/                    # Namespace package (NO __init__.py)
        └── <app>/                  # Sub-package (HAS __init__.py)
            ├── __init__.py
            ├── __main__.py         # python -m cli_web.<app>
            ├── <app>_cli.py        # Main CLI entry point
            ├── core/
            │   ├── __init__.py
            │   ├── client.py       # HTTP client (requests/httpx)
            │   ├── auth.py         # Auth management
            │   ├── session.py      # State + undo/redo
            │   └── models.py       # Response models
            ├── commands/           # Click command groups
            │   ├── __init__.py
            │   └── <resource>.py   # One file per API resource
            ├── utils/
            │   ├── __init__.py
            │   ├── repl_skin.py    # Unified REPL (from plugin)
            │   ├── output.py       # JSON/table formatting
            │   └── config.py       # Config file management
            └── tests/
                ├── __init__.py
                ├── TEST.md         # Test plan + results
                ├── test_core.py    # Unit tests (mocked HTTP)
                └── test_e2e.py     # E2E tests (live API)
```

**Implementation rules:**
- `client.py` — thin HTTP wrapper using `httpx` or `requests`
  - Centralized auth header injection
  - Automatic JSON parsing
  - Error handling with status code mapping
  - Rate limit respect (exponential backoff)
- `auth.py` — handles token storage, refresh, expiry
- Every command: `--json` flag, proper error messages
- Entry point: `cli-web-<app>` via setup.py console_scripts
- Namespace: `cli_web.*` (parallel to CLI-Anything's `cli_anything.*`)
- Copy `repl_skin.py` from plugin for consistent REPL experience

### Phase 5 — Test (Write Tests)

**Goal:** Comprehensive test suite.

**Test layers** (matches CLI-Anything):

| Layer | What it tests | Example |
|-------|--------------|---------|
| Unit tests | Core functions with mocked HTTP | `test_core.py` — CRUD ops, auth, parsing |
| E2E tests (mocked) | Full command flow with recorded responses | Replay captured traffic |
| E2E tests (live) | Real API calls against running service | Create/read/update/delete cycle |
| CLI subprocess | Installed command via `subprocess.run` | `cli-web-<app> --json boards list` |

**Testing rules:**
- Use `unittest.mock.patch` for HTTP in unit tests
- Store captured responses in `tests/fixtures/` for replay
- E2E live tests require auth — fail (don't skip) without it
- `TestCLISubprocess` using `_resolve_cli("cli-web-<app>")`
- Target: >80% coverage on core modules

### Phase 6 — Document (Update TEST.md)

**Goal:** Write TEST.md with plan and results.

**Process:**
1. Run full test suite: `python3 -m pytest cli_web/<app>/tests/ -v`
2. Update TEST.md with pass/fail summary
3. Document any skipped tests and why
4. Include example CLI usage in README.md

### Phase 7 — Publish (Install to PATH)

**Goal:** Make CLI discoverable and installable.

**Process:**
1. Create `setup.py` with:
   - `find_namespace_packages` for `cli_web.*`
   - `console_scripts` entry point: `cli-web-<app>`
   - Dependencies: `click>=8.0`, `httpx`, `rich` (optional)
2. Install: `pip install -e .`
3. Verify: `which cli-web-<app>`
4. Test installed: `cli-web-<app> --help`
5. Test JSON: `cli-web-<app> --json <command>`

---

## Critical Lessons

### Lesson 1: Auth is Everything
Unlike CLI-Anything where the software runs locally, web apps require
authentication. The auth module is the most critical component. Design
it for: token refresh, session recovery, multi-account support.

### Lesson 2: Capture Comprehensively
A 5-minute browse session won't capture the full API surface.
Systematically exercise every feature. Use `/web-harness:refine`
to expand coverage iteratively.

### Lesson 3: APIs Change
Unlike local software, web APIs can change without notice.
Include version detection and graceful degradation for removed
endpoints. Tests should detect API changes early.

### Lesson 4: Rate Limiting
Respect rate limits. Add exponential backoff. Cache responses
where safe. Never hammer endpoints during recording or testing.

### Lesson 5: Verify Responses
Never trust status 200 alone. Verify response body contains
expected fields. Some APIs return 200 with error payloads.

### Lesson 6: GraphQL Needs Special Handling
Many modern apps use GraphQL. The CLI should abstract query
complexity — users run `items list`, not write GraphQL queries.
Map operations to human-friendly commands.

---

## Naming Conventions

| Convention | CLI-Anything | Web-Harness |
|-----------|-------------|-------------|
| CLI command | `cli-anything-<software>` | `cli-web-<app>` |
| Namespace | `cli_anything.<software>` | `cli_web.<app>` |
| SOP doc | `<SOFTWARE>.md` | `<APP>.md` |
| Plugin command | `/cli-anything` | `/web-harness` |
| Traffic data | N/A (source code) | `traffic-capture/` |
