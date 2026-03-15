# Web-Harness Standards Alignment Design

**Date:** 2026-03-15
**Status:** Approved

---

## Goal

Bring the `cli-anything-web-plugin` fully up to `cli-anything-plugin` standards by
porting the ReplSkin class, expanding command documentation depth, adding enforcement
rules to WEB-HARNESS.md, and adding missing plugin infrastructure files.

---

## Reference

The canonical standard is `C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything/cli-anything-plugin/`.
Every change below brings the web plugin to parity with that reference — adapted for
web app conventions (HTTP APIs, auth, traffic capture) rather than GUI app conventions.

---

## Change 1: scripts/repl_skin.py — Full Port

**Problem:** The current `scripts/repl_skin.py` extends `cmd.Cmd` — a completely
different architecture from CLI-Anything's `ReplSkin`. It lacks prompt_toolkit
integration, per-app accent colors, and most of the rich display methods.

**Solution:** Replace entirely with a port of CLI-Anything's `ReplSkin` class.

### API to implement (identical to CLI-Anything's):

```python
class ReplSkin:
    def __init__(self, app: str, version: str = "1.0.0", history_file: str | None = None)
    def print_banner(self)
    def prompt(self, project_name="", modified=False, context="") -> str
    def prompt_tokens(self, project_name="", modified=False, context="")
    def get_prompt_style(self)
    def create_prompt_session(self)
    def get_input(self, pt_session, project_name="", modified=False, context="") -> str
    def success(self, message: str)
    def error(self, message: str)
    def warning(self, message: str)
    def info(self, message: str)
    def hint(self, message: str)
    def section(self, title: str)
    def status(self, label: str, value: str)
    def status_block(self, items: dict, title: str = "")
    def progress(self, current: int, total: int, label: str = "")
    def table(self, headers: list, rows: list, max_col_width: int = 40)
    def help(self, commands: dict)
    def print_goodbye(self)
    def bottom_toolbar(self, items: dict)
```

### Web-specific adaptations:

**`_ACCENT_COLORS`** — replace GUI app names with web app names:
```python
_ACCENT_COLORS = {
    "monday":    "\033[38;5;214m",   # warm orange (Monday.com brand)
    "notion":    "\033[38;5;255m",   # near-white (Notion brand)
    "linear":    "\033[38;5;99m",    # purple (Linear brand)
    "jira":      "\033[38;5;27m",    # blue (Jira brand)
    "slack":     "\033[38;5;55m",    # aubergine (Slack brand)
    "github":    "\033[38;5;240m",   # dark gray (GitHub brand)
    "figma":     "\033[38;5;213m",   # pink (Figma brand)
    "airtable":  "\033[38;5;35m",    # green (Airtable brand)
    "asana":     "\033[38;5;196m",   # red (Asana brand)
    "trello":    "\033[38;5;39m",    # blue (Trello brand)
}
_DEFAULT_ACCENT = "\033[38;5;75m"    # sky blue fallback
```

**History file path:**
```python
hist_dir = Path.home() / f".cli-web-{self.app}"
```

**`_ANSI_256_TO_HEX`** — the full base dict is copied verbatim from CLI-Anything's `scripts/repl_skin.py`. Add these 10 new entries for the web app accent colors:
```python
214: "#ffaf00",  # monday
255: "#eeeeee",  # notion
99:  "#875fff",  # linear
27:  "#005fff",  # jira
55:  "#5f0087",  # slack
240: "#585858",  # github
213: "#ff87ff",  # figma
35:  "#00af5f",  # airtable
196: "#ff0000",  # asana
39:  "#00afff",  # trello
```

**Relationship to `utils/repl_skin.py`:** The generated `cli_web/<app>/utils/repl_skin.py` inside each app package is a verbatim copy of this `scripts/repl_skin.py`. The `validate` command's Category 2 check for `utils/repl_skin.py` verifies this copy exists in the app package. Implementers building new app harnesses must copy `${CLAUDE_PLUGIN_ROOT}/scripts/repl_skin.py` into `cli_web/<app>/utils/repl_skin.py`.

**Banner display name** — use `app.replace("_", " ").title()` so `monday_com` → `Monday Com`.

