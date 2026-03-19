---
name: methodology
description: >
  Analyze captured HTTP traffic, design CLI architecture, and implement the Python
  CLI package. Covers Phases 2-3 of the pipeline: parse raw-traffic.json, identify
  protocol type, map endpoints, design Click command groups, implement with parallel
  subagents. Use when the user asks to "create a CLI for a website", "generate API
  wrapper", "reverse engineer web API", "analyze traffic", "design CLI", "implement CLI",
  "build CLI from network traffic", or discusses turning closed-source web applications
  into agent-controllable command-line interfaces.
version: 0.2.0
---

# CLI-Anything-Web Methodology (Phases 2-3)

Analyze captured traffic, design the CLI command structure, and implement the
complete Python CLI package. This skill owns the core transformation from raw
HTTP traffic to a production-ready CLI.

---

## Prerequisites (Hard Gate)

Do NOT start unless:
- [ ] `raw-traffic.json` exists (with WRITE operations, or read-only GET-only traffic)
- [ ] Auth state was captured during Phase 1 (if the site requires auth)

If raw-traffic.json is missing or has no WRITE operations, invoke the
`capture` skill first.

**Exception for read-only sites:** If the site is genuinely read-only (search engine,
dashboard, analytics viewer with no create/update/delete), the trace may contain only
GET requests. In this case, note "read-only site — no write operations" in `<APP>.md`
and proceed. The generated CLI will have read-only commands (list, get, search) but
no create/update/delete commands. This is valid.

**No-auth sites:** If the target site requires no authentication (public API,
no login needed), the "Auth state captured" prerequisite does not apply. Note
"no-auth site" in `<APP>.md` and proceed.

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
   | Public REST API | Documented `/api/` endpoints, OpenAPI spec, JSON responses | Standard `client.py` with httpx |
   | Plain HTML (no framework) | No SPA root, no framework globals, data in `<table>`/`<div>` | `client.py` with httpx + BeautifulSoup4 |

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
   - No auth / public access: fully public API, no login required. CLI may
     optionally support API key auth for write operations (e.g., dev.to).

7. Write `<APP>.md` -- software-specific SOP document

**Output:** `<APP>.md` with API map, data model, auth scheme.

**References:** `traffic-patterns.md`, `google-batchexecute.md`, `ssr-patterns.md`

---

## Phase 3: Implement (Code Generation)

### Design Before You Code

Before writing any code, note the command structure in `<APP>.md` (10 minutes max):

- Map each API endpoint group to a Click command group:
  - `/api/v1/boards/*` → `boards` command group
  - `/api/v1/items/*` → `items` command group
- Map CRUD operations to subcommands (GET list → `list`, GET single → `get`,
  POST → `create`, PUT/PATCH → `update`, DELETE → `delete`)
- Note auth design: `auth login`, `auth status`, `auth refresh`; credentials at
  `~/.config/cli-web-<app>/auth.json`
- Note REPL design: bare command enters REPL, branded banner via `repl_skin.py`

**Goal:** Generate the complete Python CLI package.

### Package Structure

See HARNESS.md "Generated CLI Structure" for the complete package template.
Key points: `cli_web/` namespace (NO `__init__.py`), `<app>/` sub-package (HAS `__init__.py`),
`core/`, `commands/`, `utils/`, `tests/` directories.

### Implementation Rules

- **`exceptions.py`** -- domain-specific exception hierarchy (MUST implement first):
  ```python
  # core/exceptions.py — generated for every CLI
  class AppError(Exception):
      """Base for all <app> CLI errors."""

  class AuthError(AppError):
      """Auth failed — expired cookies, invalid tokens."""
      def __init__(self, message: str, recoverable: bool = True):
          self.recoverable = recoverable
          super().__init__(message)

  class RateLimitError(AppError):
      """429 — retry with backoff."""
      def __init__(self, message: str, retry_after: float | None = None):
          self.retry_after = retry_after
          super().__init__(message)

  class NetworkError(AppError):
      """Connection/DNS/timeout errors."""

  class ServerError(AppError):
      """5xx responses."""
      def __init__(self, message: str, status_code: int = 500):
          self.status_code = status_code
          super().__init__(message)

  class NotFoundError(AppError):
      """404 — resource not found."""
  ```
  Extend with domain-specific errors as needed. All other modules import from here.
  See `references/exception-hierarchy-example.py` for a complete example.

- **`client.py`** -- HTTP client with exception mapping and auth retry:
  - Centralized auth header/cookie injection
  - Automatic JSON parsing with response body verification
  - **Status code → exception mapping**: 401/403→`AuthError`, 404→`NotFoundError`, 429→`RateLimitError`, 5xx→`ServerError`
  - **Auth retry**: On `AuthError(recoverable=True)`, refresh tokens and retry once
  - Exponential backoff for rate limits (see `references/polling-backoff-example.py`)
  - For apps with 3+ resource types: split into namespaced sub-clients (`client.notebooks.list()`, `client.sources.add()`)
  - See `references/client-architecture-example.py` for the full pattern

