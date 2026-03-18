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
- **CAPTCHAs MUST pause and prompt, never crash or skip.** If a CAPTCHA is detected
  in any response, stop and tell the user to solve it in their browser. Wait for
  confirmation, then retry.

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

---

## Testing Strategy

Standard three-layer suite (fixture replay is optional):

| Layer | File | What it tests |
|-------|------|--------------|
| Unit tests | `test_core.py` | Core functions with mocked HTTP. No real network. Fast, deterministic. |
| E2E live tests | `test_e2e.py` | Real API calls. Require auth — FAIL without it. CRUD round-trip. |
| CLI subprocess | `test_e2e.py` | Installed `cli-web-<app>` via `_resolve_cli()`. Full end-to-end. |
| E2E fixture tests *(optional)* | `test_e2e.py` | Replay captured responses from `tests/fixtures/`. Only add for complex HTML parsing. |
