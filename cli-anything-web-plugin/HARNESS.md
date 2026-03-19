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

Every generated CLI MUST include a `core/exceptions.py` with a domain-specific exception
hierarchy. Generic `RuntimeError` is not acceptable — typed exceptions enable retry logic,
proper CLI exit codes, and structured JSON error responses.

**Required base hierarchy:**

```python
# core/exceptions.py
class AppError(Exception):
    """Base for all CLI errors."""

class AuthError(AppError):
    """Authentication failed — token expired, cookies invalid, etc."""
    def __init__(self, message: str, recoverable: bool = True):
        self.recoverable = recoverable
        super().__init__(message)

class RateLimitError(AppError):
    """Server returned 429 — retry after backoff."""
    def __init__(self, message: str, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(message)

class NetworkError(AppError):
    """Connection failed, DNS error, timeout."""

class ServerError(AppError):
    """Server returned 5xx."""
    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)

class NotFoundError(AppError):
    """Resource not found (404)."""
```

Extend with domain-specific errors as needed (e.g., `ArtifactNotReadyError`,
`SourceProcessingError`). The client maps HTTP status codes to these exceptions.
Commands catch them and produce appropriate exit codes + JSON error output.

### Exponential Backoff & Polling

Any operation that takes >2 seconds (content generation, file processing, research)
MUST use exponential backoff polling — never fixed `time.sleep()`.

**Required pattern:**

```python
# core/client.py or utils/polling.py
import time

def poll_until_complete(
    check_fn,                    # () -> status dict
    initial_interval: float = 2.0,
    max_interval: float = 10.0,
    timeout: float = 300.0,
    backoff_factor: float = 1.5,
) -> dict:
    """Poll with exponential backoff until complete or timeout."""
    start = time.perf_counter()
    interval = initial_interval
    while time.perf_counter() - start < timeout:
        status = check_fn()
        if status.get("completed") or status.get("failed"):
            return status
        time.sleep(min(interval, max_interval))
        interval *= backoff_factor
    raise TimeoutError(f"Operation timed out after {timeout}s")
```

For generation commands, also implement retry on rate limit:
```python
def retry_on_rate_limit(fn, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except RateLimitError as e:
            if attempt == max_retries:
                raise
            delay = e.retry_after or (60 * (2 ** attempt))
            time.sleep(min(delay, 300))
```

### Progress Feedback

Operations taking >2 seconds SHOULD show progress to the user. Use `rich` for
spinners and progress bars when not in `--json` mode:

```python
from rich.console import Console
console = Console()

with console.status("Generating audio...") as status:
    result = poll_until_complete(check_fn)
    status.update("Downloading...")
    download(result["url"], output_path)
```

In `--json` mode, suppress spinners and output only the final JSON result.
Add `rich>=13.0` to `setup.py` dependencies.

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

| | Development (Phases 1-8) | End-User (published CLI) |
|--|--------------------------|--------------------------|
| **Browser** | playwright-cli manages its own | playwright-cli via subprocess (auth only) |
| **Traffic capture** | `tracing-start` → browse → `tracing-stop` | N/A — CLI uses httpx |
| **Auth** | `state-save` after user logs in | `auth login` → subprocess `state-save` → parse cookies |
| **Runtime HTTP** | N/A | httpx — no browser needed |
| **Dependencies** | Node.js + npx | click, httpx, Node.js + npx (auth only) |

**The generated CLI MUST work standalone.** playwright-cli is only needed during
`auth login` — all regular commands use httpx.

---

## Pipeline: Skill Sequence

The 8-phase pipeline is implemented as a chain of skills. Each skill handles its
phases and invokes the next when done. Hard gates prevent skipping.

| Phase | Skill | What it does | Hard Gate |
|-------|-------|-------------|-----------|
| 1 | `capture` | Assess site + capture traffic + explore + save auth | playwright-cli available |
| 2 | `methodology` | Analyze + Design + Implement CLI | raw-traffic.json exists |
| 3 | `testing` | Write tests + document results | Implementation complete |
| 4 | `standards` | Publish, verify, smoke test, generate Claude skill | All tests pass |

**Sequencing:**
```
capture → methodology → testing → standards → DONE
```

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
- **E2E tests MUST include subprocess tests** via `_resolve_cli("cli-web-<app>")`.
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
  trigger → poll → download → save. Support `--output <path>` flag.
- **Generation commands MUST support `--wait` and `--retry`.** `--wait` polls
  until the artifact is ready (exponential backoff). `--retry N` retries on
  429 rate limit (default 3). `--output <path>` saves content to a file.
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

Every CLI MUST support partial ID prefixes for get/rename/delete operations.
Users should type `abc` to match `abc123-long-uuid-...` instead of copying
the full UUID. The `resolve_partial_id()` helper in `utils/helpers.py`:

- IDs >= 20 chars: assume complete, match exactly
- Short prefixes: case-insensitive prefix match against list
- Ambiguous: show up to 5 candidates
- No match: clear error

See `references/helpers-module-example.py` for the implementation.

Commands that accept a resource ID (get, rename, delete) MUST use `@click.argument`
(positional) instead of `@click.option("--id", required=True)`:

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

Generation commands MUST support `--retry N` flag. The `retry_on_rate_limit()`
helper wraps the generation call with exponential backoff (60s→300s).

### Regional Cookie Support

The auth module MUST accept Google cookies from regional domains (`.google.co.jp`,
`.google.de`, `.google.com.br`, etc.) in addition to `.google.com`. International
users may have cookies on regional ccTLDs. Include a `GOOGLE_REGIONAL_CCTLDS`
frozenset with 60+ domains. Also include `.googleusercontent.com` for authenticated
media downloads.

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
   implementations or open-source clients before hardcoding IDs. A single wrong
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