- **`auth.py`** -- handles token storage, refresh, expiry. Implementation depends on auth type:

  **For no-auth or API-key sites:** `auth.py` is optional. If the site uses API key auth,
  implement a simple `login(api_key)` / `inject_auth(headers)` module — no browser needed.

  **For browser-delegated auth (Google, Microsoft, etc.):** Full playwright-cli login flow
  with cookie domain priority for international users.

  See `references/auth-strategies.md` for complete implementation patterns including:
  - Browser login with `Popen` (not `subprocess.run` — critical fix)
  - Cookie domain priority (`.google.com` over regional domains)
  - Dual format handling (list vs dict cookies)
  - API key auth (simple header injection)
  - Environment variable auth for CI/CD
  - Context commands (`use <id>`, `status`) for stateful apps

  Key rules:
  - Store cookies at `~/.config/cli-web-<app>/auth.json` with chmod 600
  - `setup.py` should NOT include Playwright Python — only `click`, `httpx`

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

- **Progress feedback** -- Use `rich` spinners for operations >2s when not in `--json` mode:
  ```python
  from rich.console import Console
  console = Console()
  with console.status("Generating...") as spinner:
      result = poll_until_complete(check_fn)
  ```
  Add `rich>=13.0` to `setup.py` dependencies.

- **JSON error output** -- When `--json` is active, errors MUST also be JSON — agents
  parsing stdout will crash on unexpected plain-text error messages:
  ```python
  # utils/output.py
  def json_error(code: str, message: str, **extra) -> str:
      return json.dumps({"error": True, "code": code, "message": message, **extra})

  # In commands: catch exceptions, output json_error()
  ```
  Standard error codes: `AUTH_EXPIRED`, `RATE_LIMITED`, `NOT_FOUND`, `SERVER_ERROR`, `NETWORK_ERROR`

- Every command: `--json` flag, proper error messages

- **All commands MUST use `handle_errors()` context manager** — not manual try/except,
  because scattered try/except blocks produce inconsistent exit codes and miss JSON error formatting.
  This centralizes error handling, exit codes (1=user, 2=system, 130=interrupt),
  and JSON error output:
  ```python
  @notebooks.command("list")
  @click.option("--json", "use_json", is_flag=True)
  def list_notebooks(use_json):
      with handle_errors(json_mode=use_json):
          client = AppClient()
          nbs = client.list_notebooks()
  ```

- **Generation commands MUST support `--wait`, `--retry`, `--output`** — without these,
  agents cannot script end-to-end workflows (generate, wait for result, save to disk):
  ```python
  @artifacts.command("generate")
  @click.option("--wait", is_flag=True, help="Wait for completion.")
  @click.option("--retry", type=int, default=3, help="Max retries on rate limit.")
  @click.option("--output", "-o", type=click.Path(), help="Save to file.")
  def generate(notebook, artifact_type, wait, retry, output, use_json):
      with handle_errors(json_mode=use_json):
          nb_id = require_notebook(notebook)
          result = retry_on_rate_limit(lambda: client.generate(...), max_retries=retry)
  ```

- **Windows UTF-8 fix** — Add at the top of `<app>_cli.py` before any imports that print:
  ```python
  import sys
  if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
      try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
      except AttributeError: pass
  ```
- **HTML table parsers MUST extract ALL visible columns** — not just name/price,
  because missing fields in `--json` output make the CLI useless for filtering and analysis.
  If the site shows version, club, nation, stats, skills, weak foot — parse all of them.
  Empty fields in `--json` output = incomplete parser.
- Entry point: `cli-web-<app>` via setup.py console_scripts
- Namespace: `cli_web.*`
- Copy `repl_skin.py` from plugin for consistent REPL experience
- **`utils/helpers.py`** -- shared CLI helpers (generate for every CLI):
  - `resolve_partial_id(partial, items)` — prefix-match UUIDs for get/rename/delete
  - `handle_errors(json_mode)` — context manager replacing try/except in all commands
  - `require_notebook(notebook_arg)` — gets notebook ID from arg or persistent context
  - `sanitize_filename(name)` — safe filenames from artifact titles
  - `poll_until_complete(check_fn)` — exponential backoff polling
  - `get_context_value(key)` / `set_context_value(key, value)` — persistent context.json
  See `references/helpers-module-example.py` for the complete module.

> **Not all helpers apply to every CLI.** Include only what the CLI uses:
> `handle_errors` and `print_json` are always needed. `resolve_partial_id` only
> for UUID-based apps. `require_notebook`/context helpers only for apps with
> persistent context. `poll_until_complete` only for generation/async operations.

### REPL Implementation Rules (Critical)

These three bugs appear in almost every generated REPL. Get them right the first time:

**1. Use `shlex.split()`, never `line.split()`**

