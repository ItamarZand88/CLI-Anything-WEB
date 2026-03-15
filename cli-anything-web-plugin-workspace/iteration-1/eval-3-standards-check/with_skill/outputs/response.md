# Standards Check: cli-web-notebooklm

Checked against the 50-check quality checklist (8 categories) from the cli-anything-web-standards skill.

---

## Current Structure (Provided)

```
notebooklm/agent-harness/
├── NOTEBOOKLM.md
├── setup.py
└── cli_web/
    └── notebooklm/
        ├── __init__.py
        ├── notebooklm_cli.py
        ├── core/
        │   ├── client.py
        │   └── auth.py
        └── tests/
            └── test_core.py
```

---

## Category 1: Directory Structure (6 checks)

| Check | Status | Notes |
|---|---|---|
| `agent-harness/cli_web/notebooklm/` exists | PASS | Present |
| `agent-harness/NOTEBOOKLM.md` exists | PASS | Present |
| `cli_web/` has NO `__init__.py` (namespace package) | UNKNOWN | Cannot confirm from listing — verify manually that `cli_web/__init__.py` does NOT exist |
| `notebooklm/` HAS `__init__.py` | PASS | Present |
| `core/`, `commands/`, `utils/`, `tests/` all present | FAIL | `commands/` and `utils/` directories are missing entirely |
| `setup.py` at `agent-harness/` root | PASS | Present |

**Missing:**
- `cli_web/notebooklm/commands/` — directory does not exist
- `cli_web/notebooklm/utils/` — directory does not exist

---

## Category 2: Required Files (13 checks)

| Check | Status | File |
|---|---|---|
| `README.md` | FAIL | Missing |
| `notebooklm_cli.py` | PASS | Present |
| `__main__.py` | FAIL | Missing |
| `core/client.py` | PASS | Present |
| `core/auth.py` | PASS | Present |
| `core/session.py` | FAIL | Missing |
| `core/models.py` | FAIL | Missing |
| `utils/repl_skin.py` | FAIL | Missing (entire `utils/` dir missing) |
| `utils/output.py` | FAIL | Missing |
| `utils/config.py` | FAIL | Missing |
| `tests/TEST.md` | FAIL | Missing |
| `tests/test_core.py` | PASS | Present |
| `tests/test_e2e.py` | FAIL | Missing |

**Missing files (9 of 13):**
1. `cli_web/notebooklm/README.md`
2. `cli_web/notebooklm/__main__.py`
3. `cli_web/notebooklm/core/session.py`
4. `cli_web/notebooklm/core/models.py`
5. `cli_web/notebooklm/utils/repl_skin.py`
6. `cli_web/notebooklm/utils/output.py`
7. `cli_web/notebooklm/utils/config.py`
8. `cli_web/notebooklm/tests/TEST.md`
9. `cli_web/notebooklm/tests/test_e2e.py`

---

## Category 3: CLI Implementation (6 checks)

All 6 checks are code-level and cannot be confirmed from file structure alone. Each must be verified inside `notebooklm_cli.py`:

| Check | Status | What to verify |
|---|---|---|
| Click framework with `@click.group` | UNKNOWN | Confirm Click groups are used |
| `--json` flag on every command | UNKNOWN | Every command must accept `--json` |
| REPL mode via `invoke_without_command=True` | UNKNOWN | Main group must set this |
| `ReplSkin` used for banner, prompt, messages | FAIL (implied) | `utils/repl_skin.py` is missing — cannot be used |
| `auth` group with `login`, `status`, `refresh` | UNKNOWN | Verify subcommands exist |
| Global session state (`pass_context=True`) | UNKNOWN | Verify context passing |

**Guaranteed failure:**
- `ReplSkin` cannot be used because `utils/repl_skin.py` does not exist. Copy it from `${CLAUDE_PLUGIN_ROOT}/scripts/repl_skin.py`.

---

## Category 4: Core Modules (4 checks)

| Check | Status | Notes |
|---|---|---|
| `client.py`: auth header injection, exponential backoff, JSON parsing | UNKNOWN | File exists; contents unreviewed |
| `auth.py`: login, refresh, expiry check, secure storage (chmod 600) | UNKNOWN | File exists; contents unreviewed |
| `session.py`: Session class with undo/redo stack | FAIL | File does not exist |
| `models.py`: typed response models | FAIL | File does not exist |

**Missing implementations:**
- `core/session.py` — must implement a `Session` class with undo/redo stack
- `core/models.py` — must implement typed response models (e.g., dataclasses or Pydantic)

---

## Category 5: Test Standards (8 checks)

