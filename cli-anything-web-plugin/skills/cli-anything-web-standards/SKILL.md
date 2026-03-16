---
name: cli-anything-web-standards
description: Use this skill when building, reviewing, or checking quality of a cli-web-* CLI package. Auto-activates during implementation (Phase 4), validation, code review, or whenever you need to verify a web CLI meets production standards. Also use when the user asks about required files for a cli-web package, directory structure for cli_web namespace packages, what a valid web CLI harness looks like, or when checking if an implementation is complete. Covers 50 checks across 8 categories.
version: 0.1.0
---

# CLI-Anything-Web Quality Standards

This skill contains the 50-check quality checklist for `cli-web-*` CLIs.
Use it as a self-check during implementation — don't wait for explicit
`/cli-anything-web:validate` invocation.

For the full methodology SOP, read `${CLAUDE_PLUGIN_ROOT}/HARNESS.md`.

## Package Structure

Every `cli-web-<app>` CLI must follow this layout:

```
<app-name>/
└── agent-harness/
    ├── <APP>.md               # API map, data model, auth scheme
    ├── setup.py               # PyPI config (find_namespace_packages)
    └── cli_web/               # Namespace package (NO __init__.py)
        └── <app>/             # Sub-package
            ├── __init__.py    # Required — marks as sub-package
            ├── README.md
            ├── <app>_cli.py   # Main CLI entry point
            ├── __main__.py
            ├── core/
            │   ├── client.py      # HTTP client, auth injection, backoff
            │   ├── auth.py        # Login, refresh, secure storage
            │   ├── session.py     # State, undo/redo
            │   └── models.py      # Typed response models
            ├── commands/          # Click command groups
            ├── utils/
            │   ├── repl_skin.py   # Copy from plugin scripts/
            │   ├── output.py      # JSON/table formatting
            │   └── config.py      # Config file management
            └── tests/
                ├── TEST.md        # Plan (Part 1) + Results (Part 2)
                ├── fixtures/      # Captured API responses for replay
                ├── test_core.py   # Unit tests (mocked HTTP)
                └── test_e2e.py    # E2E + subprocess tests
```

## 8-Category Checklist (50 checks)

### 1. Directory Structure (6 checks)

*(checked against `agent-harness/` root)*

- `agent-harness/cli_web/<app>/` exists
- `agent-harness/<APP>.md` exists (SOP at harness root)
- `cli_web/` has NO `__init__.py` (namespace package)
- `<app>/` HAS `__init__.py`
- `core/`, `commands/`, `utils/`, `tests/` all present (one atomic check)
- `setup.py` at `agent-harness/` root

### 2. Required Files (13 checks)

*(checked against `cli_web/<app>/`)*

`README.md`, `<app>_cli.py`, `__main__.py`,
`core/client.py`, `core/auth.py`, `core/session.py`, `core/models.py`,
`utils/repl_skin.py`, `utils/output.py`, `utils/config.py`,
`tests/TEST.md`, `tests/test_core.py`, `tests/test_e2e.py`

### 3. CLI Implementation (6 checks)

- Click framework with command groups (`@click.group`)
- `--json` flag on every command
- REPL mode via `invoke_without_command=True`
- `ReplSkin` used for banner, prompt, messages
- `auth` group with `login`, `status`, `refresh`
- Global session state (`pass_context=True`)

### 4. Core Modules (4 checks)

- `client.py`: centralized auth header injection, exponential backoff, JSON parsing
- `auth.py`: login, refresh, expiry check, secure storage (chmod 600)
- `session.py`: Session class with undo/redo stack
- `models.py`: typed response models
- If protocol is non-REST: `core/rpc/` exists with `types.py`, `encoder.py`, `decoder.py`

### 5. Test Standards (8 checks)

- `TEST.md` has both plan (Part 1) and results (Part 2)
- Unit tests use `unittest.mock.patch` — no real network
- E2E fixture tests replay from `tests/fixtures/`
- E2E live tests FAIL (not skip) without auth
- `TestCLISubprocess` class exists
- Uses `_resolve_cli("cli-web-<app>")` — no hardcoded paths
- Subprocess `_run` does NOT set `cwd`
- Supports `CLI_WEB_FORCE_INSTALLED=1`

### 6. Documentation (3 checks)

- `README.md`: installation, auth setup, command reference, examples
- `<APP>.md`: API map, data model, auth scheme, endpoint inventory
- No `HARNESS.md` inside app package (lives in plugin root)

### 7. PyPI Packaging (5 checks)

- `find_namespace_packages(include=["cli_web.*"])`
- Package name: `cli-web-<app>`
- Entry point: `cli-web-<app>=cli_web.<app>.<app>_cli:main`
- All imports use `cli_web.<app>.*` prefix
- `python_requires=">=3.10"`

### 8. Code Quality (5 checks)

- No syntax errors, no import errors
- No hardcoded auth tokens or API keys
- No hardcoded API base URLs or credentials in source
- No hardcoded session tokens, CSRF tokens, build labels, or session IDs (must be extracted dynamically)
- No bare `except:` blocks
- Error messages include actionable guidance

## Key Rules (from HARNESS.md)

These are non-negotiable standards:

- **Content generation downloads the result** — if the app generates content (audio,
  images, video), the CLI must trigger → poll → download → save. Support `--output`.
- **CAPTCHAs pause and prompt** — never crash or skip. Detect, tell user to solve in
  browser, wait for confirmation, retry.
- **Auth stored securely** — `chmod 600 auth.json`, never hardcode tokens
- **Tests fail without auth** — never skip, the CLI is useless without a live account
- **Every command supports `--json`** — agents need structured output
- **E2E includes subprocess tests** — test the installed package, not just source imports
- **REPL is the default** — `invoke_without_command=True`, branded banner via `ReplSkin`
- **Rate limits respected** — exponential backoff, never hammer endpoints
- **Response bodies verified** — never trust status 200 alone

## Naming Conventions

| Convention | Value |
|-----------|-------|
| CLI command | `cli-web-<app>` |
| Python namespace | `cli_web.<app>` |
| App-specific SOP | `<APP>.md` |
| App names | No hyphens. Underscores OK (`monday_com`) |

## Related

- **`/cli-anything-web:validate`** — Command to run the full 50-check validation
- **`${CLAUDE_PLUGIN_ROOT}/HARNESS.md`** — Full methodology SOP
- **`cli-anything-web-testing`** skill — Detailed testing patterns and code examples
- **`cli-anything-web-methodology`** skill — High-level pipeline overview