```python
# ✓ Correct — handles quoted args: players search "messi" -> ['players', 'search', 'messi']
import shlex
args = shlex.split(line)

# ✗ Wrong — produces: ['players', 'search', '"messi"'] — quotes become part of the value
args = line.split()
```

**2. Never pass `**ctx.params` to `cli.main()` in REPL dispatch**

```python
# ✓ Correct — preserve --json flag by prepending to args
repl_args = ["--json"] + args if ctx.obj.get("json") else args
cli.main(args=repl_args, standalone_mode=False)

# ✗ Wrong — ctx.params = {"json_mode": False} gets passed to Context.__init__()
# which doesn't accept it → TypeError: Context.__init__() got an unexpected
# keyword argument 'json_mode'
cli.main(args=args, standalone_mode=False, **ctx.params)
```

**3. Keep `_print_repl_help()` in sync with the actual command surface**

The `_print_repl_help()` function in `<app>_cli.py` is the user's first discovery surface — it's what they see when they type `help` in the REPL. It must mirror the real commands, including all key options. A REPL that shows outdated or incomplete help is confusing and makes the CLI feel broken.

```python
# ✓ Correct — help lists actual options users can pass
def _print_repl_help():
    _skin.info("Available commands:")
    print("  players list [OPTIONS]")
    print("    --position <GK|ST|CM|...>    Filter by position")
    print("    --rating-min N --rating-max N  Rating range")
    print("    --cheapest                   Sort cheapest first")

# ✗ Wrong — stale help doesn't mention new --position, --rating-min, etc.
def _print_repl_help():
    print("  players list [--min-price N]   List players with filters")
```

Rule: **every time you add options to a command, update `_print_repl_help()` in the same commit**.

---

**4. Use `@click.argument` for positional REPL params, not `@click.option("--x", required=True)`**

REPL commands show `players search <query>` in help. If `query` is a `--query` option,
users typing `players search messi` get "Error: Missing option '--query'".
Use positional arguments for natural command-line style:

```python
# ✓ Correct — users type: players search messi  OR  players get 21610
@players.command()
@click.argument("query")
def search(query): ...

@players.command()
@click.argument("player_id", type=int)
def get(player_id): ...

# ✗ Wrong — users get an error unless they type: players search --query messi
@players.command()
@click.option("--query", required=True)
def search(query): ...
```

Rule of thumb: if a command takes a single required value that would be a positional arg
in a shell command (`git checkout main`, `grep pattern`), use `@click.argument`.
Use `@click.option` only for optional or named parameters (`--rating-min`, `--platform`).

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

1. **First (sequential):** `core/exceptions.py`, `core/client.py`, `core/auth.py` (if auth required),
   `core/session.py` (if stateful context needed), `core/models.py`
   -- these are the foundation that everything else imports
2. **Then (parallel subagents):** all `commands/*.py` files + `rpc/encoder.py` + `rpc/decoder.py`
   -- each is independent once the core exists
3. **Last (sequential):** `utils/helpers.py`, `<app>_cli.py`, `__main__.py`, `setup.py`, copy `repl_skin.py`
   -- these wire everything together

> **Start tests early:** Once `core/client.py`, `core/auth.py`, and `core/models.py` are
> implemented, spawn a test-writing subagent immediately — don't wait for all command modules
> to finish. The unit tests for core modules are independent of the command implementations.

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

When implementation is complete, invoke the `testing` skill
to plan and write tests.

Do NOT skip testing -- every CLI must have comprehensive tests before publishing.

---

## Companion Skills

| Skill | When it activates |
|-------|------------------|
| `capture` | Phase 1 -- traffic recording (prerequisite for this skill) |
| `testing` | Phase 3 -- test writing, documentation |
| `standards` | Phase 4 -- publish, verify, smoke test |
| `auto-optimize` | Meta -- autonomous skill optimization |

---

## Integration

| Relationship | Skill |
|-------------|-------|
| **Preceded by** | `capture` (Phase 1) |
| **Followed by** | `testing` (Phase 3) |
| **References** | `traffic-patterns.md`, `auth-strategies.md`, `google-batchexecute.md`, `ssr-patterns.md`, `exception-hierarchy-example.py`, `client-architecture-example.py`, `polling-backoff-example.py`, `rich-output-example.py` |

---

## Reference Files

- **`references/traffic-patterns.md`** -- Common API patterns (REST, GraphQL, RPC)
- **`references/auth-strategies.md`** -- Auth implementation strategies
- **`references/google-batchexecute.md`** -- Google batchexecute RPC protocol spec
- **`references/ssr-patterns.md`** -- SSR framework patterns and data extraction strategies
- **`references/exception-hierarchy-example.py`** -- Complete exception hierarchy with HTTP status mapping
- **`references/client-architecture-example.py`** -- Namespaced sub-client pattern with auth retry
- **`references/polling-backoff-example.py`** -- Exponential backoff polling and rate-limit retry
- **`references/rich-output-example.py`** -- Rich progress bars, JSON error responses, table formatting
