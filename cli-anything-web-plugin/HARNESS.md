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

## Browser Automation: playwright-cli

The plugin uses `npx @playwright/cli@latest` (playwright-cli) for all browser
interaction and traffic capture. This is a CLI tool — the agent calls it via Bash,
not through MCP. Data (snapshots, screenshots, traces) goes to files on disk,
keeping context usage ~4x lower than MCP-based approaches.

### Tool Hierarchy (strict priority)

| Priority | Tool | When to use |
|----------|------|-------------|
| 1. PRIMARY | `npx @playwright/cli@latest` via Bash | Always try first |
| 2. FALLBACK | `mcp__chrome-devtools__*` MCP tools | Only if playwright-cli unavailable |
| 3. NEVER | `mcp__claude-in-chrome__*` | Blocked — cannot capture request bodies |

### Development vs End-User

| | Development (Phases 1-8) | End-User (published CLI) |
|--|--------------------------|--------------------------|
| **Browser** | playwright-cli manages its own | playwright-cli via subprocess (auth only) |
| **Traffic capture** | `tracing-start` → browse → `tracing-stop` | N/A — CLI uses httpx |
| **Auth** | `state-save` after user logs in | `auth login` → subprocess `state-save` → parse cookies |
| **Runtime HTTP** | N/A | httpx — no browser needed |
| **Dependencies** | Node.js + npx | click, httpx, Node.js + npx (auth only) |

**The generated CLI MUST work standalone.** playwright-cli is only needed during
`auth login` — all regular commands use httpx. If the CLI requires a browser for
normal operations, it's broken.

---

## 8-Phase Pipeline

### Prerequisites

**Primary: playwright-cli (recommended)**

playwright-cli auto-launches and manages its own browser. No manual setup needed.
Just verify Node.js and npx are available:
```bash
npx @playwright/cli@latest --version
```
If this fails, install Node.js from https://nodejs.org/

**Fallback: Chrome Debug Profile (if playwright-cli unavailable)**

If playwright-cli cannot be used, fall back to chrome-devtools-mcp:
1. Launch: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/launch-chrome-debug.sh <url>`
2. Log into the target web app (cookies persist across restarts)
3. Agent uses `mcp__chrome-devtools__*` tools instead

---

### Phase 1 — Record (Traffic Capture)

**Goal:** Capture comprehensive HTTP traffic from the target web app.

**Primary method: playwright-cli**

```bash
# 1. Open browser with named session
npx @playwright/cli@latest -s=<app> open <url> --headed --persistent

# 2. If login required — ask user to log in, wait for confirmation

# 3. Start trace recording (captures ALL network with full bodies)
npx @playwright/cli@latest -s=<app> tracing-start

# 4. Systematically explore the app:
npx @playwright/cli@latest -s=<app> snapshot          # Get element refs (YAML)
npx @playwright/cli@latest -s=<app> click e15          # Navigate
npx @playwright/cli@latest -s=<app> fill e8 "search"   # Fill forms
npx @playwright/cli@latest -s=<app> screenshot          # Visual check (file on disk)

# 5. Stop trace — saves .network + resources/ with full request/response bodies
npx @playwright/cli@latest -s=<app> tracing-stop

# 6. Save auth state for reuse
npx @playwright/cli@latest -s=<app> state-save <app>-auth.json

# 7. Parse trace → raw-traffic.json
python ${CLAUDE_PLUGIN_ROOT}/scripts/parse-trace.py \
  .playwright-cli/traces/ \
  --output <app>/traffic-capture/raw-traffic.json

# 8. Close browser
npx @playwright/cli@latest -s=<app> close
```

**Fallback method: chrome-devtools-mcp**

If playwright-cli is not available, tell the user:
"playwright-cli is not available. Falling back to chrome-devtools MCP.
Please launch debug Chrome: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/launch-chrome-debug.sh <url>`"

Then use `mcp__chrome-devtools__*` tools:
- `navigate_page` with the target URL
- `list_network_requests` to capture traffic
- `get_network_request(id)` for full request/response details
- Save to `<app>/traffic-capture/raw-traffic.json`

