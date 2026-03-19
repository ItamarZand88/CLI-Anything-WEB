# HARNESS.md — CLI-Anything-Web Methodology

**Making Closed-Source Web Apps Agent-Native via Network Traffic Analysis**

This is the methodology overview. Each phase is implemented by a dedicated skill.
Read this file for the big picture; read the relevant skill for phase details.

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

### Error Handling Architecture

Every generated CLI MUST include `core/exceptions.py` with a domain-specific exception
hierarchy — typed exceptions enable retry logic, proper CLI exit codes, and structured
JSON error responses. See `references/exception-hierarchy-example.py` for the complete
template. Required types: `AppError` (base), `AuthError` (recoverable flag),
`RateLimitError` (retry_after), `NetworkError`, `ServerError` (status_code), `NotFoundError`.

### Exponential Backoff & Polling

Operations taking >2 seconds MUST use exponential backoff polling (2s→10s, factor 1.5,
timeout 300s) — never fixed `time.sleep()`. Generation commands also need rate-limit
retry (60s→300s backoff on 429). See `references/polling-backoff-example.py` for both
patterns.

### Progress & Output

Use `rich>=13.0` for spinners/progress bars in interactive mode. Suppress in `--json`
mode. See `references/rich-output-example.py` for patterns.

### JSON Error Response Format

When `--json` is active, errors MUST also be JSON — not plain text to stderr:

```python
# Success:
{"success": true, "data": {...}}

# Error:
{"error": true, "code": "AUTH_EXPIRED", "message": "Session expired. Run: cli-web-<app> auth login"}
{"error": true, "code": "RATE_LIMITED", "message": "Rate limited. Retry after 60s", "retry_after": 60}
{"error": true, "code": "NOT_FOUND", "message": "Notebook abc123 not found"}
```

Error codes map directly from the exception hierarchy:
`AuthError` → `AUTH_EXPIRED`, `RateLimitError` → `RATE_LIMITED`, `NotFoundError` → `NOT_FOUND`,
`ServerError` → `SERVER_ERROR`, `NetworkError` → `NETWORK_ERROR`.

---

## Tool Hierarchy (strict priority)

| Priority | Tool | When to use |
|----------|------|-------------|
| 1. PRIMARY | `npx @playwright/cli@latest` via Bash | Always try first |
| 2. FALLBACK | `mcp__chrome-devtools__*` MCP tools | Only if playwright-cli unavailable |
| 3. NEVER | `mcp__claude-in-chrome__*` | Blocked — cannot capture request bodies |

### Development vs End-User

| | Development (Phases 1-4) | End-User (published CLI) |
|--|--------------------------|--------------------------|
| **Browser** | playwright-cli manages its own | playwright-cli via subprocess (auth only) |
| **Traffic capture** | `tracing-start` → browse → `tracing-stop` | N/A — CLI uses httpx |
| **Auth** | `state-save` after user logs in | `auth login` → subprocess `state-save` → parse cookies |
| **Runtime HTTP** | N/A | httpx — no browser needed |
| **Dependencies** | Node.js + npx | click, httpx, Node.js + npx (auth only) |

**The generated CLI MUST work standalone** — a CLI that requires a running browser
defeats the purpose of having a CLI. playwright-cli is only needed during `auth login`;
all regular commands use httpx.

---

## Pipeline: Skill Sequence

The 8-phase pipeline is implemented as a chain of skills. Each skill handles its
phases and invokes the next when done. Hard gates prevent skipping.

| Phase | Skill | What it does | Hard Gate |
|-------|-------|-------------|-----------|
| 1 | `capture` | Assess site + capture traffic + explore + save auth | playwright-cli available (or public API shortcut) |
| 2 | `methodology` | Analyze + Design + Implement CLI | raw-traffic.json exists |
| 3 | `testing` | Write tests + document results | Implementation complete |
| 4 | `standards` | Publish, verify, smoke test, generate Claude skill | All tests pass |

