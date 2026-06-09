# HARNESS.md — CLI-Anything-Web Methodology

**Making Closed-Source Web Apps Agent-Native via Network Traffic Analysis**

This is the navigational overview: pipeline, tool hierarchy, and the map of
skills/scripts/references. Implementation rules are DEFINED once in
`skills/shared/CONVENTIONS.md`; failure handling lives in
`skills/shared/RECOVERY.md`. Read this file for the big picture; read the
relevant skill for phase details.

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

### The Conventions Spec

All implementation rules — exception hierarchy, JSON envelope, auth rules,
REPL rules, backoff, naming, UTF-8 fix, subprocess tests, protocol-leak
checks — are defined in **`skills/shared/CONVENTIONS.md`**. Quick index:

| Rule | Where defined |
|------|---------------|
| Typed exception hierarchy + error codes | CONVENTIONS.md §Exception Hierarchy |
| `--json` success/error envelope | CONVENTIONS.md §JSON Envelope |
| Auth storage, env var, 3-attempt auto-refresh, cookie priority | CONVENTIONS.md §Auth Rules |
| REPL: shlex, --json propagation, help-sync, positional args | CONVENTIONS.md §REPL Rules |
| Exponential backoff, `--wait`/`--retry`/`--output` | CONVENTIONS.md §Exponential Backoff & Polling |
| Windows UTF-8 fix (stdout AND stderr) | CONVENTIONS.md §Windows UTF-8 Fix |
| `_resolve_cli` + `CLI_WEB_FORCE_INSTALLED` subprocess tests | CONVENTIONS.md §Subprocess Test Rule |
| Protocol-leak smoke check (`wrb.fr`, empty `[]`, …) | CONVENTIONS.md §Protocol-Leak Smoke Check |
| Naming (`cli-web-<app>`, namespaces, config dirs) | CONVENTIONS.md §Naming Conventions |

When any hard gate fails (tracing-stop, parse-trace, validate-capture,
phase-state, scaffold), follow the decision trees in
**`skills/shared/RECOVERY.md`** — they bound retries and map each validator
gate to a targeted remediation.

---

## Tool Hierarchy (strict priority)

### Phase 1: Traffic Capture (Developer)

| Priority | Tool | When to use |
|----------|------|-------------|
| 1. PRIMARY | `npx @playwright/cli@latest` via Bash | Traffic recording, tracing |
| 2. FALLBACK | `mcp__chrome-devtools__*` MCP tools | Only if playwright-cli unavailable |
| 3. NEVER | `mcp__claude-in-chrome__*` | Blocked — cannot capture request bodies |

### Generated CLI: Auth Login (End-User)

| Tool | When to use |
|------|-------------|
| Python `sync_playwright()` | `auth login` command — opens browser for Google/SSO login |
| `curl_cffi` with `impersonate` | Runtime HTTP for anti-bot protected sites (Unsplash, ProductHunt) |
| `httpx` | Runtime HTTP for unprotected sites and JSON APIs |

> **CRITICAL**: Generated CLIs use Python `sync_playwright()` for auth login,
> NOT `npx @playwright/cli`. See CONVENTIONS.md §Auth Rules.

### Development vs End-User

| | Development (Phases 1-4) | End-User (published CLI) |
|--|--------------------------|--------------------------|
| **Browser** | npx playwright-cli manages its own | Python sync_playwright() (auth only) |
| **Traffic capture** | `tracing-start` → browse → `tracing-stop` | N/A — CLI uses httpx/curl_cffi |
| **Auth** | `state-save` after user logs in | `auth login` → sync_playwright context → storage_state → parse cookies |
| **Runtime HTTP** | N/A | httpx or curl_cffi — no browser needed |
| **Dependencies** | Node.js + npx | click, httpx (or curl_cffi), playwright (auth only) |

**The generated CLI MUST work standalone** — a CLI that requires a running browser
defeats the purpose of having a CLI. Python playwright is only needed during `auth login`;
all regular commands use httpx.

---

## Pipeline: Skill Sequence

The 4-phase pipeline is implemented as a chain of skills. Each skill handles its
phases and invokes the next when done. Hard gates prevent skipping.

| Phase | Skill | What it does | Hard Gate |
|-------|-------|-------------|-----------|
| 1 | `capture` | Assess site + capture traffic + explore + save auth | playwright-cli available (or public API shortcut) |
| 2 | `methodology` | Analyze + Design + Implement CLI | raw-traffic.json exists + validate-capture passed |
| 3 | `testing` | Write tests + document results | Implementation complete |
| 4 | `standards` | Publish, verify, smoke test, generate Claude skill | All tests pass |

