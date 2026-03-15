# Web-Harness Standards Alignment Design

**Date:** 2026-03-15
**Status:** In Revision

---

## Goal

Bring `cli-anything-web-plugin` to production quality by porting the ReplSkin class,
filling methodology gaps in the pipeline SOP, expanding command documentation depth,
removing comparison framing in favor of standalone identity, and adding missing plugin
infrastructure files.

The quality bar is defined by the reference repo at
`C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything/cli-anything-plugin/`.
We use that repo as a proven quality standard — not as a parent or dependency. The web
plugin stands entirely on its own; the reference is used only to measure depth and
completeness.

---

## Change 1: scripts/repl_skin.py — Full Port

**Problem:** The current `scripts/repl_skin.py` extends `cmd.Cmd` — a completely
different architecture. It lacks prompt_toolkit integration, per-app accent colors,
and most of the rich display methods.

**Solution:** Replace entirely with a proper `ReplSkin` class.

### API to implement:

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

**`_ACCENT_COLORS`** — web app brand colors:
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

**`_ANSI_256_TO_HEX`** — **Prerequisite: the reference repo at
`C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything/cli-anything-plugin/`
MUST be accessible before implementing this change.** Copy the full base dict verbatim
from `scripts/repl_skin.py` in that repo. Add these 10 new entries for the web app
accent colors:
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

**Relationship to `utils/repl_skin.py`:** The generated `cli_web/<app>/utils/repl_skin.py`
inside each app package is a verbatim copy of this `scripts/repl_skin.py`. The `validate`
command's Category 2 check for `utils/repl_skin.py` verifies this copy exists. Implementers
building new app harnesses must copy `${CLAUDE_PLUGIN_ROOT}/scripts/repl_skin.py` into
`cli_web/<app>/utils/repl_skin.py`.

**Banner display name** — use `app.replace("_", " ").title()` so `monday_com` → `Monday Com`.

**Environment variable:** rename `CLI_ANYTHING_NO_COLOR` → `CLI_WEB_NO_COLOR` for
disabling color output.

**Unlisted methods** — behavior for all display methods not explicitly adapted above
(`print_goodbye`, `prompt`, `prompt_tokens`, `get_prompt_style`, `create_prompt_session`,
`get_input`, `success`, `error`, `warning`, `info`, `hint`, `section`, `status`,
`status_block`, `progress`, `table`, `help`, `bottom_toolbar`) is identical to the
reference implementation — port verbatim from the reference file listed above.

All other ANSI codes, box-drawing chars, prompt_toolkit integration, and color detection
logic are identical to the reference implementation.

---

## Change 2: commands/validate.md — 8-Category Structure

**Problem:** Current validate command has a basic flat checklist. The reference has
8 named categories with specific check counts and a `N/N checks passed` summary.

**Solution:** Rewrite to 8 categories, each with specific numbered checks:

### Category structure:

**1. Directory Structure** *(checked against `agent-harness/` root)*
- `agent-harness/cli_web/<app>/` exists
- `agent-harness/<APP>.md` exists (software-specific SOP at the harness root)
- `cli_web/` has NO `__init__.py` (namespace package — no `__init__.py` required)
- `<app>/` HAS `__init__.py`
- `core/`, `commands/`, `utils/`, `tests/` all present inside `cli_web/<app>/` (one atomic check — pass only if all four exist)
- `setup.py` at `agent-harness/` root

**2. Required Files** *(checked against `cli_web/<app>/`)*
- `README.md`, `<app>_cli.py`, `__main__.py`
- `core/client.py`, `core/auth.py`, `core/session.py`, `core/models.py`
- `utils/repl_skin.py`, `utils/output.py`, `utils/config.py`
- `tests/TEST.md`, `tests/test_core.py`, `tests/test_e2e.py`

**3. CLI Implementation Standards**
- Uses Click framework with command groups
- `--json` flag on every command
- REPL mode when run without arguments — validated by static source inspection:
  grep `<app>_cli.py` for `invoke_without_command=True`
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
- No `CLI-ANYTHING-WEB.md` inside app package (it lives in plugin root, not here)

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

### Report format:
```
Web Harness Validation Report
App: monday
Path: ./monday/agent-harness/cli_web/monday

Directory Structure  (6/6 checks passed)
Required Files       (13/13 files present)
CLI Standards        (6/6 standards met)
Core Modules         (4/4 standards met)
Test Standards       (8/8 standards met)
Documentation        (3/3 standards met)
PyPI Packaging       (5/5 standards met)
Code Quality         (5/5 checks passed)

Overall: PASS (50/50 checks)
```

---

## Change 3: CLI-ANYTHING-WEB.md — Rename + Standalone Framing + Pipeline Gaps

**Problem:** Four distinct sub-problems in the current `WEB-HARNESS.md`:

