# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLI-Anything-Web is a Claude Code plugin that generates production-grade Python CLIs for any web application by capturing live HTTP traffic. Point at a URL → capture API traffic via playwright-cli → analyze endpoints → generate a complete CLI with auth, REPL mode, `--json` output, and tests.

## Plugin Structure

```
cli-anything-web-plugin/          # The plugin itself
├── .claude-plugin/plugin.json    # Plugin manifest
├── HARNESS.md                    # Core methodology SOP (read this first)
├── commands/                     # Slash commands (/cli-anything-web, /record, /refine, etc.)
├── skills/                       # 4-phase skill system (capture → methodology → testing → standards)
└── scripts/                      # parse-trace.py, mitmproxy-capture.py, analyze-traffic.py (v1.3.0), site-fingerprint.js, capture-checkpoint.py, phase-state.py, repl_skin.py
```

Generated CLIs live in their own directories (e.g., `futbin/agent-harness/`) with namespace packages under `cli_web/`.

## Pipeline Phases

The skill sequence is strictly ordered: `capture → methodology → testing → standards → DONE`

| Phase | Skill | What it does |
|-------|-------|-------------|
| 1 | capture | Site assessment + browser traffic recording (or public API shortcut) |
| 2 | methodology | Analyze traffic, design CLI architecture, implement code |
| 3 | testing | Write unit + E2E + subprocess tests |
| 4 | standards | Implementation review (3 agents), 75-check checklist, publish, smoke test, generate skill |

### Site Profiles

Not all sites need the same pipeline path. Identify the profile early:
- **Auth + CRUD** (full pipeline): Google apps, Monday.com, Notion, Jira
- **Auth + read-only**: Dashboards, analytics viewers
- **No-auth + CRUD**: Sites with optional API key auth (Dev.to)
- **No-auth + read-only**: Hacker News, Wikipedia, npm — skip auth.py, skip write tests

## Tool Hierarchy (Strict)

1. **PRIMARY (traffic capture)**: `npx @playwright/cli@latest` — handles traffic recording during Phase 1 via tracing.
1b. **OPTIONAL (traffic capture)**: `mitmproxy-capture.py` — proxy-based capture with no body truncation, real-time filtering, enhanced metadata. Activated with `--mitmproxy` flag on `/cli-anything-web`. Requires `pip install mitmproxy` (Python 3.12+).
2. **PRIMARY (auth login)**: Python `sync_playwright()` — handles browser-based auth login in generated CLIs
3. **FALLBACK**: `mcp__chrome-devtools__*` — only if playwright unavailable
4. **NEVER**: `mcp__claude-in-chrome__*` — cannot capture request bodies

## Generated CLI Structure

Every generated CLI follows this exact layout under `<app>/agent-harness/`:

```
cli_web/                    # Namespace package (NO __init__.py)
└── <app>/                  # Sub-package (HAS __init__.py)
    ├── <app>_cli.py        # Click entry point + REPL default
    ├── core/               # exceptions.py, client.py, auth.py, session.py, models.py
    │   └── rpc/            # Optional: types.py, encoder.py, decoder.py (non-REST protocols)
    ├── commands/           # One file per resource group
    ├── utils/              # helpers.py, repl_skin.py, output.py, config.py
    └── tests/              # test_core.py (unit), test_e2e.py (E2E + subprocess)
```

Key files alongside: `setup.py`, `<APP>.md` (API map), `README.md`, `TEST.md`

## Running Tests

```bash
cd <app>/agent-harness
pip install -e .
python -m pytest cli_web/<app>/tests/ -v -s

# Single test
python -m pytest cli_web/<app>/tests/test_core.py::test_player_search -v -s
```

Set `CLI_WEB_FORCE_INSTALLED=1` for subprocess tests to find the installed CLI binary.

## Validating the Plugin

```bash
bash cli-anything-web-plugin/verify-plugin.sh
```

## Critical Conventions

- **Naming**: CLI command = `cli-web-<app>`, Python namespace = `cli_web.<app>`, config dir = `~/.config/cli-web-<app>/`
- **Namespace packages**: `cli_web/` has NO `__init__.py`; sub-packages DO have `__init__.py`
- **Typed exceptions**: Every CLI has `core/exceptions.py` with `AppError → AuthError, RateLimitError, NetworkError, ServerError, NotFoundError, RPCError`. No generic `RuntimeError`.
- **Auth**: Credentials in `auth.json` with `chmod 600`, never hardcoded. Env var `CLI_WEB_<APP>_AUTH_JSON` for CI/CD.
- **Auth cookie priority**: For Google apps, `.google.com` cookies MUST take priority over regional duplicates (`.google.co.il`, `.google.de`, etc.). Naive `{c["name"]: c["value"]}` flattening is BROKEN for international users. See `auth-strategies.md` "Cookie domain priority".
- **Auth login flow**: `login_browser()` MUST use Python `sync_playwright()` with `launch_persistent_context()`, NOT `npx @playwright/cli`. The npx approach has interactive input issues (Popen + input() race). Always include Windows event loop fix (`asyncio.DefaultEventLoopPolicy()`), anti-automation args, and regional cookie forcing (navigate to `accounts.google.com` then back after login).
- **Auth format handling**: `load_cookies()` must handle both raw playwright list format `[{name, value, domain}]` and extracted dict format `{name: value}`.
- **Auth retry**: Client retries once on recoverable `AuthError` (token refresh), never more.
- **Tests FAIL on missing auth** — never skip
- **Every command supports `--json`** — structured output for agents, including errors: `{"error": true, "code": "AUTH_EXPIRED", "message": "..."}`
- **REPL is default** when no subcommand given
- **Context commands**: `use <id>` and `status` for apps with persistent context (notebooks, projects)
- **Exponential backoff**: Polling operations use backoff (2s→10s), never fixed `time.sleep()`
- **E2E tests include subprocess tests** via `_resolve_cli("cli-web-<app>")`
- **HTML scraping fixtures** must use real CSS class names from production