> **Phase numbering:** The pipeline has 4 phases. Some skills reference legacy
> sub-phase numbers (e.g., "Phase 7", "Phase 8"). Ignore these — use the 4-phase
> scheme above. Capture=1, Methodology=2, Testing=3, Standards=4.

**Sequencing:**
```
capture → methodology → testing → standards → DONE
```

### Parallelism Strategy

Phases are sequential (each depends on the previous), but WITHIN each phase there
are significant parallelism opportunities. Use the `Agent` tool with multiple
concurrent calls to maximize throughput.

```
Phase 1 (Capture): Sequential — single browser session
  framework detection → protection check → API probe → full capture

Phase 2 (Methodology): Fork-join pattern
  Sequential: exceptions.py → client.py → auth.py → models.py
  Parallel:   commands/*.py (one agent per file) + test_core.py (background)
  Sequential: cli entry point, __main__.py, setup.py

Phase 3 (Testing): Parallel test execution
  Parallel:   test_core.py (if not started in Phase 2) + test_e2e.py
  Sequential: run tests → update TEST.md

Phase 4 (Standards): Parallel post-pipeline tasks
  Sequential: pip install → smoke test
  Parallel:   Claude skill + repo README update + package README
```

**Key rules for parallel dispatch:**
- Launch ALL independent agents in a **single message** with multiple `Agent` tool calls
- Use `run_in_background: true` for agents whose results you don't need immediately
- Each agent gets: a clear scope, the files it depends on, and where to write output
- Never parallelize agents that write to the **same file**

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

## Reference Materials

These reference files provide detailed patterns for specific topics. They live
under `skills/*/references/` and are loaded when the relevant skill activates.

### Capture References (`skills/capture/references/`)

| Reference | When to read | Used in |
|-----------|-------------|---------|
| `playwright-cli-tracing.md` | Understanding trace file format | Phase 1 |
| `playwright-cli-sessions.md` | Named sessions, auth persistence | Phase 1 |
| `playwright-cli-advanced.md` | run-code, wait strategies, downloads | Phase 1 |
| `framework-detection.md` | Detecting SSR frameworks during capture | Phase 1 |
| `protection-detection.md` | Checking anti-bot protections during capture | Phase 1 |
| `api-discovery.md` | Finding API endpoints, decision tree, strategy details | Phase 1 |

### Methodology References (`skills/methodology/references/`)

| Reference | When to read | Used in |
|-----------|-------------|---------|
| `traffic-patterns.md` | Phase 2 — identifying API protocol (REST, GraphQL, SSR, batchexecute) | Phase 1-3 |
| `auth-strategies.md` | Phase 4 — implementing auth module | Phase 4 |
| `google-batchexecute.md` | Phase 2+4 — when target is a Google app | Phase 2, 4 |
| `ssr-patterns.md` | Phase 2 — when target uses SSR (Next.js, Nuxt, etc.) | Phase 2 |
| `helpers-module-example.py` | Phase 3 — implementing utils/helpers.py | Phase 3 |
| `persistent-context-example.py` | Phase 3 — persistent context commands | Phase 3 |

---

## Critical Rules

These are non-negotiable standards that apply across all phases:

- **Auth credentials MUST be stored securely.** `chmod 600 auth.json`. Never hardcode
  tokens in source. If auth file missing, CLI errors with clear instructions — never
  falls back to unauthenticated requests.
- **Tests MUST fail (not skip) when auth is missing.** Tests that skip on missing auth
  give false confidence. Before running any E2E test, run `cli-web-<app> auth login`
  then `auth status` to verify. Tests that output "auth not configured" are BROKEN.
- **Every command MUST support `--json`.** Agents consume structured output.
  Human-readable is optional; machine-readable is required.
  **`--json` flag placement:** Place `--json` on EACH individual command (not just
  the top-level group). In REPL mode, propagate `--json` from the top-level group
  via `ctx.obj["json"]`. For subprocess calls, `cli-web-<app> <resource> list --json`
  must work — this means `--json` must be an option on the command, not only on the group.