**Critical rules (both methods):**
- Filter OUT: static assets (.js, .css, .png, fonts, analytics, CDN)
- Filter IN: API calls (JSON responses, `/api/`, GraphQL, RPC endpoints)
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
4. **Identify RPC protocol type** — classify the API transport:

   | Protocol | Detection Signal | Client Pattern |
   |----------|-----------------|----------------|
   | REST | Resource URLs (`/api/v1/boards/:id`), standard HTTP methods | `client.py` with method-per-endpoint |
   | GraphQL | Single `/graphql` endpoint, `query`/`mutation` in body | `client.py` with query templates |
   | gRPC-Web | `application/grpc-web` content type, binary payloads | Proto-based client |
   | Google batchexecute | `batchexecute` in URL, `f.req=` body, `)]}'\n` prefix | `rpc/` subpackage (see `references/google-batchexecute.md`) |
   | Custom RPC | Single endpoint, method name in body, proprietary encoding | Custom codec module |

   This determines client architecture in Phase 4 — REST uses simple `client.py`,
   non-REST protocols need a dedicated `rpc/` subpackage with encoder/decoder/types.
5. Detect data model:
   - Entity types (boards, items, users, projects...)
   - Relationships (board has many items, item belongs to board)
   - ID formats (UUID, numeric, slug)
6. Detect auth pattern:
   - Cookie-based sessions
   - Bearer/JWT tokens
   - OAuth refresh flow
   - API key headers
   - Browser-delegated auth: tokens embedded in page JavaScript (e.g., `WIZ_global_data`),
     not in HTTP headers. Requires CDP for initial cookies, HTTP for token extraction.
     See `references/auth-strategies.md` "Browser-Delegated Auth" section.
7. Write `<APP>.md` — software-specific SOP document

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
            │   ├── rpc/              # Optional: for non-REST protocols
            │   │   ├── __init__.py
            │   │   ├── types.py      # Method enum, URL constants
            │   │   ├── encoder.py    # Request encoding
            │   │   └── decoder.py    # Response decoding
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
- `auth.py` — handles token storage, refresh, expiry. MUST support 2 login methods:
  1. **`auth login`** (primary) — uses playwright-cli via subprocess to open browser.
     User logs in manually, `state-save` captures cookies + localStorage.
     No Playwright Python needed — just `npx @playwright/cli`.
     ```python
     # auth.py — playwright-cli login
     def login(app_url, auth_path):
         import subprocess
         session = "auth-login"
         subprocess.run(["npx", "@playwright/cli@latest", "-s=" + session,
                         "open", app_url, "--headed", "--persistent"], check=True)
         input("Log in, then press ENTER...")
         subprocess.run(["npx", "@playwright/cli@latest", "-s=" + session,
                         "state-save", str(auth_path)], check=True)
         subprocess.run(["npx", "@playwright/cli@latest", "-s=" + session,
                         "close"], check=True)
         state = json.loads(auth_path.read_text())
         cookies = {c["name"]: c["value"] for c in state.get("cookies", [])}
         save_cookies(cookies)
     ```
  2. **`auth login --cookies-json <file>`** (manual fallback) — import from JSON file.
  - Store cookies at `~/.config/cli-web-<app>/auth.json` with chmod 600
  - No more `--from-chrome` or `--from-browser` flags
  - `setup.py` should NOT include Playwright Python — only `click`, `httpx`
- **Anti-bot resilient client construction** (when detected in Phase 2):
  - Extract session tokens via CDP first (cookies), then HTTP GET + HTML parsing (CSRF, session IDs)
  - **Never hardcode** build labels (`bl`), session IDs (`f.sid`), or CSRF tokens — extract dynamically at runtime
  - Replicate same-origin headers captured during Phase 1 traffic (e.g., `x-same-domain: 1` for Google apps)
  - Implement auto-retry on 401/403: re-fetch homepage → re-extract tokens → retry once
  - See `references/google-batchexecute.md` for the complete Google pattern