1. **Comparison framing** — Core Philosophy and Naming Conventions section currently
   position the tool relative to CLI-Anything (e.g., "CLI-Anything generates CLIs from
   source code. Web-Harness generates from traffic", "Design Principles (inherited from
   CLI-Anything)"). This plugin is standalone. The comparison language makes it appear
   to be a companion tool that only makes sense alongside another project.

2. **Missing Phase: Test Planning** — The pipeline has no dedicated "write TEST.md plan
   BEFORE writing test code" phase. The reference methodology requires: implement first,
   then write the test plan (TEST.md Part 1), THEN write the test code, THEN append
   results (TEST.md Part 2). Currently Phase 5 (Test) and Phase 6 (Document) are merged
   incorrectly — Phase 6 says "Write TEST.md" as if it's written after running, not in
   two parts.

3. **Missing: Response Body Verification methodology** — Phase 5 (Test) lacks the
   equivalent of HARNESS.md's "Output Verification Methodology". For web CLIs, this means:
   never trust status 200 alone, always verify response body contains expected fields,
   always verify CRUD round-trips (create → read → verify → delete → verify gone).

4. **Missing: Realistic Workflow Scenarios** — Phase 4 (currently the test planning
   equivalent) lacks web-adapted workflow scenarios like HARNESS.md's Phase 4 examples.

5. **File must be renamed** from `WEB-HARNESS.md` to `CLI-ANYTHING-WEB.md` to match
   the repo's identity.

### 3a. Rename: WEB-HARNESS.md → CLI-ANYTHING-WEB.md

Rename the file. Update every reference to `WEB-HARNESS.md` in:
- All 6 command files: `commands/web-harness.md`, `commands/record.md`,
  `commands/refine.md`, `commands/test.md`, `commands/validate.md`, `commands/list.md`
- `scripts/setup-web-harness.sh`
- `README.md`
- `QUICKSTART.md`

### 3b. Replace Core Philosophy section (standalone framing)

Remove the two-column comparison. Replace with:

```markdown
## Core Philosophy

Web-Harness builds production-grade Python CLI interfaces for closed-source web
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
```

### 3c. Replace Naming Conventions section (standalone, no comparison column)

Replace the current two-column CLI-Anything vs Web-Harness comparison table with a
single-column reference:

```markdown
## Naming Conventions

| Convention | Value |
|-----------|-------|
| CLI command | `cli-web-<app>` |
| Python namespace | `cli_web.<app>` |
| App-specific SOP | `<APP>.md` |
| Plugin slash command | `/web-harness` |
| Traffic capture dir | `traffic-capture/` |
| Auth config dir | `~/.config/cli-web-<app>/` |
```

### 3d. Add Phase 5: Test Planning (between current Phase 4 Implement and Phase 5 Test)

Insert a new Phase 5 (Test Planning). Renumber: current Phase 5 → Phase 6,
current Phase 6 → Phase 7, current Phase 7 → Phase 8. Total phases becomes 8.

New Phase 5 content:

```markdown
### Phase 5 — Plan Tests (TEST.md Part 1)

**Goal:** Write the test plan BEFORE writing any test code.

**BEFORE writing any test code**, create `tests/TEST.md` in the app package.
This file serves as the test plan and MUST contain:

1. **Test Inventory** — List planned test files and estimated test counts:
   - `test_core.py`: XX unit tests planned
   - `test_e2e.py`: XX E2E tests planned (fixture), XX E2E tests planned (live),
     XX subprocess tests planned

2. **Unit Test Plan** — For each core module, describe what will be tested:
   - Module name (e.g., `client.py`)
   - Functions to test
   - Edge cases (invalid auth, rate limit response, malformed JSON, 404, 401, 500)
   - Expected test count

3. **E2E Test Plan** — Describe the test scenarios:
   - Fixture replay tests: which captured responses will be replayed?
   - Live tests: which CRUD workflows will run against the real API?
   - What response fields will be verified?

4. **Realistic Workflow Scenarios** — Detail each multi-step workflow:
   - **Scenario name**
   - **Simulates**: what real user task (e.g., "creating and managing a project board",
     "bulk-creating tasks and archiving completed ones")
   - **Operations**: step-by-step API calls
   - **Verified**: what response fields and round-trip consistency is checked

   Example scenarios for web apps:
   - Auth flow: login → store token → make authenticated request → token refresh
   - CRUD round-trip: create entity → read it back → verify fields match → update →
     verify update → delete → verify 404 on read
   - Paginated list: fetch page 1 → verify count → fetch page 2 → verify no overlap
   - Bulk operations: create N items → list all → verify count → delete all → verify empty
   - Rate limit handling: rapid requests → verify backoff behavior

This planning document ensures comprehensive test coverage before writing code.
```

### 3e. Update Phase 6 (formerly Phase 5): Test Implementation

The existing Phase 5 (Test) content is adequate for test code structure. Add to it:

**Response Body Verification methodology** (web equivalent of Output Verification):

```markdown
**Response Body Verification — never trust status 200 alone:**
- Always verify the response body contains expected top-level fields
- For create operations: verify returned entity has the submitted field values
- For read operations: verify entity ID matches what was requested
- For update operations: verify changed fields reflect new values
- For delete operations: verify subsequent read returns 404
- For list operations: verify count, verify each item has required fields
- Print entity IDs and counts so users can manually verify: e.g.,
  `print(f"[verify] Created board id={data['id']} name={data['name']}")`
```

Also add: **Round-trip test requirement** — every E2E live test MUST include at minimum
a create → read → verify round-trip. Tests that only create without reading back give
false confidence.

### 3f. Update Phase 7 (formerly Phase 6): Test Documentation

Change Phase 7 (Document) to make the two-part TEST.md structure explicit:

The Phase must clearly state: Phase 7 **appends results to the existing TEST.md**
(which already has Part 1 from Phase 5). It does NOT write TEST.md from scratch.

Process:
1. Run full test suite: `python3 -m pytest cli_web/<app>/tests/ -v --tb=short`
2. Run subprocess tests with `CLI_WEB_FORCE_INSTALLED=1` to confirm installed command
3. **Append** to existing `TEST.md` a Part 2 section with:
   - Full `pytest -v --tb=no` output
   - Summary: total tests, pass rate, execution date
   - Any gaps or failed tests with explanation

### 3g. Rules section (after Critical Lessons, before Naming Conventions)

Add enforcement rules in bold-rule style. Placement: insert after the `## Critical Lessons`
section (which already exists in the current file at the end of the Critical Lessons
section list) and before the `## Naming Conventions` section (both sections confirmed
present in the current `WEB-HARNESS.md`):

- **Auth credentials MUST be stored securely.** `chmod 600 auth.json`. Never hardcode
  tokens in source. If auth file missing, CLI errors with clear instructions — never
  falls back to unauthenticated requests.
- **Tests MUST fail (not skip) when auth is missing.** Tests that skip on missing auth
  give false confidence. The CLI is useless without a live account.
- **Every command MUST support `--json`.** Agents consume structured output.
  Human-readable is optional; machine-readable is required.
- **E2E tests MUST include subprocess tests** via `_resolve_cli("cli-web-<app>")`.
  Tests must run against the installed package, not just source imports.
- **Every `cli_web/<app>/` MUST contain `README.md`** with auth setup, install steps,
  and usage examples.
- **Every `cli_web/<app>/tests/` MUST contain `TEST.md`** written in two parts: plan
  (before tests), results (appended after running).
- **Every CLI MUST use the unified REPL skin** (`repl_skin.py`). REPL MUST be the
  default when invoked without a subcommand.
- **Rate limits MUST be respected.** Never retry without backoff. Never hammer endpoints.
- **Response bodies MUST be verified.** Never trust HTTP status alone. Always check
  that returned JSON contains expected fields.

### 3h. Testing Strategy section (after Rules)

4-layer table:

| Layer | File | What it tests |
|-------|------|--------------|
| Unit tests | `test_core.py` | Core functions with mocked HTTP. No real network. Fast, deterministic. |
| E2E fixture tests | `test_e2e.py` | Full command flow replaying captured responses from `tests/fixtures/`. Verifies parsing logic. |
| E2E live tests | `test_e2e.py` | Real API calls. Require auth — FAIL without it. CRUD round-trip, workflow scenarios. |
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

**App naming convention:** App names must contain no hyphens. Underscores are permitted
(e.g., `cli-web-monday_com` → `cli_web.monday_com.monday_com_cli`). Valid examples:
`monday`, `notion`, `jira`, `monday_com`.

### 3i. Phase 8 expansion (formerly Phase 7)

Add the namespace package explanation:
- Why namespace packages: multiple `cli-web-*` CLIs coexist in same Python environment
- `cli_web/` has NO `__init__.py` — this is the rule that enables it
- `find_namespace_packages(include=["cli_web.*"])` — not `find_packages`
- Install verification commands with `CLI_WEB_FORCE_INSTALLED=1`

---

## Change 4: Remaining File Fixes

### README.md
Remove the `claude mcp add` / Claude Desktop marketplace-style install step from the
Quick Start section. Replace with:
```bash
cp -r /path/to/cli-anything-web-plugin ~/.claude/plugins/web-harness
/reload-plugins
/help web-harness
```
Also update the Commands table to include `web-harness:list` with description:
"List all installed and generated `cli-web-*` CLIs".

### commands/refine.md
- Insert a new step between current Step 3 (Gap analysis) and Step 4 (Record new traffic):
  "Present gap report to user and confirm which gaps to address before proceeding."
  Verify the current step count before renumbering (expected: 9 steps based on current
  file content). The new step becomes Step 4; all subsequent steps shift by one.
- Add **Success Criteria** section
- Add **Notes** section: refine is incremental, never removes commands, present before implementing

### commands/test.md
- Modify existing Step 3 (currently: "If installed, also run subprocess tests:
  `CLI_WEB_FORCE_INSTALLED=1 python3 -m pytest ...`") to include: after running, verify
  subprocess backend by checking that `[_resolve_cli] Using installed command:` appears
  in the output
- Add **Failure Handling** section: show failures, do NOT update TEST.md, suggest fixes,
  offer to re-run

### commands/web-harness.md
- Add **Success Criteria** section with these 9 items:
  1. All core modules are implemented and functional (`client.py`, `auth.py`, `session.py`, `models.py`)
  2. CLI supports both one-shot commands and REPL mode
  3. `--json` output mode works for all commands
  4. All tests pass (100% pass rate)
  5. Subprocess tests use `_resolve_cli()` and pass with `CLI_WEB_FORCE_INSTALLED=1`
  6. TEST.md contains both plan (Part 1) and results (Part 2)
  7. README.md documents installation and usage
  8. `setup.py` is created and local installation works
  9. CLI is available in PATH as `cli-web-<app>`
- Add **Output Structure** directory tree:
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
Web-specific plugin structure checker. Reports ALL checks (no fail-fast). Prints one
line per check: `[PASS]` or `[FAIL]` prefix followed by the check description. Prints
a summary line at the end: `X/Y checks passed`. Exits 0 if all pass, exits 1 if any
fail. This is a static shell script — not generated. Checks:
- `.claude-plugin/plugin.json` valid JSON
- `CLI-ANYTHING-WEB.md` exists
- All 6 command files exist: `commands/web-harness.md`, `commands/record.md`,
  `commands/refine.md`, `commands/test.md`, `commands/validate.md`, `commands/list.md`
- `scripts/repl_skin.py` exists
- `scripts/setup-web-harness.sh` executable
- `.mcp.json` exists and valid JSON
- `skills/web-harness-methodology/SKILL.md` exists
- `PUBLISHING.md` exists
- `README.md` exists

### LICENSE (new file)
Static MIT License file. Year: 2026. Copyright holder: "CLI-Anything Contributors".
The implementer writes this file once with those values — it is not generated at runtime.

---

## Complete File Inventory

| File | Action |
|------|--------|
| `WEB-HARNESS.md` | Rename to `CLI-ANYTHING-WEB.md` |
| `CLI-ANYTHING-WEB.md` | Add standalone framing, Phase 5 (Test Planning), Response Verification, Phase 7 two-part TEST.md, Rules, Testing Strategy, Phase 8 expansion |
| `commands/web-harness.md` | Update `WEB-HARNESS.md` reference → `CLI-ANYTHING-WEB.md`; add Success Criteria, Output Structure |
| `commands/record.md` | Update `WEB-HARNESS.md` reference → `CLI-ANYTHING-WEB.md` |
| `commands/refine.md` | Update `WEB-HARNESS.md` reference → `CLI-ANYTHING-WEB.md`; add gap-present step, Success Criteria, Notes |
| `commands/test.md` | Update `WEB-HARNESS.md` reference → `CLI-ANYTHING-WEB.md`; add subprocess verification step, Failure Handling section |
| `commands/validate.md` | Update `WEB-HARNESS.md` reference → `CLI-ANYTHING-WEB.md`; major rewrite — 8-category structure, N/N format |
| `commands/list.md` | Update `WEB-HARNESS.md` reference → `CLI-ANYTHING-WEB.md` |
| `scripts/repl_skin.py` | Complete rewrite — proper ReplSkin class, web accent colors |
| `scripts/setup-web-harness.sh` | Update `WEB-HARNESS.md` reference → `CLI-ANYTHING-WEB.md` |
| `README.md` | Remove marketplace references; add list command to table; update `WEB-HARNESS.md` reference |
| `QUICKSTART.md` | Update `WEB-HARNESS.md` reference → `CLI-ANYTHING-WEB.md` |
| `verify-plugin.sh` | New file — plugin structure checker |
| `LICENSE` | New file — MIT |

---

## Out of Scope

- Changes to `scripts/setup-web-harness.sh` methodology (only the reference update needed)
- Changes to `skills/` reference files (already good)
- Changes to `.claude-plugin/plugin.json` (already complete)
- Changes to `.mcp.json` (correct)
- Changes to `PUBLISHING.md` (already updated in previous session)
- Changes to `commands/list.md` beyond the reference update (already implemented)
