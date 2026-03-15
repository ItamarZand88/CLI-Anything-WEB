# Production-Readiness Gap Analysis: cli-web-notebooklm

Evaluated against the 8-category, 50-check standard defined in `HARNESS.md`
(the authoritative SOP for all `cli-web-*` packages).

---

## Summary

Your current structure covers roughly 7 of the 50 required checks. Below is the
complete list of every missing file and every missing standard.

---

## Category 1: Directory Structure (6 checks)

Current state: `notebooklm/agent-harness/` with `setup.py` and `cli_web/notebooklm/`.

| # | Check | Status |
|---|-------|--------|
| 1 | `agent-harness/cli_web/notebooklm/` exists | PASS |
| 2 | `agent-harness/NOTEBOOKLM.md` exists | PASS (you have `NOTEBOOKLM.md`) |
| 3 | `cli_web/` has NO `__init__.py` (namespace package rule) | UNKNOWN — not shown, treat as a risk |
| 4 | `notebooklm/` HAS `__init__.py` | PASS (you have `__init__.py`) |
| 5 | `core/`, `commands/`, `utils/`, `tests/` all present inside `cli_web/notebooklm/` | FAIL — `commands/` and `utils/` are missing |
| 6 | `setup.py` at `agent-harness/` root | PASS |

**Missing directories:**
- `cli_web/notebooklm/commands/` — Click command group files, one per API resource
- `cli_web/notebooklm/utils/` — output formatter, config manager, REPL skin copy

**Risk: namespace package integrity.** Verify that `cli_web/__init__.py` does NOT exist.
If it does, the namespace package is broken and multiple `cli-web-*` packages cannot
coexist in the same Python environment. Remove it if present.

---

## Category 2: Required Files (13 checks)

| File | Status |
|------|--------|
| `cli_web/notebooklm/README.md` | MISSING |
| `cli_web/notebooklm/notebooklm_cli.py` | PASS |
| `cli_web/notebooklm/__main__.py` | MISSING |
| `cli_web/notebooklm/core/client.py` | PASS |
| `cli_web/notebooklm/core/auth.py` | PASS |
| `cli_web/notebooklm/core/session.py` | MISSING |
| `cli_web/notebooklm/core/models.py` | MISSING |
| `cli_web/notebooklm/utils/repl_skin.py` | MISSING |
| `cli_web/notebooklm/utils/output.py` | MISSING |
| `cli_web/notebooklm/utils/config.py` | MISSING |
| `cli_web/notebooklm/tests/TEST.md` | MISSING |
| `cli_web/notebooklm/tests/test_core.py` | PASS |
| `cli_web/notebooklm/tests/test_e2e.py` | MISSING |

**9 files are missing.** Complete list:
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

## Category 3: CLI Implementation Standards (6 checks)

| Check | Status |
|-------|--------|
| Uses Click framework with command groups (`@click.group`) | UNKNOWN — source not shown |
| `--json` flag on every command | UNKNOWN — likely missing (not mentioned) |
| REPL mode — `invoke_without_command=True` in `notebooklm_cli.py` | UNKNOWN — likely missing |
| `repl_skin.py` used for banner, prompt, and messages | FAIL — `utils/repl_skin.py` is missing |
| `auth` command group with `login`, `status`, `refresh` subcommands | UNKNOWN — likely missing |
| Global session state (`pass_context=True` or module-level session object) | FAIL — `session.py` is missing |

**Standards to implement in `notebooklm_cli.py`:**
- Add `invoke_without_command=True` to the main Click group so bare invocation enters REPL
- Add `--json` as an option on every command (not just the group)
- Add an `auth` command group with three subcommands: `login`, `status`, `refresh`
- Wire `pass_context=True` or a module-level session object for stateful REPL

---

## Category 4: Core Module Standards (4 checks)

| Module | Status |
|--------|--------|
| `client.py`: centralized auth header injection, exponential backoff, JSON parsing | UNKNOWN |
| `auth.py`: login, refresh, expiry check, secure storage (`chmod 600`) | UNKNOWN |
| `session.py`: Session class with undo/redo stack | FAIL — file does not exist |
| `models.py`: typed response models | FAIL — file does not exist |

**What to build:**

`core/session.py` — Session class with:
- Current context (active notebook, workspace)
- Undo/redo stack for mutating operations
- Output format preference

`core/models.py` — Typed response models (dataclasses or Pydantic) for:
- Notebook, Note, Source, Citation, Audio Overview
- All list response wrappers