- **RPC codec subpackage** (for non-REST protocols like batchexecute):
  When the API uses a non-REST protocol, add `core/rpc/` with:
  - `types.py` — method ID enum, URL constants
  - `encoder.py` — request encoding (protocol-specific format)
  - `decoder.py` — response decoding (strip prefix, parse chunks, extract results)
  The `client.py` still exists but delegates encoding/decoding to `rpc/`.
- Every command: `--json` flag, proper error messages
- Entry point: `cli-web-<app>` via setup.py console_scripts
- Namespace: `cli_web.*`
- Copy `repl_skin.py` from plugin for consistent REPL experience

**Parallel implementation (dispatch independent modules as subagents):**

When the CLI has 3+ command groups (e.g., notebooks, sources, chat, artifacts),
dispatch parallel subagents — one per command module. Each agent gets:
- The `<APP>.md` API spec for its resource
- The `client.py` and `auth.py` interfaces it depends on
- Clear scope: "Implement `commands/notebooks.py` with list, get, create, delete"

Parallelization opportunities in Phase 4:

| Independent from each other | Dispatch in parallel |
|----------------------------|---------------------|
| `commands/notebooks.py`, `commands/sources.py`, `commands/chat.py` | Yes — each command file only depends on `client.py` |
| `rpc/encoder.py` and `rpc/decoder.py` | Yes — encoder doesn't depend on decoder |
| `auth.py` and `models.py` | Yes — no shared logic |
| `client.py` and `commands/*` | **No** — commands depend on client |
| `<app>_cli.py` (entry point) | **Last** — imports all commands, write after they're done |

**Implementation order:**
1. First (sequential): `core/client.py`, `core/auth.py`, `core/session.py`, `core/models.py`
   — these are the foundation that everything else imports
2. Then (parallel subagents): all `commands/*.py` files + `rpc/encoder.py` + `rpc/decoder.py`
   — each is independent once the core exists
3. Last (sequential): `<app>_cli.py`, `__main__.py`, `setup.py`, copy `repl_skin.py`
   — these wire everything together

Example dispatch for a Google app with 4 command groups:
```
# After core/ modules are written:
Agent 1 → "Implement commands/notebooks.py (list, get, create, delete, rename)"
Agent 2 → "Implement commands/sources.py (add-url, add-pdf, add-text, list, delete)"
Agent 3 → "Implement commands/chat.py (ask, history)"
Agent 4 → "Implement commands/artifacts.py (list, create, get)"
# All 4 run concurrently, then integrate
```

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

**Parallel test writing (dispatch independent test files as subagents):**

Like Phase 4, test files are independent and can be written in parallel:

| Test file | Scope | Independent? |
|-----------|-------|-------------|
| `test_core.py` — client tests | Mock HTTP, test `client.py` | Yes |
| `test_core.py` — auth tests | Mock filesystem, test `auth.py` | Yes |
| `test_core.py` — RPC codec tests | Test encoder/decoder with fixtures | Yes |
| `test_e2e.py` — fixture replay | Replay captured responses | Depends on fixtures existing |
| `test_e2e.py` — live tests | Real API calls | Depends on auth working |
| `test_e2e.py` — subprocess tests | `_resolve_cli()` | Depends on `pip install -e .` |

Dispatch strategy:
```
Agent 1 → "Write unit tests for core/client.py and core/auth.py in test_core.py"
Agent 2 → "Write RPC encoder/decoder unit tests (if applicable) in test_core.py"
Agent 3 → "Write E2E fixture replay tests and live CRUD tests in test_e2e.py"
# After all return, integrate into final test files and run
```

Each agent receives: the module it's testing, the TEST.md plan (from Phase 5),
and sample API responses from `tests/fixtures/`. Agents must NOT depend on each
other's output.

**Test layers:**

| Layer | What it tests | Example |
|-------|--------------|---------|
| Unit tests | Core functions with mocked HTTP | `test_core.py` — CRUD ops, auth, parsing |
| E2E tests (mocked) | Full command flow with recorded responses | Replay captured traffic |
| E2E tests (live) | Real API calls against running service | Create/read/update/delete cycle |
| CLI subprocess | Installed command via `subprocess.run` | `cli-web-<app> --json boards list` |