- **E2E tests MUST include subprocess tests** via `_resolve_cli("cli-web-<app>")` —
  source-level imports can hide packaging bugs (missing entry points, broken imports)
  that only surface when the CLI is invoked as an installed command.
- **Every `cli_web/<app>/` MUST contain `README.md`** with auth setup, install steps,
  and usage examples — without it, users who discover the CLI via `pip` have no way to
  learn how to authenticate or use it.
- **Every `cli_web/<app>/tests/` MUST contain `TEST.md`** written in two parts: plan
  (before tests), results (appended after running) — this is the audit trail that proves
  tests were designed intentionally and actually passed, not just committed untested.
- **Every CLI MUST use the unified REPL skin** (`repl_skin.py`) — consistent branding
  and prompt behavior across all `cli-web-*` tools. REPL MUST be the default when
  invoked without a subcommand — users expect an interactive shell, not a help dump.
- **Rate limits MUST be respected.** Never retry without backoff. Never hammer endpoints.
- **Response bodies MUST be verified.** Never trust HTTP status alone. Always check
  that returned JSON contains expected fields.
- **Content generation commands MUST download the result.** If the app generates
  content (audio, images, video, documents), the CLI must handle the full lifecycle:
  trigger → poll → download → save. Support `--output <path>` flag.
- **Generation commands MUST support `--wait` and `--retry`** — without these, agents
  cannot script end-to-end workflows and must poll manually. `--wait` polls until the
  artifact is ready (exponential backoff). `--retry N` retries on 429 rate limit
  (default 3). `--output <path>` saves content to a file.
- **CAPTCHAs MUST pause and prompt, never crash or skip.** If a CAPTCHA is detected
  in any response, stop and tell the user to solve it in their browser. Wait for
  confirmation, then retry.

### Auth Resilience

Beyond basic cookie storage, the auth module MUST support:

1. **Environment variable auth** — `CLI_WEB_<APP>_AUTH_JSON` for CI/CD and headless
   environments. When set, skip file-based auth entirely:
   ```python
   env_auth = os.environ.get(f"CLI_WEB_{app_upper}_AUTH_JSON")
   if env_auth:
       return json.loads(env_auth)
   ```

2. **Auto-refresh with single retry** — On 401/403, re-fetch homepage tokens, retry once.
   Never retry more than once to avoid infinite loops:
   ```python
   def _call_with_auth_retry(self, method, url, **kwargs):
       try:
           return self._call(method, url, **kwargs)
       except AuthError as e:
           if not e.recoverable:
               raise
           self._refresh_tokens()
           return self._call(method, url, retry_on_auth=False, **kwargs)
   ```

3. **Context commands** — For apps with persistent context (e.g., selecting a notebook,
   project, or workspace), provide `use <id>` and `status` commands:
   ```bash
   cli-web-<app> use <resource-id>    # Set context
   cli-web-<app> status               # Show current context
   ```
   Store context in `~/.config/cli-web-<app>/context.json`. This avoids passing
   `--notebook-id` on every command.

### Namespaced Sub-Clients

For apps with 3+ resource types, the client SHOULD be split into namespaced sub-clients
instead of one monolithic class:

```python
# Instead of:
client = AppClient()
client.list_notebooks()
client.add_source(nb_id, url)
client.generate_audio(nb_id)

# Use namespaced sub-clients:
client = AppClient()
client.notebooks.list()
client.sources.add_url(nb_id, url)
client.artifacts.generate_audio(nb_id)
```

Each sub-client lives in its own file (`_notebooks.py`, `_sources.py`, `_artifacts.py`)
and shares the core HTTP transport from `client.py`. This keeps each file focused
and makes the codebase navigable.

### Partial ID Resolution