> **Phase numbering:** The pipeline has 4 phases: Capture=1, Methodology=2,
> Testing=3, Standards=4. The standards phase includes an implementation
> review step (3 parallel agents) before the structural checklist and publish.

**Sequencing:**
```
capture → methodology → testing → standards → DONE
```

Gate failures: see `skills/shared/RECOVERY.md` for the per-gate decision trees.

### Parallelism Strategy

Phases are sequential. Within each phase, dispatch independent file writes as
parallel subagents. Core modules (exceptions → client → auth → models) must be
sequential. Command modules and test files are independent — write them in parallel.
Never parallelize writes to the same file.

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
Read them **section-addressed** when possible (e.g., `auth-strategies.md`
§"Cookie domain priority") instead of whole-file.

### Shared Specs (`skills/shared/`)

| File | Purpose |
|------|---------|
| `CONVENTIONS.md` | THE definition of every implementation rule (see index above) |
| `RECOVERY.md` | Failure decision trees for every hard gate |

### Capture References (`skills/capture/references/`)

| Reference | When to read | Used in |
|-----------|-------------|---------|
| `playwright-cli-commands.md` | **READ FIRST** — correct syntax, timeouts, ESM rules | Phase 1 |
| `playwright-cli-tracing.md` | Trace file format, lifecycle management, recovery protocol | Phase 1 |
| `playwright-cli-sessions.md` | Named sessions, auth persistence | Phase 1 |
| `playwright-cli-advanced.md` | run-code, wait strategies, iframe handling, localized UIs, downloads | Phase 1 |
| `framework-detection.md` | Site fingerprint command, SSR framework detection | Phase 1 |
| `protection-detection.md` | Checking anti-bot protections during capture | Phase 1 |
| `api-discovery.md` | Finding API endpoints, decision tree, strategy details | Phase 1 |

### Capture Scripts (`scripts/`)

| Script | Purpose | When to use |
|--------|---------|-------------|
| `phase-state.py` | Track all 4 pipeline phases — skip completed, retry failed. Low-level state store; mutated by skills via `complete`/`fail`/`reset`/`check`. | Before each phase, prevents re-running expensive work |
| `capture-checkpoint.py` | Save/restore capture session state (within Phase 1) | Resume interrupted captures, prevent duplicate work |
| `parse-trace.py` | Convert trace files → raw-traffic.json | After `tracing-stop` (default capture method) |
| `mitmproxy-capture.py` | Optional proxy-based capture — no body truncation, real-time noise filtering, dedup, enhanced metadata (timestamps, cookies, body sizes). Supports `start-proxy`/`stop-proxy` for agent-driven browsing. Activated with `--mitmproxy` flag. Requires `pip install mitmproxy` (Python 3.12+). | When `--mitmproxy` flag is passed to `/cli-anything-web` |
| `analyze-traffic.py` | Analyze raw-traffic.json → protocol/endpoint detection. v1.3.0 adds request sequence, session lifecycle, and endpoint size analysis when enhanced fields are present. | Auto-run by parse-trace.py or mitmproxy-capture.py |
| `extract-browser-cookies.py` | Cookie extraction utility | During auth implementation |
| `site-fingerprint.js` | Playwright run-code script — detects SSR framework (Next.js, Nuxt, etc.) and baseline protections | Phase 1 — invoked by capture skill during site assessment |
| `launch-chrome-debug.sh` | Launch Chrome with a dedicated debug profile + remote-debugging port | Phase 1 — when using `mcp__chrome-devtools__*` as fallback capture |

### Pipeline Automation Scripts (`scripts/`)

