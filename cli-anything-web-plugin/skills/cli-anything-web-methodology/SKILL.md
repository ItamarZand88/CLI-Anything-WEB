---
name: cli-anything-web-methodology
description: >
  Analyze captured HTTP traffic, design CLI architecture, and implement the Python
  CLI package. Covers Phases 2-4 of the pipeline: parse raw-traffic.json, identify
  protocol type, map endpoints, design Click command groups, implement with parallel
  subagents. Use when the user asks to "create a CLI for a website", "generate API
  wrapper", "reverse engineer web API", "analyze traffic", "design CLI", "implement CLI",
  "build CLI from network traffic", or discusses turning closed-source web applications
  into agent-controllable command-line interfaces.
version: 0.1.0
---

# CLI-Anything-Web Methodology (Phases 2-4)

Analyze captured traffic, design the CLI command structure, and implement the
complete Python CLI package. This skill owns the core transformation from raw
HTTP traffic to a production-ready CLI.

---

## Prerequisites (Hard Gate)

Do NOT start unless:
- [ ] `raw-traffic.json` exists with WRITE operations (POST/PUT/PATCH/DELETE)
- [ ] Auth state was captured during Phase 1

If raw-traffic.json is missing or has no WRITE operations, invoke the
`cli-anything-web-capture` skill first.

---

## Phase 2: Analyze (API Discovery)

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

4. **Identify RPC protocol type** -- classify the API transport:

   | Protocol | Detection Signal | Client Pattern |
   |----------|-----------------|----------------|
   | REST | Resource URLs (`/api/v1/boards/:id`), standard HTTP methods | `client.py` with method-per-endpoint |
   | GraphQL | Single `/graphql` endpoint, `query`/`mutation` in body | `client.py` with query templates |
   | gRPC-Web | `application/grpc-web` content type, binary payloads | Proto-based client |
   | Google batchexecute | `batchexecute` in URL, `f.req=` body, `)]}'\n` prefix | `rpc/` subpackage (see `references/google-batchexecute.md`) |
   | Custom RPC | Single endpoint, method name in body, proprietary encoding | Custom codec module |

   This determines client architecture in Phase 4 -- REST uses simple `client.py`,
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

7. Write `<APP>.md` -- software-specific SOP document

**Output:** `<APP>.md` with API map, data model, auth scheme.

**References:** `traffic-patterns.md`, `google-batchexecute.md`, `ssr-patterns.md`

---

## Phase 3: Design (CLI Architecture)

**Goal:** Design the CLI command structure.

**Process:**

1. Map each API endpoint group to a Click command group:
   - `/api/v1/boards/*` -> `boards` command group
   - `/api/v1/items/*` -> `items` command group

2. Map CRUD operations to subcommands:
   - GET (list) -> `boards list`
   - GET (single) -> `boards get --id <id>`
   - POST -> `boards create --name <name>`
   - PUT/PATCH -> `boards update --id <id> --name <name>`
   - DELETE -> `boards delete --id <id>`

3. Design auth management:
   - `auth login` -- interactive login flow
   - `auth status` -- show current session
   - `auth refresh` -- refresh token if applicable
   - Store credentials in `~/.config/cli-web-<app>/auth.json`

4. Design session state:
   - Current workspace/project context
   - Undo/redo stack for mutating operations
   - Output format preferences

5. Design REPL commands:
   - Bare command -> enters REPL
   - Branded banner via `repl_skin.py`
   - Context-aware prompt showing current entity

**Output:** Architecture spec in `<APP>.md`.

**References:** `traffic-patterns.md`

---

## Phase 4: Implement (Code Generation)

**Goal:** Generate the complete Python CLI package.

### Package Structure

```
<app>/
+-- agent-harness/
    +-- <APP>.md                    # Software-specific SOP
    +-- setup.py                    # PyPI config (find_namespace_packages)
    +-- cli_web/                    # Namespace package (NO __init__.py)
        +-- <app>/                  # Sub-package (HAS __init__.py)
            +-- __init__.py
            +-- __main__.py         # python -m cli_web.<app>
            +-- <app>_cli.py        # Main CLI entry point
            +-- core/
            |   +-- __init__.py
            |   +-- client.py       # HTTP client (requests/httpx)
            |   +-- auth.py         # Auth management
            |   +-- session.py      # State + undo/redo
            |   +-- models.py       # Response models
            |   +-- rpc/              # Optional: for non-REST protocols
            |       +-- __init__.py
            |       +-- types.py      # Method enum, URL constants
            |       +-- encoder.py    # Request encoding
            |       +-- decoder.py    # Response decoding
            +-- commands/           # Click command groups
            |   +-- __init__.py
            |   +-- <resource>.py   # One file per API resource
            +-- utils/
            |   +-- __init__.py
            |   +-- repl_skin.py    # Unified REPL (from plugin)
            |   +-- output.py       # JSON/table formatting
            |   +-- config.py       # Config file management
            +-- tests/
                +-- __init__.py
                +-- TEST.md         # Test plan + results
                +-- test_core.py    # Unit tests (mocked HTTP)
                +-- test_e2e.py     # E2E tests (live API)
```