## Tech Stack for Generated CLIs

- **CLI framework**: Click (with `@click.group(invoke_without_command=True)`)
- **HTTP client**: httpx (default), or curl_cffi for anti-bot protected sites (Cloudflare, AWS WAF, generic challenges). Use curl_cffi when plain httpx gets 401/403 with "bot" or "challenge" in response body. Sites can add protection at any time — if a working CLI starts getting blocked, switch to curl_cffi. For Cloudflare **managed challenge** sites (page title "Just a moment...") where curl_cffi also fails, use **camoufox** (stealth Firefox, `pip install camoufox`) for browser-interactive operations in headless mode. Combine with curl_cffi for read-only endpoints (hybrid pattern).
- **HTML parsing**: BeautifulSoup4 (for SSR sites)
- **Output**: Rich (`>=13.0`) for tables, spinners, colored status; custom table formatting
- **Auth flow**: Python `sync_playwright()` browser login → cookie extraction → `auth.json`; env var fallback for CI. Optional: `playwright-stealth` if bot detection blocks login.
- **Packaging**: `find_namespace_packages(include=["cli_web.*"])` in setup.py

## RPC Method Verification (Critical for batchexecute)

When implementing Google batchexecute CLIs, RPC method IDs can be confusing — the same service may use one ID for multiple operations with different param structures. **Never assume an RPC ID from its name alone.** Always verify:

1. **Cross-check every RPC method ID** against captured traffic. The param structure in `f.req` varies by operation even when using the same endpoint.
2. **One RPC ID may serve multiple operations**: e.g., `izAoDd` handles add-url, add-text, and add-file sources — differentiated only by param structure.
3. **Never reuse RPC IDs from other operations**: e.g., `VfAZjd` is SUMMARIZE, not ADD_URL_SOURCE. `hPTbtc` is GET_LAST_CONVERSATION_ID, not ADD_TEXT_SOURCE.
4. **Verify param structures match the actual traffic capture**: compare `f.req` body from captured HAR/trace with what the code generates.

### Mandatory CLI Output Verification

After implementing any command, run it with `--json` and check for raw protocol leaks
(`wrb.fr`, `af.httprm`, empty `[]`, null fields). See methodology/SKILL.md "Mandatory Smoke Check".

## Protocol Detection

Generated CLIs handle multiple API patterns: REST, GraphQL, gRPC-Web, Google batchexecute, custom RPC. The methodology skill identifies the protocol type during traffic analysis and generates appropriate client code.

### AWS WAF Sites (Booking.com pattern)

Sites protected by AWS WAF return a 202 JavaScript challenge page to raw HTTP clients. The bypass strategy:
- **`curl_cffi` with `impersonate='chrome'`** passes the WAF for GraphQL endpoints without cookies
- **SSR HTML pages** need a `aws-waf-token` cookie obtained via playwright-cli browser session
- **Critical**: Use ONLY the `aws-waf-token` cookie for SSR requests — the `bkng` session cookie contains affiliate data that triggers server-side redirects on detail pages
- **Hotel detail pages** redirect when date/occupancy params are present — fetch without them

## Generated CLIs

| CLI | Directory | Protocol | Key Pattern |
|-----|-----------|----------|-------------|
| `cli-web-stitch` | `stitch/` | batchexecute RPC | Google SSO + RPC codec (Nemo service) |
| `cli-web-reddit` | `reddit/` | REST JSON API (curl_cffi) | Public .json API, bot detection bypass |
| `cli-web-booking` | `booking/` | GraphQL + HTML (curl_cffi) | AWS WAF bypass, hybrid protocol |
| `cli-web-gai` | `gai/` | Browser-rendered (Playwright) | Headless rendering, AI search, no auth |
| `cli-web-notebooklm` | `notebooklm/` | batchexecute RPC | Google SSO + RPC codec |
| `cli-web-pexels` | `pexels/` | SSR + __NEXT_DATA__ (curl_cffi) | Cloudflare bypass, photo/video download |
| `cli-web-unsplash` | `unsplash/` | REST API (curl_cffi) | Public JSON API, anti-bot bypass |
| `cli-web-producthunt` | `producthunt/` | HTML scraping (curl_cffi) | Cloudflare bypass |
| `cli-web-futbin` | `futbin/` | HTML + JSON API | HTML scraping with httpx, market analysis/scan/arbitrage, trading signals |
| `cli-web-gh-trending` | `gh-trending/` | HTML scraping | Simple SSR, no auth |
| `cli-web-youtube` | `youtube/` | InnerTube REST API (httpx) | Internal POST API, no auth, search/video/channel |
| `cli-web-hackernews` | `hackernews/` | REST API (httpx) | Firebase + Algolia API, cookie auth, stories/search/users/upvote/submit/comment |
| `cli-web-codewiki` | `codewiki/` | batchexecute RPC (httpx) | No auth, Gemini-powered wiki/chat, repos/wiki/chat |
| `cli-web-chatgpt` | `chatgpt/` | REST API + Camoufox browser | OpenAI SSO, chat/ask, image generation/download, headless Cloudflare bypass |

## Reference Examples

The `skills/methodology/references/` directory contains concrete code templates that agents follow during generation:
- `exception-hierarchy-example.py` — Domain exception hierarchy with HTTP status mapping
- `client-architecture-example.py` — Namespaced sub-client pattern with auth retry
- `polling-backoff-example.py` — Exponential backoff polling and rate-limit retry
- `rich-output-example.py` — Rich progress bars, JSON error responses, table formatting