| Script | Purpose | When to use |
|--------|---------|-------------|
| `scaffold-cli.py` | Generate the full boilerplate structure from `templates/*.tpl` (Jinja2, TEMPLATE_VERSION 2.0.0). Renders exceptions, client, unified auth, CLI entry, helpers, output, setup, conftest, README/SKILL skeletons; repeatable `--resource` flags scaffold `commands/<resource>.py` modules; writes `.manifest.json` provenance. Requires `pip install jinja2`. | Phase 2 — Step B.0, before implementing endpoint methods |
| `validate-checklist.py` | Run the automated checks of the quality checklist (AST + regex), tiered: Tier 1 critical (blocks publish) and Tier 2 comprehensive. `--tier1-only` for fail-fast; judgment-based checks are covered by the Phase 4 review agents | Phase 4 — before manual review, or via `/validate` command |
| `generate-test-docs.py` | AST-parse test files for TEST.md Part 1 (plan), run pytest for Part 2 (results) | Phase 3 — after writing tests |
| `smoke-test.py` | Post-install CLI validation (--help, --version, --json, protocol leak detection) | Phase 4 — after `pip install -e .` |
| `validate-capture.py` | Gate between Phase 1 and Phase 2 — checks entry count, protocol, WRITE ops, error rate, endpoint diversity. On failure see RECOVERY.md §validate-capture | Phase 1 — end of Step 4 in capture skill |
| `repl_skin.py` | Vendored copy of the canonical REPL UI. **Canonical source: `cli-web-core/cli_web_core/repl_skin.py`** — this copy is synced by `cli-web-devkit resync`, never hand-edited. Copied into every generated CLI's `utils/` by scaffold-cli.py | Phase 2 — copied by scaffold-cli.py |
| `setup.sh` | One-time plugin setup — verifies dependencies (playwright, mitmproxy optional) | Plugin install / CI |
| `run-pipeline.py` | Pipeline orchestrator — `status` view (reads phase-state.json and adds next-action guidance), `parse` (Phase 1 tail), `validate` (Phase 4 tail). **Use this for human/agent-facing status**; use `phase-state.py` only to mutate state. | Any phase — `run-pipeline.py status <app-dir>` for next-action guidance |

### Shared Script Utilities (`scripts/`)

Sibling modules imported by multiple scripts — single source of truth.

| Module | Exports | Consumers |
|--------|---------|-----------|
| `plugin_paths.py` | `get_plugin_root()`, `get_scripts_dir()`, `get_templates_dir()` | scaffold-cli.py, run-pipeline.py |
| `traffic_utils.py` | `NOISE_PATTERNS`, `STATIC_EXTENSIONS`, `MEDIA_EXTENSIONS`, `is_noise_url()`, `is_static_asset(url, include_media=False)`, `normalize_headers()` | parse-trace.py, analyze-traffic.py, mitmproxy-capture.py |
| `state_utils.py` | `utc_now_iso()`, `load_json_state()`, `save_json_state()` | phase-state.py, capture-checkpoint.py, run-pipeline.py |

### Pipeline Anatomy — Which Skill Calls Which Script

| Phase | Skill | Primary scripts | Auxiliary scripts |
|-------|-------|-----------------|-------------------|
| 1. capture | `skills/capture/SKILL.md` | `site-fingerprint.js`, `parse-trace.py` (default) or `mitmproxy-capture.py` (--mitmproxy), `validate-capture.py` (gate) | `capture-checkpoint.py` (resume), `launch-chrome-debug.sh` (fallback), `analyze-traffic.py` (auto-run by parse/mitmproxy) |
| 2. methodology | `skills/methodology/SKILL.md` | `scaffold-cli.py` (Step B.0) | `repl_skin.py` (copied by scaffold-cli) |
| 3. testing | `skills/testing/SKILL.md` | `generate-test-docs.py` (plan + results) | — |
| 4. standards | `skills/standards/SKILL.md` | `validate-checklist.py`, `smoke-test.py` | 4 review agents in `agents/` (cross-cli-consistency, harness-compliance, output-ux, traffic-fidelity); optional `gap-analyzer` skill |
| any | — | `phase-state.py` (track), `run-pipeline.py status` (next action) | `skills/shared/RECOVERY.md` on gate failure |

### Methodology References (`skills/methodology/references/`)

| Reference | When to read | Used in |
|-----------|-------------|---------|
| `traffic-patterns.md` | Phase 2 — identifying API protocol (REST, GraphQL, SSR, batchexecute) | Phase 2 |
| `auth-strategies.md` | Phase 2 — implementing auth module (read section-addressed, e.g., §"Cookie domain priority") | Phase 2 |
| `google-batchexecute.md` | Phase 2 — when target is a Google app | Phase 2 |
| `ssr-patterns.md` | Phase 2 — when target uses SSR (Next.js, Nuxt, etc.) | Phase 2 |
| `helpers-module-example.py` | Phase 2 — implementing utils/helpers.py | Phase 2 |
| `persistent-context-example.py` | Phase 2 — persistent context commands | Phase 2 |