`core/client.py` must have (verify these are present):
- A single method that injects auth headers on every request
- Exponential backoff on 429 / 5xx responses
- Automatic JSON parsing with error on non-JSON bodies

`core/auth.py` must have (verify these are present):
- `login()` — stores token to `~/.config/cli-web-notebooklm/auth.json`
- `chmod 600` on the auth file after writing
- `refresh()` — refreshes token before expiry
- `is_expired()` — expiry check used before every request
- Never falls back to unauthenticated requests when auth file is missing

---

## Category 5: Test Standards (8 checks)

| Check | Status |
|-------|--------|
| `TEST.md` has both plan (Part 1) and results (Part 2) | FAIL — file missing |
| Unit tests use `unittest.mock.patch` for HTTP — no real network | UNKNOWN |
| E2E fixture tests replay captured responses from `tests/fixtures/` | FAIL — fixtures dir missing |
| E2E live tests require auth — FAIL (not skip) without it | FAIL — `test_e2e.py` missing |
| `test_e2e.py` has `TestCLISubprocess` class | FAIL — `test_e2e.py` missing |
| Uses `_resolve_cli("cli-web-notebooklm")` — no hardcoded paths | FAIL — `test_e2e.py` missing |
| Subprocess `_run` does NOT set `cwd` | FAIL — `test_e2e.py` missing |
| Supports `CLI_WEB_FORCE_INSTALLED=1` | FAIL — not implemented |

**Missing items:**
- `cli_web/notebooklm/tests/TEST.md` — must be written in two parts: plan first (before writing test code), results appended after running
- `cli_web/notebooklm/tests/fixtures/` — directory of captured NotebookLM API responses for fixture replay
- `cli_web/notebooklm/tests/test_e2e.py` — must contain:
  - Fixture replay tests (no network)
  - Live tests that call the real API (FAIL without auth — never skip)
  - `TestCLISubprocess` class using `_resolve_cli("cli-web-notebooklm")`
  - `_run()` helper that does NOT set `cwd`
  - `CLI_WEB_FORCE_INSTALLED=1` support

**TEST.md two-part structure (mandatory process):**
1. Write Part 1 (test plan) BEFORE writing any test code — list every planned test, edge cases, workflow scenarios
2. Append Part 2 (results) AFTER running the suite — full `pytest -v --tb=no` output plus summary

**Response verification requirement** (applies to all tests):
- Never trust HTTP 200 alone
- For create: verify returned entity contains submitted field values
- For read: verify entity ID matches requested ID
- For update: verify changed fields reflect new values
- For delete: verify subsequent read returns 404
- Print IDs for manual verification: `print(f"[verify] Created notebook id={data['id']}")`

---

## Category 6: Documentation Standards (3 checks)

| Check | Status |
|-------|--------|
| `README.md`: installation, auth setup, command reference, examples | FAIL — file missing |
| `NOTEBOOKLM.md`: API map, data model, auth scheme, endpoint inventory | PASS (file exists) |
| No `HARNESS.md` copy inside app package | PASS (not present) |

**`README.md` must include:**
- Installation: `pip install -e .` and verification with `which cli-web-notebooklm`
- Auth setup: how to run `cli-web-notebooklm auth login` and where credentials are stored
- Full command reference with every subcommand and its flags
- At least 3 real usage examples with expected output

---

## Category 7: PyPI Packaging Standards (5 checks)

| Check | Status |
|-------|--------|
| `find_namespace_packages(include=["cli_web.*"])` in setup.py | UNKNOWN — setup.py not shown |
| Package name: `cli-web-notebooklm` | UNKNOWN |
| Entry point: `cli-web-notebooklm=cli_web.notebooklm.notebooklm_cli:main` | UNKNOWN |
| All imports use `cli_web.notebooklm.*` prefix | UNKNOWN |
| `python_requires=">=3.10"` | UNKNOWN |

**Review `setup.py` against these exact requirements:**

```python
from setuptools import setup, find_namespace_packages

setup(
    name="cli-web-notebooklm",
    version="0.1.0",
    packages=find_namespace_packages(include=["cli_web.*"]),
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "cli-web-notebooklm=cli_web.notebooklm.notebooklm_cli:main",
        ],
    },
    install_requires=[
        "click>=8.0",
        "httpx",
        "prompt_toolkit",
        "rich",
    ],
)
```

Critical: use `find_namespace_packages`, NOT `find_packages`. Using `find_packages`
will break namespace coexistence with other `cli-web-*` packages.

