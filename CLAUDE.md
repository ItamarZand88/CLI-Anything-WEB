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
├── scripts/                      # Shared utilities (repl_skin.py, parse-trace.py, etc.)
└── docs/                         # PUBLISHING.md, QUICKSTART.md
```

Generated CLIs live in their own directories (e.g., `futbin/agent-harness/`) with namespace packages under `cli_web/`.

## Pipeline Phases

The skill sequence is strictly ordered: `capture → methodology → testing → standards → DONE`

| Phase | Skill | What it does |
|-------|-------|-------------|
| 1 | capture | Site assessment + browser traffic recording (or public API shortcut) |
| 2 | methodology | Analyze traffic, design CLI architecture, implement code |
| 3 | testing | Write unit + E2E + subprocess tests |
| 4 | standards | Publish (`pip install -e .`), smoke test, generate skill |

### Site Profiles

Not all sites need the same pipeline path. Identify the profile early:
- **Auth + CRUD** (full pipeline): Google apps, Monday.com, Notion, Jira
- **Auth + read-only**: Dashboards, analytics viewers
- **No-auth + CRUD**: Sites with optional API key auth (Dev.to)
- **No-auth + read-only**: Hacker News, Wikipedia, npm — skip auth.py, skip write tests

## Tool Hierarchy (Strict)

1. **PRIMARY**: `npx @playwright/cli@latest` — handles auth, traffic capture, browser management
2. **FALLBACK**: `mcp__chrome-devtools__*` — only if playwright-cli unavailable
3. **NEVER**: `mcp__claude-in-chrome__*` — cannot capture request bodies

## Generated CLI Structure

Every generated CLI follows this exact layout under `<app>/agent-harness/`:

```
cli_web/                    # Namespace package (NO __init__.py)
└── <app>/                  # Sub-package (HAS __init__.py)
    ├── <app>_cli.py        # Click entry point + REPL default
    ├── core/               # exceptions.py, client.py, auth.py, session.py, models.py
    │   └── rpc/            # Optional: types.py, encoder.py, decoder.py (non-REST protocols)
    ├── commands/           # One file per resource group
    ├── utils/              # repl_skin.py (from plugin/scripts/), output.py, config.py
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
- **Auth login flow**: `login_browser()` MUST use `subprocess.Popen()`, not `subprocess.run()` — playwright-cli `open --persistent` blocks until browser closes, making `input()` unreachable.
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
- **HTTP client**: httpx (with typed exception mapping per status code)
- **HTML parsing**: BeautifulSoup4 (for SSR sites)
- **Output**: Rich (`>=13.0`) for tables, spinners, colored status; custom table formatting
- **Auth flow**: playwright-cli browser login → cookie extraction → `auth.json`; env var fallback for CI
- **Packaging**: `find_namespace_packages(include=["cli_web.*"])` in setup.py

## Protocol Detection

Generated CLIs handle multiple API patterns: REST, GraphQL, gRPC-Web, Google batchexecute, custom RPC. The methodology skill identifies the protocol type during traffic analysis and generates appropriate client code.

## Reference Examples

The `skills/methodology/references/` directory contains concrete code templates that agents follow during generation:
- `exception-hierarchy-example.py` — Domain exception hierarchy with HTTP status mapping
- `client-architecture-example.py` — Namespaced sub-client pattern with auth retry
- `polling-backoff-example.py` — Exponential backoff polling and rate-limit retry
- `rich-output-example.py` — Rich progress bars, JSON error responses, table formatting