### Implementation Patterns (Reference Files)

These patterns are documented in reference files — read them during implementation, don't reinvent:

| Pattern | Reference | Key |
|---------|-----------|-----|
| Exception hierarchy | `exception-hierarchy-example.py` | CONVENTIONS.md §Exception Hierarchy |
| Client architecture | `client-architecture-example.py` | Sub-clients for 3+ resources |
| Polling/backoff | `polling-backoff-example.py` | CONVENTIONS.md §Exponential Backoff & Polling |
| Helpers module | `helpers-module-example.py` | handle_errors(), partial ID, _resolve_cli() |
| Persistent context | `persistent-context-example.py` | use/status commands, context.json |
| Rich output | `rich-output-example.py` | Tables, spinners, JSON error output |
| Auth strategies | `auth-strategies.md` | CONVENTIONS.md §Auth Rules |

---

## Critical Rules (index — definitions in CONVENTIONS.md)

- Auth: `chmod 600 auth.json`, env var fallback, **3-attempt auto-refresh on
  401/403** (never more), `.google.com` cookie priority, dual cookie formats
  → CONVENTIONS.md §Auth Rules. Tests FAIL (not skip) without auth.
- Every command supports `--json`; errors are JSON too → CONVENTIONS.md
  §JSON Envelope.
- REPL is default (`invoke_without_command=True`), shlex parsing, `--json`
  propagation by prepending args, help-sync → CONVENTIONS.md §REPL Rules.
- Exponential backoff for polling and 429s; generation commands take
  `--wait` + `--retry N` + `--output path` → CONVENTIONS.md §Exponential
  Backoff & Polling. CAPTCHAs pause and prompt.
- E2E tests include subprocess tests → CONVENTIONS.md §Subprocess Test Rule.
- README.md and TEST.md required in every CLI package.

---

## Lessons Learned (cross-reference)

These lessons are documented in detail in the skill/reference where they're most
actionable. This section is a quick-reference index — read the linked file for
full context and code examples.

| Bug / Gotcha | Reference | Fix |
|------|-----------|-----|
| Auth login via npx fails on Windows | `auth-strategies.md` | Use Python `sync_playwright()` with persistent context |
| `.google.co.il` cookies override `.google.com` | CONVENTIONS.md §Auth Rules | `.google.com` cookies take priority over regional |
| `load_cookies()` gets list vs dict format | CONVENTIONS.md §Auth Rules | Handle both `[{name,value}]` and `{name: value}` |
| RPC IDs reused for different operations | `google-batchexecute.md` | Always verify against traffic, never guess |
| `httpx` → 401/403 on previously working site | `protection-detection.md` | Site added Cloudflare — switch to `curl_cffi` |
| SSR slug URLs return 404 with bare IDs | `ssr-patterns.md` | Search first for canonical slug |
| Windows garbled output | CONVENTIONS.md §Windows UTF-8 Fix | Reconfigure stdout AND stderr to UTF-8 at entry |

---

## Generated CLI Structure

Every generated CLI follows this package structure (naming rules:
CONVENTIONS.md §Naming Conventions):

```
<app>/
+-- agent-harness/
    +-- <APP>.md                    # Software-specific SOP
    +-- setup.py                    # PyPI config (find_namespace_packages)
    +-- .manifest.json              # Provenance (written by scaffold-cli.py)
    +-- cli_web/                    # Namespace package (NO __init__.py)
        +-- <app>/                  # Sub-package (HAS __init__.py)
            +-- __init__.py
            +-- __main__.py         # python -m cli_web.<app>
            +-- <app>_cli.py        # Main CLI entry point
            +-- core/
            |   +-- __init__.py
            |   +-- client.py       # HTTP client (httpx or curl_cffi)
            |   +-- auth.py         # Auth management (auth sites only)
            |   +-- session.py      # State + undo/redo (stateful apps only)
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
            |   +-- repl_skin.py    # Vendored from cli-web-core (devkit-synced)
            |   +-- helpers.py      # Shared helpers (partial ID, error handler, context, polling)
            |   +-- output.py       # JSON/table formatting
            |   +-- config.py       # Config file management
            +-- tests/
                +-- __init__.py
                +-- TEST.md         # Test plan + results
                +-- test_core.py    # Unit tests (mocked HTTP)
                +-- test_e2e.py     # E2E tests (live API)
```