### Implementation Rules

- **`client.py`** -- thin HTTP wrapper using `httpx` or `requests`
  - Centralized auth header injection
  - Automatic JSON parsing
  - Error handling with status code mapping
  - Rate limit respect (exponential backoff)

- **`auth.py`** -- handles token storage, refresh, expiry. MUST support 2 login methods:
  1. **`auth login`** (primary) -- uses playwright-cli via subprocess to open browser.
     User logs in manually, `state-save` captures cookies + localStorage.
     No Playwright Python needed -- just `npx @playwright/cli`.
     ```python
     # auth.py -- playwright-cli login
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
  2. **`auth login --cookies-json <file>`** (manual fallback) -- import from JSON file.
  - Store cookies at `~/.config/cli-web-<app>/auth.json` with chmod 600
  - No more `--from-chrome` or `--from-browser` flags
  - `setup.py` should NOT include Playwright Python -- only `click`, `httpx`

- **Anti-bot resilient client construction** (when detected in Phase 2):
  - Extract session tokens via CDP first (cookies), then HTTP GET + HTML parsing (CSRF, session IDs)
  - **Never hardcode** build labels (`bl`), session IDs (`f.sid`), or CSRF tokens -- extract dynamically at runtime
  - Replicate same-origin headers captured during Phase 1 traffic (e.g., `x-same-domain: 1` for Google apps)
  - Implement auto-retry on 401/403: re-fetch homepage -> re-extract tokens -> retry once
  - See `references/google-batchexecute.md` for the complete Google pattern

- **RPC codec subpackage** (for non-REST protocols like batchexecute):
  When the API uses a non-REST protocol, add `core/rpc/` with:
  - `types.py` -- method ID enum, URL constants
  - `encoder.py` -- request encoding (protocol-specific format)
  - `decoder.py` -- response decoding (strip prefix, parse chunks, extract results)
  The `client.py` still exists but delegates encoding/decoding to `rpc/`.

- Every command: `--json` flag, proper error messages
- Entry point: `cli-web-<app>` via setup.py console_scripts
- Namespace: `cli_web.*`
- Copy `repl_skin.py` from plugin for consistent REPL experience

### Parallel Implementation (dispatch independent modules as subagents)

When the CLI has 3+ command groups (e.g., notebooks, sources, chat, artifacts),
dispatch parallel subagents -- one per command module. Each agent gets:
- The `<APP>.md` API spec for its resource
- The `client.py` and `auth.py` interfaces it depends on
- Clear scope: "Implement `commands/notebooks.py` with list, get, create, delete"

**Parallelization opportunities:**

| Independent from each other | Dispatch in parallel |
|----------------------------|---------------------|
| `commands/notebooks.py`, `commands/sources.py`, `commands/chat.py` | Yes -- each command file only depends on `client.py` |
| `rpc/encoder.py` and `rpc/decoder.py` | Yes -- encoder doesn't depend on decoder |
| `auth.py` and `models.py` | Yes -- no shared logic |
| `client.py` and `commands/*` | **No** -- commands depend on client |
| `<app>_cli.py` (entry point) | **Last** -- imports all commands, write after they're done |

**Implementation order:**

1. **First (sequential):** `core/client.py`, `core/auth.py`, `core/session.py`, `core/models.py`
   -- these are the foundation that everything else imports
2. **Then (parallel subagents):** all `commands/*.py` files + `rpc/encoder.py` + `rpc/decoder.py`
   -- each is independent once the core exists
3. **Last (sequential):** `<app>_cli.py`, `__main__.py`, `setup.py`, copy `repl_skin.py`
   -- these wire everything together

Example dispatch for a Google app with 4 command groups:
```
# After core/ modules are written:
Agent 1 -> "Implement commands/notebooks.py (list, get, create, delete, rename)"
Agent 2 -> "Implement commands/sources.py (add-url, add-pdf, add-text, list, delete)"
Agent 3 -> "Implement commands/chat.py (ask, history)"
Agent 4 -> "Implement commands/artifacts.py (list, create, get)"
# All 4 run concurrently, then integrate
```

**References:** `auth-strategies.md`, `google-batchexecute.md`

---

## Next Step

When implementation is complete, invoke the `cli-anything-web-testing` skill
to plan and write tests.

Do NOT skip testing -- every CLI must have comprehensive tests before publishing.

---

## Companion Skills

| Skill | When it activates |
|-------|------------------|
| `cli-anything-web-capture` | Phase 1 -- traffic recording (prerequisite for this skill) |
| `cli-anything-web-testing` | Phases 5-7 -- test planning, writing, documentation |
| `cli-anything-web-standards` | Phase 8 -- publish, verify, smoke test |
| `auto-optimize` | Meta -- autonomous skill optimization |

---

## Reference Files

- **`references/traffic-patterns.md`** -- Common API patterns (REST, GraphQL, RPC)
- **`references/auth-strategies.md`** -- Auth implementation strategies
- **`references/google-batchexecute.md`** -- Google batchexecute RPC protocol spec
- **`references/ssr-patterns.md`** -- SSR framework patterns and data extraction strategies