**CRITICAL — Auth must be configured BEFORE running any E2E or subprocess tests:**

Before writing or running any live test, you MUST ensure authentication is working:
1. Ensure Chrome is connected via autoConnect and user is logged in
2. Run `cli-web-<app> auth login --from-chrome` to extract cookies
3. Run `cli-web-<app> auth status` — must show "All required cookies present" AND
   live validation must succeed
4. If auth status shows a failure (401, missing cookies), STOP and fix auth first.
   Do NOT write tests that catch auth errors and report "auth not configured" — that
   defeats the entire purpose. The CLI talks to a REAL service. Tests must talk to
   the REAL service too.

This is the web equivalent of CLI-Anything's rule "the real software MUST be installed."
In our case: **real auth MUST be configured and verified working before any E2E test.**

**Testing rules:**
- Use `unittest.mock.patch` for HTTP in unit tests
- Store captured responses in `tests/fixtures/` for replay
- E2E live tests require auth — **FAIL (not skip, not catch, not "auth not configured")**
- If a test cannot authenticate, it must `pytest.fail("Auth not configured. Run: cli-web-<app> auth login")`
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
1. **Verify auth is working FIRST:**
   ```bash
   cli-web-<app> auth login --from-chrome     # extract cookies from connected Chrome
   cli-web-<app> auth status                  # must show live validation: OK
   ```
   If auth status fails, fix it before proceeding. Do NOT run tests without working auth.
2. Run full test suite: `python3 -m pytest cli_web/<app>/tests/ -v --tb=short`
3. Run subprocess tests: `CLI_WEB_FORCE_INSTALLED=1 python3 -m pytest cli_web/<app>/tests/ -v -s -k subprocess`
4. **ALL tests must pass.** If E2E tests fail with auth errors, go back to step 1.
   Do NOT record "auth not configured" as a test result — that means auth is broken.
5. **Append** Part 2 to existing `TEST.md`:
   - Full `pytest -v --tb=no` output showing ALL tests passing
   - Summary: total tests, pass rate, execution date
   - Any gaps with explanation
6. Include example CLI usage in README.md

### Phase 8 — Publish and Verify (Install to PATH)

**Goal:** Make CLI installable AND verify it works end-to-end as a real user would use it.

**Process:**
1. Create `setup.py` with:
   - `find_namespace_packages` for `cli_web.*`
   - `console_scripts` entry point: `cli-web-<app>`
   - Dependencies: `click>=8.0`, `httpx`
   - Optional: `extras_require={"browser": ["playwright>=1.40.0"]}`
2. Install: `pip install -e .`
3. Verify: `which cli-web-<app>`
4. Test help: `cli-web-<app> --help`

**End-User Smoke Test (MANDATORY — do NOT skip this):**

This is the most critical verification step. The agent MUST simulate what a real
end user would do after `pip install cli-web-<app>`. If this fails, the pipeline
is NOT complete — go back and fix the issue.

5. **Authenticate using Playwright (NOT --from-chrome):**
   ```bash
   cli-web-<app> auth login
   ```
   This MUST use Playwright — it opens the user's regular browser (not the debug
   Chrome). If this fails, the CLI is broken for end users. Do NOT fall back to
   `--from-chrome` for the smoke test — that only proves it works with the debug
   Chrome, which end users won't have.
6. **Verify auth status shows LIVE VALIDATION OK:**
   ```bash
   cli-web-<app> auth status
   ```
   Must show: cookies present, tokens valid. If it shows "expired", "redirect",
   or any auth failure — STOP. Fix auth before proceeding.

7. **Run a real API call and verify the response:**
   ```bash
   cli-web-<app> --json <first-resource> list
   ```
   This must return real data from the live API — NOT an error, NOT empty,
   NOT "auth not configured". Verify the JSON response contains expected fields.