Every CLI MUST support partial ID prefixes for get/rename/delete operations —
UUIDs are 36 characters and impossible to type from memory. Users should type
`abc` to match `abc123-long-uuid-...` instead of copying the full UUID. The `resolve_partial_id()` helper in `utils/helpers.py`:

- IDs >= 20 chars: assume complete, match exactly
- Short prefixes: case-insensitive prefix match against list
- Ambiguous: show up to 5 candidates
- No match: clear error

See `references/helpers-module-example.py` for the implementation.

Commands that accept a resource ID (get, rename, delete) MUST use `@click.argument`
(positional) instead of `@click.option("--id", required=True)` — positional args
match natural shell conventions (`git checkout main`, not `git checkout --branch main`):

```bash
# Good: cli-web-app notebooks get abc123
# Bad:  cli-web-app notebooks get --id abc123
```

### Persistent Context

For apps where commands operate on a specific resource (notebook, project,
workspace), provide `use <id>` and `status` commands that persist to
`~/.config/cli-web-<app>/context.json`. This makes `--notebook` optional
on subsequent commands. The `require_notebook()` helper checks the arg first,
then falls back to context.

See `references/persistent-context-example.py` for the pattern.

### Error Handler Context Manager

Commands MUST use `with handle_errors(json_mode=use_json):` instead of
manual try/except blocks. This centralizes error handling, ensures consistent
exit codes (1=user, 2=system, 130=interrupt), and produces structured JSON
errors in `--json` mode.

### Rate-Limit Retry

Generation commands MUST support `--retry N` flag — generation endpoints are the most
rate-limited, and a single 429 should not abort a long-running workflow. The
`retry_on_rate_limit()` helper wraps the generation call with exponential backoff (60s→300s).

### Regional Cookie Support

The auth module MUST accept Google cookies from regional domains (`.google.co.jp`,
`.google.de`, `.google.com.br`, etc.) in addition to `.google.com`. International
users may have cookies on regional ccTLDs. Include a `GOOGLE_REGIONAL_CCTLDS`
frozenset with 60+ domains. Also include `.googleusercontent.com` for authenticated
media downloads.

**CRITICAL: `.google.com` cookies MUST always take priority over regional duplicates.**
When the same cookie name exists on both `.google.com` and `.google.co.il` (or any
other regional domain), the `.google.com` value is the one that Google services
accept. Never overwrite a `.google.com` cookie with a regional duplicate. This is
the #1 auth bug for international users. See Critical Lesson #14 and
`auth-strategies.md` "Cookie domain priority" for the working pattern from
`notebooklm/agent-harness/cli_web/notebooklm/core/auth.py`.

---

## Critical Lessons

1. **Auth is Everything** — The auth module is the most critical component.
2. **Capture Comprehensively** — Systematically exercise every feature.
3. **APIs Change** — Include version detection and graceful degradation.
4. **Rate Limiting** — Respect limits. Add exponential backoff. Cache where safe.
5. **Verify Responses** — Never trust status 200 alone.
6. **GraphQL Needs Special Handling** — Abstract query complexity into human-friendly commands.
7. **Content Generation Requires Download** — trigger → poll → download → save.
8. **CAPTCHAs Require Human Intervention** — Detect, pause, guide, resume.
9. **Cross-Reference RPC IDs** — Obfuscated method IDs (batchexecute) can be
   mislabeled during traffic analysis. Always cross-reference with known-good
   implementations (check existing CLIs in this repo — `futbin/`, `notebooklm/`). A single wrong
   ID (e.g., using CREATE_NOTE instead of CREATE_ARTIFACT) causes silent failures.
10. **Force UTF-8 on Windows** — Player names, Hebrew text, and emoji break on
    Windows without explicit encoding. Add this at the top of `<app>_cli.py`:
    ```python
    import sys
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError: pass
    ```
11. **HTML Parsers Must Extract ALL Visible Fields** — When scraping a table, extract
    every column — not just name/price. If the HTML shows version, club, nation, and
    6 stat columns, the parser must return all of them. Empty fields in the output
    mean the parser is incomplete, not that the data doesn't exist. Verify by comparing
    `--json` output fields against what the browser shows.
