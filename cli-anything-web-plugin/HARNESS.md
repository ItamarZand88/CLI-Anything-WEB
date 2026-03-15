# HARNESS.md — Methodology SOP

**Making Closed-Source Web Apps Agent-Native via Network Traffic Analysis**

This is the single source of truth for the cli-anything-web pipeline.
All commands reference this document. It encodes proven patterns for
generating production-ready CLI interfaces from observed HTTP traffic.

---

## Core Philosophy

CLI-Anything-Web builds production-grade Python CLI interfaces for closed-source web
applications by observing their live HTTP traffic. We capture real API calls directly
from the browser, reverse-engineer the API surface, and generate a stateful CLI that
sends authentic HTTP requests to the real service.

The output: a Python CLI under `cli_web/<app>/` with Click commands, `--json` output,
REPL mode, auth management, session state, and comprehensive tests.

### Design Principles

1. **Authentic Integration** — The CLI sends real HTTP requests to real servers.
   No mocks, no reimplementations, no toy replacements.
2. **Dual Interaction** — Every CLI has REPL mode + subcommand mode.
3. **Agent-Native** — `--json` flag on every command. `--help` self-docs.
   Agents discover tools via `which cli-web-<app>`.
4. **Zero Compromise** — Tests fail (not skip) when auth is missing or endpoints
   are unreachable.
5. **Structured Output** — JSON for agents, human-readable tables for interactive use.

---

## 8-Phase Pipeline

### Prerequisites — Chrome Debug Profile

Before running the pipeline, the user must have a dedicated Chrome debug profile
with an active login session for the target web app. This is required because Google
and many other services block sign-in on automated/debugged browser instances.

**One-time setup:**

1. Launch Chrome with a dedicated debug profile:
   ```bash
   # Windows
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\.chrome-debug-profile"

   # macOS
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-debug-profile"

   # Linux
   google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-debug-profile"
   ```
2. In that Chrome window, navigate to the target web app and **log in normally**
3. Close Chrome — your session cookies persist in `~/.chrome-debug-profile/`

**Before each recording session:**

Re-launch the debug Chrome (same command as above). You'll already be logged in.
The plugin's `.mcp.json` configures chrome-devtools-mcp to connect on port 9222.

---

### Phase 1 — Record (Traffic Capture)

**Goal:** Capture comprehensive HTTP traffic from the target web app.

**Process:**
1. Verify the debug Chrome is running on port 9222 with the user already logged in
2. Call `navigate_page` with the target URL
3. If login has expired — pause and ask user to re-authenticate in the debug Chrome
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

**Package structure:**
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
  - **MUST support `auth login --from-browser`** — auto-extract cookies from the
    Chrome debug profile (port 9222) using CDP. This is the primary login method.
    Use `${CLAUDE_PLUGIN_ROOT}/scripts/extract-browser-cookies.py` as the reference
    implementation. The flow:
    1. Connect to Chrome debug port (`http://127.0.0.1:9222`)
    2. Use `Storage.getCookies` CDP command to get all cookies
    3. Filter for the target domain (e.g., `.google.com`)
    4. Save to `~/.config/cli-web-<app>/auth.json`
    Requires `pip install websockets`.
  - Also support `auth login --cookies-json <file>` as a fallback for manual import
  - Store cookies at `~/.config/cli-web-<app>/auth.json` with chmod 600
- Every command: `--json` flag, proper error messages
- Entry point: `cli-web-<app>` via setup.py console_scripts
- Namespace: `cli_web.*`
- Copy `repl_skin.py` from plugin for consistent REPL experience

### Phase 5 — Plan Tests (TEST.md Part 1)

**Goal:** Write the test plan BEFORE writing any test code.

**BEFORE writing any test code**, create `tests/TEST.md` in the app package.
This file serves as the test plan and MUST contain:

1. **Test Inventory** — List planned test files and estimated test counts:
   - `test_core.py`: XX unit tests planned
   - `test_e2e.py`: XX E2E tests planned (fixture), XX E2E tests planned (live),
     XX subprocess tests planned

2. **Unit Test Plan** — For each core module, describe what will be tested:
   - Module name (e.g., `client.py`)
   - Functions to test
   - Edge cases (invalid auth, rate limit response, malformed JSON, 404, 401, 500)
   - Expected test count

3. **E2E Test Plan** — Describe the test scenarios:
   - Fixture replay tests: which captured responses will be replayed?
   - Live tests: which CRUD workflows will run against the real API?
   - What response fields will be verified?

4. **Realistic Workflow Scenarios** — Detail each multi-step workflow:
   - **Scenario name**
   - **Simulates**: what real user task (e.g., "creating and managing a project board",
     "bulk-creating tasks and archiving completed ones")
   - **Operations**: step-by-step API calls
   - **Verified**: what response fields and round-trip consistency is checked

   Example scenarios for web apps:
   - Auth flow: login → store token → make authenticated request → token refresh
   - CRUD round-trip: create entity → read it back → verify fields match → update →
     verify update → delete → verify 404 on read
   - Paginated list: fetch page 1 → verify count → fetch page 2 → verify no overlap
   - Bulk operations: create N items → list all → verify count → delete all → verify empty
   - Rate limit handling: rapid requests → verify backoff behavior