8. **Run a CRUD smoke test if the app supports it:**
   ```bash
   cli-web-<app> --json <resource> create --name "smoke-test-$(date +%s)"
   cli-web-<app> --json <resource> list   # verify the created item appears
   cli-web-<app> --json <resource> delete --id <id-from-create>
   ```

9. **Only after steps 5-8 pass, declare the pipeline complete.**

**The pipeline is NOT done until:**
- `auth login` works with **Playwright** (the end-user method, NOT --from-chrome)
- `auth status` shows valid
- At least one real API call returns real data
- The CLI works standalone — no debug Chrome, no port 9222, no MCP

**Why namespace packages:**
- Multiple `cli-web-*` CLIs coexist in the same Python environment without conflicts
- `cli_web/` has NO `__init__.py` — this is the rule that enables it
- Use `find_namespace_packages(include=["cli_web.*"])` — NOT `find_packages`

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

### Lesson 7: Content Generation Requires Download
Many web apps generate content asynchronously (Suno generates songs, NotebookLM
generates audio overviews, Canva generates designs). The CLI MUST handle the full
lifecycle: trigger generation → poll for completion → download the result.

Pattern:
1. **Trigger:** Send the create/generate request → get a job/task ID
2. **Poll:** Check status endpoint repeatedly with backoff until `status == "complete"`
3. **Download:** Fetch the binary content (audio, image, video, PDF) from the result URL
4. **Save:** Write to local file with correct extension, print path and size

The CLI command should handle all 4 steps in one call:
```
cli-web-suno generate --prompt "jazz piano" --output song.mp3
# → Triggers generation
# → Polls until complete (shows progress)
# → Downloads MP3 to song.mp3
# → Prints: Saved song.mp3 (4.2 MB, 3:24)
```

If the result URL requires authentication (signed URLs, cookies), the download
must use the same auth session as the API calls. Some apps serve media from CDN
domains (e.g., `cdn.suno.com`) — capture these domains during Phase 1 and include
them in the cookie domain filter.

### Lesson 8: CAPTCHAs Require Human Intervention
Web apps may present CAPTCHAs at any time — during login, after repeated requests,
or when they detect automated access. The CLI MUST handle this gracefully:

1. **Detect:** Check for CAPTCHA signals in responses (403 with challenge page,
   specific error codes, redirect to challenge URL, response body containing
   "captcha", "challenge", "verify you're human")
2. **Pause:** Do NOT retry. Do NOT skip. Do NOT crash.
3. **Guide:** Tell the user exactly what to do:
   ```
   CAPTCHA detected. Please solve it manually:
   1. Open your browser to: <url>
   2. Complete the CAPTCHA challenge
   3. Press ENTER here when done
   ```
4. **Resume:** After user confirms, retry the failed request

This applies to ALL phases — traffic capture, auth, API calls, and testing.
During Phase 1 recording, if a CAPTCHA appears in the browser, pause and ask
the user to solve it before continuing. During CLI usage, catch CAPTCHA
responses and prompt the user.

## Rules

- **Auth credentials MUST be stored securely.** `chmod 600 auth.json`. Never hardcode
  tokens in source. If auth file missing, CLI errors with clear instructions — never
  falls back to unauthenticated requests.
- **Tests MUST fail (not skip) when auth is missing.** Tests that skip on missing auth
  give false confidence. The CLI is useless without a live account. Before running any
  E2E test, run `cli-web-<app> auth login` then `auth status` to verify.
  Tests that output "auth not configured" are BROKEN — fix auth first, then test.
  This is the web equivalent of "the real software MUST be installed."
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
- **Content generation commands MUST download the result.** If the app generates
  content (audio, images, video, documents), the CLI must handle the full lifecycle:
  trigger → poll → download → save. Don't just return a URL — download the file.
  Support `--output <path>` flag for specifying where to save.
- **CAPTCHAs MUST pause and prompt, never crash or skip.** If a CAPTCHA is detected
  in any response (403 challenge, "verify you're human", challenge redirect), stop
  and tell the user to solve it in their browser. Wait for confirmation, then retry.

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