**Environment variable:** rename `CLI_ANYTHING_NO_COLOR` → `CLI_WEB_NO_COLOR` for
disabling color output.

**Unlisted methods** — behavior for all display methods not explicitly adapted above (`print_goodbye`, `prompt`, `prompt_tokens`, `get_prompt_style`, `create_prompt_session`, `get_input`, `success`, `error`, `warning`, `info`, `hint`, `section`, `status`, `status_block`, `progress`, `table`, `help`, `bottom_toolbar`) is identical to CLI-Anything's implementation — port verbatim.

All other ANSI codes, box-drawing chars, prompt_toolkit integration, and color detection
logic are identical to CLI-Anything's implementation.

---

## Change 2: commands/validate.md — 8-Category Structure

**Problem:** Current validate command has a basic flat checklist. CLI-Anything's has
8 named categories with specific check counts and a `N/N checks passed` summary.

**Solution:** Rewrite to 8 categories, each with specific numbered checks, matching
CLI-Anything's depth. Web-specific categories differ from CLI-Anything's:

### Category structure:

**1. Directory Structure**
- `agent-harness/cli_web/<app>/` exists
- `cli_web/` has NO `__init__.py` (namespace package — no `__init__.py` required)
- `<app>/` HAS `__init__.py`
- `core/`, `commands/`, `utils/`, `tests/` present
- `setup.py` uses `find_namespace_packages`

**2. Required Files**
- `README.md`, `<app>_cli.py`, `__main__.py`
- `core/client.py`, `core/auth.py`, `core/session.py`, `core/models.py`
- `utils/repl_skin.py`, `utils/output.py`, `utils/config.py`
- `tests/TEST.md`, `tests/test_core.py`, `tests/test_e2e.py`
- `<APP>.md` (software-specific SOP)

**3. CLI Implementation Standards**
- Uses Click framework with command groups
- `--json` flag on every command
- REPL mode when run without arguments — validated by static source inspection: grep `<app>_cli.py` for `invoke_without_command=True`
- `repl_skin.py` used for banner, prompt, messages
- `auth` command group with `login`, `status`, `refresh`
- Has global session state (e.g. `pass_context=True` or module-level session object)

**4. Core Module Standards**
- `client.py`: centralized auth header injection, exponential backoff, JSON parsing
- `auth.py`: login, refresh, expiry check, secure storage (chmod 600)
- `session.py`: Session class with undo/redo stack
- `models.py`: typed response models

**5. Test Standards**
- `TEST.md` has both plan (Part 1) and results (Part 2)
- Unit tests use `unittest.mock.patch` for HTTP — no real network
- E2E fixture tests replay captured responses from `tests/fixtures/`
- E2E live tests require auth — FAIL (not skip) without it
- `test_e2e.py` has `TestCLISubprocess` class
- Uses `_resolve_cli("cli-web-<app>")` — no hardcoded paths
- Subprocess `_run` does NOT set `cwd`
- Supports `CLI_WEB_FORCE_INSTALLED=1`