This planning document ensures comprehensive test coverage before writing code.

### Phase 6 — Test (Write Tests)

**Goal:** Comprehensive test suite.

**Test layers:**

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

**Response Body Verification — never trust status 200 alone:**
- Always verify the response body contains expected top-level fields
- For create operations: verify returned entity has the submitted field values
- For read operations: verify entity ID matches what was requested
- For update operations: verify changed fields reflect new values
- For delete operations: verify subsequent read returns 404
- For list operations: verify count, verify each item has required fields
- Print entity IDs and counts so users can manually verify: e.g.,
  `print(f"[verify] Created board id={data['id']} name={data['name']}")`

**Round-trip test requirement:** every E2E live test MUST include at minimum
a create → read → verify round-trip. Tests that only create without reading back give
false confidence.

### Phase 7 — Document (Update TEST.md)

**Goal:** Append test results to TEST.md (Part 2).

Phase 7 **appends** results to the existing `TEST.md` (which already has Part 1 from Phase 5). It does NOT write TEST.md from scratch.

**Process:**
1. Run full test suite: `python3 -m pytest cli_web/<app>/tests/ -v --tb=short`
2. Run subprocess tests: `CLI_WEB_FORCE_INSTALLED=1 python3 -m pytest cli_web/<app>/tests/ -v -s -k subprocess`
3. **Append** Part 2 to existing `TEST.md`:
   - Full `pytest -v --tb=no` output
   - Summary: total tests, pass rate, execution date
   - Any gaps or failed tests with explanation
4. Include example CLI usage in README.md

### Phase 8 — Publish (Install to PATH)

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

**Why namespace packages:**
- Multiple `cli-web-*` CLIs coexist in the same Python environment without conflicts
- `cli_web/` has NO `__init__.py` — this is the rule that enables it
- Use `find_namespace_packages(include=["cli_web.*"])` — NOT `find_packages`
- Install verification:
  ```bash
  pip install -e .
  which cli-web-<app>
  CLI_WEB_FORCE_INSTALLED=1 python3 -m pytest cli_web/<app>/tests/ -v -s
  ```
  Output must show `[_resolve_cli] Using installed command:` confirming the installed package is tested.

---

## Critical Lessons

### Lesson 1: Auth is Everything
Web apps require authentication for every operation. The auth module is
the most critical component. Design it for: token refresh, session
recovery, multi-account support.

### Lesson 2: Capture Comprehensively
A 5-minute browse session won't capture the full API surface.
Systematically exercise every feature. Use `/cli-anything-web:refine`
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

## Rules

- **Auth credentials MUST be stored securely.** `chmod 600 auth.json`. Never hardcode
  tokens in source. If auth file missing, CLI errors with clear instructions — never
  falls back to unauthenticated requests.
- **Tests MUST fail (not skip) when auth is missing.** Tests that skip on missing auth
  give false confidence. The CLI is useless without a live account.
- **Every command MUST support `--json`.** Agents consume structured output.
  Human-readable is optional; machine-readable is required.
- **E2E tests MUST include subprocess tests** via `_resolve_cli("cli-web-<app>")`.
  Tests must run against the installed package, not just source imports.
- **Every `cli_web/<app>/` MUST contain `README.md`** with auth setup, install steps,
  and usage examples.
- **Every `cli_web/<app>/tests/` MUST contain `TEST.md`** written in two parts: plan
  (before tests), results (appended after running).
- **Every CLI MUST use the unified REPL skin** (`repl_skin.py`). REPL MUST be the
  default when invoked without a subcommand.
- **Rate limits MUST be respected.** Never retry without backoff. Never hammer endpoints.
- **Response bodies MUST be verified.** Never trust HTTP status alone. Always check
  that returned JSON contains expected fields.

---

## Testing Strategy

Four test layers with complementary purposes:

| Layer | File | What it tests |
|-------|------|--------------|
| Unit tests | `test_core.py` | Core functions with mocked HTTP. No real network. Fast, deterministic. |
| E2E fixture tests | `test_e2e.py` | Full command flow replaying captured responses from `tests/fixtures/`. Verifies parsing logic. |
| E2E live tests | `test_e2e.py` | Real API calls. Require auth — FAIL without it. CRUD round-trip, workflow scenarios. |
| CLI subprocess | `test_e2e.py` | Installed `cli-web-<app>` via `_resolve_cli()`. Full workflow end-to-end. |

Use the `_resolve_cli` helper for subprocess tests:
```python
def _resolve_cli(name):
    force = os.environ.get("CLI_WEB_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-web-", "cli_web.") + "." + name.split("-")[-1] + "_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]
```

**App naming convention:** App names must contain no hyphens. Underscores are permitted
(e.g., `cli-web-monday_com` → `cli_web.monday_com.monday_com_cli`). Valid examples:
`monday`, `notion`, `jira`, `monday_com`.

---

## Naming Conventions

| Convention | Value |
|-----------|-------|
| CLI command | `cli-web-<app>` |
| Python namespace | `cli_web.<app>` |
| App-specific SOP | `<APP>.md` |
| Plugin slash command | `/cli-anything-web` |
| Traffic capture dir | `traffic-capture/` |
| Auth config dir | `~/.config/cli-web-<app>/` |