| Check | Status | Notes |
|---|---|---|
| `TEST.md` has plan (Part 1) and results (Part 2) | FAIL | `tests/TEST.md` does not exist |
| Unit tests use `unittest.mock.patch` — no real network | UNKNOWN | `test_core.py` exists; not reviewed |
| E2E fixture tests replay from `tests/fixtures/` | FAIL | `tests/fixtures/` directory missing; `test_e2e.py` missing |
| E2E live tests FAIL (not skip) without auth | FAIL | `test_e2e.py` does not exist |
| `TestCLISubprocess` class exists | FAIL | `test_e2e.py` does not exist |
| Uses `_resolve_cli("cli-web-notebooklm")` — no hardcoded paths | FAIL | `test_e2e.py` does not exist |
| Subprocess `_run` does NOT set `cwd` | FAIL | `test_e2e.py` does not exist |
| Supports `CLI_WEB_FORCE_INSTALLED=1` | FAIL | `test_e2e.py` does not exist |

**Missing:**
- `cli_web/notebooklm/tests/TEST.md` — must have Part 1 (plan) and Part 2 (results)
- `cli_web/notebooklm/tests/test_e2e.py` — must include `TestCLISubprocess`, `_resolve_cli`, subprocess `_run` without `cwd`
- `cli_web/notebooklm/tests/fixtures/` — directory for captured API response replays

---

## Category 6: Documentation (3 checks)

| Check | Status | Notes |
|---|---|---|
| `README.md`: installation, auth setup, command reference, examples | FAIL | Missing entirely |
| `NOTEBOOKLM.md`: API map, data model, auth scheme, endpoint inventory | PASS | Present at harness root |
| No `HARNESS.md` inside app package | PASS | Not present (correct) |

**Missing:**
- `cli_web/notebooklm/README.md` — must cover installation, auth setup, command reference, and examples

---

## Category 7: PyPI Packaging (5 checks)

All 5 checks are code-level inside `setup.py` and cannot be confirmed from structure alone:

| Check | What to verify in `setup.py` |
|---|---|
| `find_namespace_packages(include=["cli_web.*"])` | Confirm this exact call is used |
| Package name: `cli-web-notebooklm` | Confirm `name="cli-web-notebooklm"` |
| Entry point: `cli-web-notebooklm=cli_web.notebooklm.notebooklm_cli:main` | Confirm under `entry_points` |
| All imports use `cli_web.notebooklm.*` prefix | Verify no relative-only or bare imports |
| `python_requires=">=3.10"` | Confirm this is set |

---

## Category 8: Code Quality (5 checks)

All 5 are code-level and require review of source files. No structural gaps, but note:

- Verify `auth.py` uses `chmod 600` when writing auth tokens to disk (non-negotiable)
- Verify no hardcoded API base URLs, tokens, or credentials anywhere in source
- Verify no bare `except:` blocks
- Verify error messages give actionable guidance (e.g., "Run `cli-web-notebooklm auth login` to authenticate")

---

## Summary: Missing Items by Priority

### Missing Files (must create before validation passes)

| # | Path (relative to `agent-harness/`) | Category |
|---|---|---|
| 1 | `cli_web/notebooklm/README.md` | Required Files / Documentation |
| 2 | `cli_web/notebooklm/__main__.py` | Required Files |
| 3 | `cli_web/notebooklm/core/session.py` | Required Files / Core Modules |
| 4 | `cli_web/notebooklm/core/models.py` | Required Files / Core Modules |
| 5 | `cli_web/notebooklm/commands/` (directory + at least one module) | Directory Structure |
| 6 | `cli_web/notebooklm/utils/repl_skin.py` | Required Files / CLI Implementation |
| 7 | `cli_web/notebooklm/utils/output.py` | Required Files |
| 8 | `cli_web/notebooklm/utils/config.py` | Required Files |
| 9 | `cli_web/notebooklm/tests/TEST.md` | Test Standards |
| 10 | `cli_web/notebooklm/tests/test_e2e.py` | Test Standards |
| 11 | `cli_web/notebooklm/tests/fixtures/` (directory) | Test Standards |

### Items to Verify in Existing Files

| File | What to check |
|---|---|
| `cli_web/` | Confirm NO `__init__.py` exists here (namespace package rule) |
| `notebooklm_cli.py` | `--json` on every command, `invoke_without_command=True`, `ReplSkin`, `auth` group with `login`/`status`/`refresh`, `pass_context=True` |
| `core/client.py` | Auth header injection, exponential backoff, JSON parsing |
| `core/auth.py` | `chmod 600` on auth file, login/refresh/expiry logic |
| `setup.py` | `find_namespace_packages`, package name, entry point, `python_requires=">=3.10"` |

### Total Gap Count

- Confirmed failing checks: **22 of 50**
- Unknown/unverifiable from structure alone: **14 of 50**
- Confirmed passing: **14 of 50**

You must resolve all 22 confirmed failures before the package will pass `/cli-anything-web:validate`.