---

## Category 8: Code Quality (5 checks)

| Check | Status |
|-------|--------|
| No syntax errors, no import errors | UNKNOWN — cannot verify without running |
| No hardcoded auth tokens or API keys in source | UNKNOWN |
| No hardcoded API base URLs or credential values | UNKNOWN |
| No bare `except:` blocks | UNKNOWN |
| Error messages include actionable guidance | UNKNOWN |

**Run before shipping:**
```bash
python3 -c "import cli_web.notebooklm"
grep -r "except:" cli_web/notebooklm/
grep -rn "api_key\|token\s*=\s*['\"]" cli_web/notebooklm/
```

All error messages must tell the user what to do next, e.g.:
`"Auth token missing. Run: cli-web-notebooklm auth login"` — not just
`"Unauthorized"`.

---

## Complete List of Missing Files

```
cli_web/notebooklm/
├── README.md                         MISSING
├── __main__.py                       MISSING
├── core/
│   ├── session.py                    MISSING
│   └── models.py                     MISSING
├── commands/                         MISSING (entire directory)
│   ├── __init__.py                   MISSING
│   └── <resource>.py                 MISSING (one per API resource)
├── utils/                            MISSING (entire directory)
│   ├── __init__.py                   MISSING
│   ├── repl_skin.py                  MISSING
│   ├── output.py                     MISSING
│   └── config.py                     MISSING
└── tests/
    ├── TEST.md                       MISSING
    ├── fixtures/                     MISSING (entire directory)
    └── test_e2e.py                   MISSING
```

Also verify `cli_web/__init__.py` does NOT exist (it must be absent for namespace packages).

---

## Complete List of Missing Standards

1. **REPL mode** — `notebooklm_cli.py` must use `invoke_without_command=True`; bare invocation enters REPL with branded banner
2. **`--json` flag** — every single command must accept `--json` for machine-readable output
3. **`auth` command group** — `login`, `status`, `refresh` subcommands are mandatory
4. **Secure credential storage** — `chmod 600` on `auth.json`; no fallback to unauthenticated requests
5. **REPL skin** — `utils/repl_skin.py` must be copied from the plugin's `scripts/repl_skin.py`; ReplSkin must be used for banner, prompts, and all user-facing messages
6. **Session state** — `core/session.py` with undo/redo stack
7. **Typed models** — `core/models.py` with dataclasses or Pydantic models for all response types
8. **Exponential backoff** — `client.py` must retry with backoff on 429 and 5xx
9. **Fixture replay tests** — `test_e2e.py` must replay captured responses from `tests/fixtures/` without hitting the network
10. **Live E2E tests that FAIL (not skip) on missing auth** — using `pytest.fail()`, not `pytest.skip()`
11. **Subprocess tests** — `TestCLISubprocess` class using `_resolve_cli("cli-web-notebooklm")`; `_run()` must not set `cwd`
12. **`CLI_WEB_FORCE_INSTALLED=1` support** — `_resolve_cli()` must raise `RuntimeError` (not fall back) when this env var is set and the command is not in PATH
13. **TEST.md two-part structure** — Part 1 (plan, written before test code) and Part 2 (results, appended after running)
14. **Response body verification** — never trust HTTP 200; always assert expected fields in the response body
15. **CRUD round-trip requirement** — every E2E live test must create → read back → verify; tests that only create give false confidence
16. **Namespace package setup** — `find_namespace_packages(include=["cli_web.*"])` in `setup.py`; correct entry point name and path; `python_requires=">=3.10"`
17. **README.md** — must cover install, auth setup, full command reference, and usage examples
18. **No bare `except:` blocks** — catch specific exceptions; all errors must include actionable next steps

---

## Estimated Check Score Against HARNESS.md

| Category | Passing | Total |
|----------|---------|-------|
| Directory Structure | ~3 | 6 |
| Required Files | 4 | 13 |
| CLI Standards | ~1 | 6 |
| Core Modules | ~2 | 4 |
| Test Standards | 0 | 8 |
| Documentation | 1 | 3 |
| PyPI Packaging | ~2 | 5 |
| Code Quality | unknown | 5 |
| **Total** | **~13** | **50** |

The package is not close to production-ready. The largest single gaps are:
the entire `utils/` layer (repl_skin, output formatter, config), the `commands/`
directory, `session.py`, `models.py`, all of `test_e2e.py`, `TEST.md`, and the
REPL/`--json` standards throughout `notebooklm_cli.py`.