**6. Documentation Standards**
- `README.md`: installation, auth setup, command reference, examples
- `<APP>.md`: API map, data model, auth scheme, endpoint inventory
- No duplicate `WEB-HARNESS.md` (reference plugin's copy)

**7. PyPI Packaging Standards**
- `find_namespace_packages(include=["cli_web.*"])`
- Package name: `cli-web-<app>`
- Entry point: `cli-web-<app>=cli_web.<app>.<app>_cli:main`
- All imports use `cli_web.<app>.*` prefix
- `python_requires=">=3.10"`

**8. Code Quality**
- No syntax errors, no import errors
- No hardcoded auth tokens or API keys
- No hardcoded API base URLs or credential values in source
- No bare `except:` blocks
- Proper error messages include actionable guidance

### Report format (matching CLI-Anything):
```
Web Harness Validation Report
App: monday
Path: ./monday/agent-harness/cli_web/monday

Directory Structure  (5/5 checks passed)
Required Files       (14/14 files present)
CLI Standards        (6/6 standards met)
Core Modules         (4/4 standards met)
Test Standards       (8/8 standards met)
Documentation        (3/3 standards met)
PyPI Packaging       (5/5 standards met)
Code Quality         (5/5 checks passed)

Overall: PASS (50/50 checks)
```

---

## Change 3: WEB-HARNESS.md — Add Rules + Testing Strategy + Phase 7 Detail

**Problem:** WEB-HARNESS.md lacks three sections that HARNESS.md has: a bold
enforcement Rules section, a detailed Testing Strategy section, and a detailed
Phase 7 namespace package explanation.

### 3a. Rules section (after Critical Lessons, before Naming Conventions)

Same bold-rule style as HARNESS.md:

- **Auth credentials MUST be stored securely.** `chmod 600 auth.json`. Never hardcode tokens in source. If auth file missing, CLI errors with clear instructions — never falls back to unauthenticated requests.
- **Tests MUST fail (not skip) when auth is missing.** The CLI is useless without a live account. Tests that skip on missing auth give false confidence.
- **Every command MUST support `--json`.** Agents consume structured output. Human-readable is optional; machine-readable is required.
- **E2E tests MUST include subprocess tests** via `_resolve_cli("cli-web-<app>")`. Tests must run against the installed package, not just source imports.
- **Every `cli_web/<app>/` MUST contain `README.md`** with auth setup, install steps, and usage examples.
- **Every `cli_web/<app>/tests/` MUST contain `TEST.md`** with plan and results.
- **Every CLI MUST use the unified REPL skin** (`repl_skin.py` from `${CLAUDE_PLUGIN_ROOT}/scripts/repl_skin.py`). REPL MUST be the default when invoked without a subcommand.
- **Rate limits MUST be respected.** Never retry without backoff. Never hammer endpoints.

### 3b. Testing Strategy section (after Rules)

4-layer table:

| Layer | File | What it tests |
|-------|------|--------------|
| Unit tests | `test_core.py` | Core functions with mocked HTTP. No real network. Fast, deterministic. |
| E2E fixture tests | `test_e2e.py` | Full command flow replaying captured responses from `tests/fixtures/`. Verifies parsing logic. |
| E2E live tests | `test_e2e.py` | Real API calls. Require auth — FAIL without it. Create/read/update/delete cycle. |
| CLI subprocess | `test_e2e.py` | Installed `cli-web-<app>` via `_resolve_cli()`. Full workflow end-to-end. |

With `_resolve_cli` pattern shown in code:
```python
def _resolve_cli(name):
    force = os.environ.get("CLI_WEB_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-web-", "cli_web.") + "." + name.split("-")[-1] + "_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]
```

**App naming convention note:** This fallback uses `name.split("-")[-1]` to derive the module name, which works correctly for single-segment app names like `cli-web-monday` → `cli_web.monday.monday_cli`. For multi-segment names like `cli-web-monday-com`, the fallback produces `cli_web.monday-com.com_cli` which is invalid. Convention: **app names must contain no hyphens**. Underscores are permitted (e.g., `cli-web-monday_com` → `cli_web.monday_com.monday_com_cli`). Valid examples: `monday`, `notion`, `jira`, `monday_com`.

### 3c. Phase 7 expansion

Add the namespace package explanation from HARNESS.md (adapted for `cli_web.*`):
- Why namespace packages: multiple `cli-web-*` CLIs coexist in same Python environment
- `cli_web/` has NO `__init__.py` — this is the rule that enables it
- `find_namespace_packages(include=["cli_web.*"])` — not `find_packages`
- Install verification commands with `CLI_WEB_FORCE_INSTALLED=1`

---

## Change 4: Remaining File Fixes

### README.md
Remove the `claude mcp add` / Claude Desktop marketplace-style install step from the Quick Start section. Replace with:
```bash
cp -r /path/to/cli-anything-web-plugin ~/.claude/plugins/web-harness
/reload-plugins
/help web-harness
```
Also update the Commands table to include `web-harness:list` with description: "List all installed and generated `cli-web-*` CLIs".

### commands/refine.md
- Insert a new step between current Step 3 (Gap analysis) and Step 4 (Record new traffic): "Present gap report to user and confirm which gaps to address before proceeding." Verify the current step count before renumbering (expected: 9 steps based on current file content). The new step becomes Step 4, and all subsequent steps shift by one (existing Steps 4–9 become Steps 5–10).
- Add **Success Criteria** section (matching CLI-Anything's refine.md)
- Add **Notes** section: refine is incremental, never removes commands, present before implementing

### commands/test.md
- Modify existing Step 3 (currently: "If installed, also run subprocess tests: `CLI_WEB_FORCE_INSTALLED=1 python3 -m pytest ...`") to include: after running, verify subprocess backend by checking that `[_resolve_cli] Using installed command:` appears in the output (confirms the installed package is being tested, not source fallback)
- Add **Failure Handling** section: show failures, do NOT update TEST.md, suggest fixes, offer to re-run

### commands/web-harness.md
- Add **Success Criteria** section with these 9 items (adapted from CLI-Anything's cli-anything.md):
  1. All core modules are implemented and functional (`client.py`, `auth.py`, `session.py`, `models.py`)
  2. CLI supports both one-shot commands and REPL mode
  3. `--json` output mode works for all commands
  4. All tests pass (100% pass rate)
  5. Subprocess tests use `_resolve_cli()` and pass with `CLI_WEB_FORCE_INSTALLED=1`
  6. TEST.md contains both plan and results
  7. README.md documents installation and usage
  8. `setup.py` is created and local installation works
  9. CLI is available in PATH as `cli-web-<app>`
- Add **Output Structure** directory tree showing the generated package layout:
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
              │   ├── client.py
              │   ├── auth.py
              │   ├── session.py
              │   └── models.py
              ├── utils/
              │   ├── repl_skin.py
              │   ├── output.py
              │   └── config.py
              └── tests/
                  ├── TEST.md
                  ├── test_core.py
                  └── test_e2e.py
  ```

### verify-plugin.sh (new file)
Web-specific plugin structure checker. Reports ALL checks (no fail-fast). Prints one line per check: `[PASS]` or `[FAIL]` prefix followed by the check description. Prints a summary line at the end: `X/Y checks passed`. Exits 0 if all checks pass, exits 1 if any check fails. This is a static shell script — not generated. Checks:
- `.claude-plugin/plugin.json` valid JSON
- `WEB-HARNESS.md` exists
- All 6 command files exist: `commands/web-harness.md`, `commands/record.md`, `commands/refine.md`, `commands/test.md`, `commands/validate.md`, `commands/list.md`
- `scripts/repl_skin.py` exists
- `scripts/setup-web-harness.sh` executable
- `.mcp.json` exists and valid JSON
- `skills/web-harness-methodology/SKILL.md` exists
- `PUBLISHING.md` exists
- `README.md` exists

### LICENSE (new file)
Static MIT License file. Year: 2026. Copyright holder: "CLI-Anything Contributors". The implementer writes this file once with those values — it is not generated at runtime.

---

## Complete File Inventory

| File | Action |
|------|--------|
| `scripts/repl_skin.py` | Complete rewrite — port CLI-Anything's ReplSkin, web accent colors |
| `commands/validate.md` | Major rewrite — 8-category structure, N/N format |
| `WEB-HARNESS.md` | Add Rules section, Testing Strategy section, expand Phase 7 |
| `README.md` | Remove marketplace references, add list command to table |
| `commands/refine.md` | Add gap-present step, Success Criteria, Notes |
| `commands/test.md` | Add subprocess verification step, Failure Handling section |
| `commands/web-harness.md` | Add Success Criteria, Output Structure |
| `commands/list.md` | No change — already implemented in previous session |
| `verify-plugin.sh` | New file — plugin structure checker |
| `LICENSE` | New file — MIT |

---

## Out of Scope

- Changes to `WEB-HARNESS.md` phases 1–6 methodology (already correct)
- Changes to `skills/` reference files (already good)
- Changes to `.claude-plugin/plugin.json` (already richer than CLI-Anything's)
- Changes to `.mcp.json` (correct)
- Changes to `scripts/setup-web-harness.sh` (already updated in previous session)
- Changes to `PUBLISHING.md` or `QUICKSTART.md` (already updated in previous session)
- Changes to `commands/list.md` (already implemented in previous session — verified complete)