12. **SSR Slug URLs** — Many SSR sites require a slug in the URL
    (`/resource/40/item-name`, not `/resource/40`). The bare-ID URL may 404.
    Strategy: search API first to get the canonical URL/slug, then scrape the
    detail page. If search doesn't return the ID, try with a placeholder slug
    (some sites redirect to the correct one).
13. **Scraped Text Has Noise** — HTML table cells often contain extra text
    alongside the value you want (percentage changes, badges, status labels,
    currency symbols). Never parse `get_text()` directly — use regex or string
    splitting to isolate the target value before type conversion.
14. **Cookie Domain Priority Breaks International Users** — Playwright's
    `state-save` captures the same Google auth cookie names (`SID`,
    `__Secure-1PSID`, `HSID`, etc.) on BOTH `.google.com` AND regional
    domains (`.google.co.il`, `.google.de`, `.google.co.jp`, etc.).
    Naive flattening `{c["name"]: c["value"] for c in cookies}` lets the
    LAST value win — which may be the regional one. Google services like
    NotebookLM only accept `.google.com` cookies. The fix: always prefer
    `.google.com` values when deduplicating. See `auth-strategies.md`
    "Cookie domain priority" section for the working pattern.
15. **`login_browser()` Must Use `Popen`, Not `subprocess.run()`** —
    Playwright-cli's `open --headed --persistent` keeps the process alive
    while the browser is open. `subprocess.run()` blocks until the browser
    closes, making the subsequent `input("press ENTER...")` unreachable.
    The user sees the browser, but the CLI appears frozen. Fix: use
    `subprocess.Popen()` so the browser runs in the background and `input()`
    works while the user logs in. Close the session separately after
    `state-save`.
16. **Playwright `state-save` Produces a List, Not a Dict** — The raw
    format is `{"cookies": [{name, value, domain, httpOnly, ...}, ...]}`.
    `load_cookies()` must handle both this list format AND the extracted
    dict format `{"cookies": {"SID": "val", ...}}`. Always check
    `isinstance(cookies, list)` before using the value. If it's a list,
    run it through `_extract_cookies()` with domain priority.

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
| App names | No hyphens. Underscores OK (`monday_com`) |

---

## Generated CLI Structure

Every generated CLI follows this package structure:

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
            |   +-- exceptions.py    # Domain-specific exception hierarchy
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
            |   +-- helpers.py      # Shared helpers (partial ID, error handler, context, polling)
            |   +-- output.py       # JSON/table formatting
            |   +-- config.py       # Config file management
            +-- tests/
                +-- __init__.py
                +-- TEST.md         # Test plan + results
                +-- test_core.py    # Unit tests (mocked HTTP)
                +-- test_e2e.py     # E2E tests (live API)
```

---

## Testing Strategy

Standard three-layer suite (fixture replay is optional):

| Layer | File | What it tests |
|-------|------|--------------|
| Unit tests | `test_core.py` | Core functions with mocked HTTP. No real network. Fast, deterministic. |
| E2E live tests | `test_e2e.py` | Real API calls. Require auth — FAIL without it. CRUD round-trip. |
| CLI subprocess | `test_e2e.py` | Installed `cli-web-<app>` via `_resolve_cli()`. Full end-to-end. |
| Integration (VCR) | `test_integration.py` | Recorded HTTP cassettes via VCR.py. Reproducible, no network. Medium realism. |
| E2E fixture tests *(optional)* | `test_e2e.py` | Replay captured responses from `tests/fixtures/`. Only add for complex HTML parsing. |

**VCR.py integration tests** are recommended for apps with complex RPC protocols
(batchexecute, GraphQL). Record cassettes during development, replay in CI.
Use `@pytest.mark.vcr` marker and store cassettes in `tests/cassettes/`.
