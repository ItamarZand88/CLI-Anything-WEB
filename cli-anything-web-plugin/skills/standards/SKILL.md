---
name: standards
description: >
  Quality standards and Phase 8 publish/verify for cli-web-* CLIs. Covers the
  70-check quality checklist, package publishing (pip install -e .), end-user
  smoke testing (READ + WRITE), and final pipeline verification. Use when building,
  reviewing, or checking quality of a cli-web-* CLI package, during implementation
  (Phase 4), validation, code review, Phase 8 publish and verify, or when checking
  if an implementation is complete.
version: 0.1.0
---

# CLI-Anything-Web Standards (Phase 8 + Quality)

Quality standards, publishing, and final verification for cli-web-* CLIs.
This skill owns the 70-check quality checklist and Phase 8 of the pipeline:
publish the CLI and verify it works end-to-end as a real user would.

---

## Prerequisites (Hard Gate)

Do NOT start unless:
- [ ] All tests pass (100% pass rate from Phase 7)
- [ ] TEST.md has both Part 1 (plan) and Part 2 (results)
- [ ] All core modules are implemented and functional

If tests are not passing, invoke the `testing` skill first.

---

## Phase 8: Publish and Verify

**Goal:** Make CLI installable AND verify it works end-to-end as a real user would use it.

### Step 1: Create setup.py and Install

1. Create `setup.py` with:
   - `find_namespace_packages` for `cli_web.*`
   - `console_scripts` entry point: `cli-web-<app>`
   - Dependencies: `click>=8.0`, `httpx`
   - Optional: `extras_require={"browser": ["playwright>=1.40.0"]}`
2. Install: `pip install -e .`
3. Verify: `which cli-web-<app>`
4. Test help: `cli-web-<app> --help`

### Step 2: End-User Smoke Test (MANDATORY)

This is the most critical verification step. The agent MUST simulate what a real
end user would do after `pip install cli-web-<app>`. If this fails, the pipeline
is NOT complete -- go back and fix the issue.

**5. Authenticate as an end user would:**
```bash
cli-web-<app> auth login
```
This uses playwright-cli via subprocess -- opens a browser, user logs in,
cookies saved. This is what end users will run. If this fails, the CLI is
broken for end users.

**6. Verify auth status shows LIVE VALIDATION OK:**
```bash
cli-web-<app> auth status
```
Must show: cookies present, tokens valid. If it shows "expired", "redirect",
or any auth failure -- STOP. Fix auth before proceeding.

**7. Run a READ operation and verify real data:**
```bash
cli-web-<app> --json <first-resource> list
```
This must return real data from the live API -- NOT an error, NOT empty,
NOT "auth not configured". Verify the JSON response contains expected fields.

**8. Run a WRITE operation and verify it actually worked:**
This is the step the agent most commonly skips. Reading data is easy -- the
real test is whether the CLI can CREATE, UPDATE, or GENERATE something.

```bash
# For CRUD apps (Monday, Notion, Jira):
cli-web-<app> --json <resource> create --name "smoke-test-$(date +%s)"
cli-web-<app> --json <resource> list   # verify the created item appears
cli-web-<app> --json <resource> delete --id <id-from-create>

# For generation apps (Suno, Midjourney, NotebookLM audio):
cli-web-<app> --json <resource> generate --prompt "test" --wait
# Verify: JSON response contains a real ID, status=complete, not an error
# If the command has --output, verify the file was downloaded and size > 0

# For search/query apps:
cli-web-<app> --json search "test query"
# Verify: results array is non-empty
```

**If ANY write/generate command fails, the pipeline is NOT complete.**
Reading a list of existing items only proves auth works -- it does NOT prove
the CLI can actually do useful work. The whole point is to CREATE things,
not just read them.

**9. Only after steps 5-8 ALL pass, declare the pipeline complete.**

### Smoke Test Checklist

- [ ] `auth login` works via playwright-cli subprocess
- [ ] `auth status` shows valid
- [ ] At least one READ returns real data
- [ ] **At least one WRITE/CREATE/GENERATE succeeds against the real API**
- [ ] The CLI works standalone -- no debug Chrome, no port 9222, no MCP

### Common Failure Mode

The agent runs `<resource> list` (which works because it's just a GET with auth),
declares "all done," but never tests the create/generate commands (which require
correct POST bodies, CSRF tokens, request encoding). This is the #1 gap to watch for.

### Why Namespace Packages

- Multiple `cli-web-*` CLIs coexist in the same Python environment without conflicts
- `cli_web/` has NO `__init__.py` -- this is the rule that enables it
- Use `find_namespace_packages(include=["cli_web.*"])` -- NOT `find_packages`

---

## Phase 9: Generate Claude Skill

**Goal:** Create a project-local Claude skill so that Claude can use this CLI
automatically in future conversations — no manual lookup required.

This step runs after all smoke tests pass. It takes about 2 minutes.

### Step 1: Find the .claude directory

The skill goes in `.claude/skills/<app>-cli/SKILL.md` relative to the project root
(the directory that contains `.claude/`). Find it:

```bash
# Walk up from CWD until you find a .claude dir, or use git root
git rev-parse --show-toplevel
```

If there is no `.claude/` at the git root, create it. The target path is:
```
<git-root>/.claude/skills/<app>-cli/SKILL.md
```

### Step 2: Read the CLI's README and command structure

Before writing the skill, collect the facts:

```bash
# Read README for description and usage examples
cat agent-harness/cli_web/<app>/README.md

# Discover all commands and their options
cli-web-<app> --help
cli-web-<app> <resource> --help   # for each command group
```

### Step 3: Write the skill file

Create `<git-root>/.claude/skills/<app>-cli/SKILL.md` with this structure:

```markdown
---
name: <app>-cli
description: Use cli-web-<app> to <one-line purpose>. Invoke this skill whenever
  the user asks about <key topics the CLI covers — be specific>. Always prefer
  cli-web-<app> over manually fetching the website.
---

# cli-web-<app>

<one-sentence description>. Installed at: `cli-web-<app>`.

## Quick Start

\`\`\`bash
# <most common operation>
cli-web-<app> <command> --json

# <second most common>
cli-web-<app> <command> --json
\`\`\`

Always use `--json` when parsing output programmatically.

---

## Commands

<For each command group, document:>
### `<resource> <verb>`
<one-line description>

\`\`\`bash
cli-web-<app> <resource> <verb> [options] --json
\`\`\`

**Key options:** <table or list of the most useful options>
**Output fields:** <key JSON fields agents will care about>

---

## Agent Patterns

\`\`\`bash
# <common task>
cli-web-<app> <command> --json | python -c "import json,sys; ..."

# <another common task>
cli-web-<app> <command> --json
\`\`\`

---

## Notes

- Auth: <required / not required — and how to set up>
- Prices/units: <if applicable>
- Rate limiting: <if applicable>
```

**Skill description guidelines:**
- Name the exact topics the CLI covers so the skill triggers reliably
- Use "whenever the user asks about X, Y, Z" phrasing
- If the app has notable filters or options (like player position, rating range),
  mention them in the description so the skill triggers for filter-heavy queries too
- End with "Always prefer cli-web-<app> over manually fetching the website."

### Step 4: Verify

```bash
# Confirm the file exists and is valid YAML frontmatter
head -5 <git-root>/.claude/skills/<app>-cli/SKILL.md
```

The skill takes effect immediately in the next Claude Code session in this project.

---

## Pipeline Complete

The pipeline is NOT done until:
- `auth login` works via playwright-cli subprocess
- `auth status` shows valid
- At least one READ returns real data
- **At least one WRITE/CREATE/GENERATE succeeds against the real API**
- The CLI works standalone -- no debug Chrome, no port 9222, no MCP
- **`.claude/skills/<app>-cli/SKILL.md` exists and documents all commands**

**Final Step:** Pipeline complete. All checks pass.

---

## Package Structure

See HARNESS.md "Generated CLI Structure" for the complete package template.
Key points: `cli_web/` namespace (NO `__init__.py`), `<app>/` sub-package (HAS `__init__.py`),
`core/`, `commands/`, `utils/`, `tests/` directories.

## 8-Category Checklist (59 checks)

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
`utils/repl_skin.py`, `utils/output.py`, `utils/config.py`, `utils/helpers.py`,
`tests/TEST.md`, `tests/test_core.py`, `tests/test_e2e.py`

### 3. CLI Implementation (6 checks)

- Click framework with command groups (`@click.group`)
- `--json` flag on every command
- REPL mode via `invoke_without_command=True`
- `ReplSkin` used for banner, prompt, messages
- `auth` group with `login`, `status`, `refresh`
- Global session state (`pass_context=True`)
- Commands use `handle_errors(json_mode)` context manager — no manual try/except blocks
- Resource get/rename/delete use `@click.argument` (positional ID), not `@click.option("--id")`
- `--notebook` is optional on notebook-scoped commands (falls back to persistent context via `require_notebook()`)

### 4. Core Modules (4 checks)

- `client.py`: centralized auth header injection, exponential backoff, JSON parsing
- `auth.py`: login, refresh, expiry check, secure storage (chmod 600)
- `session.py`: Session class with undo/redo stack
- `models.py`: typed response models
- If protocol is non-REST: `core/rpc/` exists with `types.py`, `encoder.py`, `decoder.py`
- `core/exceptions.py`: domain-specific exception hierarchy (AuthError, RateLimitError, NetworkError, ServerError, NotFoundError)
- `client.py` maps HTTP status codes to typed exceptions (401→AuthError, 404→NotFoundError, 429→RateLimitError, 5xx→ServerError)
- Auth retry: client retries once on recoverable AuthError with token refresh

### 5. Test Standards (8 checks)

- `TEST.md` has both plan (Part 1) and results (Part 2)
- Unit tests use `unittest.mock.patch` -- no real network
- E2E fixture tests replay from `tests/fixtures/`
- E2E live tests FAIL (not skip) without auth
- `TestCLISubprocess` class exists
- Uses `_resolve_cli("cli-web-<app>")` -- no hardcoded paths
- Subprocess `_run` does NOT set `cwd`
- Supports `CLI_WEB_FORCE_INSTALLED=1`

### 6. Documentation (3 checks)

- `README.md` in `cli_web/<app>/` — must follow this structure:
  ```markdown
  # cli-web-<app>

  > Generated by [CLI-Anything-Web](../../../../cli-anything-web-plugin/) from [<app>.com](<url>)

  One-line description of what the CLI does.

  ## Installation
  ## Usage          (show key commands with examples)
  ## Auth           (login methods, when auth is required vs optional)
  ## JSON Output    (show --json flag usage)
  ## Testing        (pytest commands for unit and E2E)
  ```
- `<APP>.md`: API map, data model, auth scheme, endpoint inventory
- No `HARNESS.md` inside app package (lives in plugin root)

### 7. PyPI Packaging (5 checks)

- `find_namespace_packages(include=["cli_web.*"])`
- Package name: `cli-web-<app>`
- Entry point: `cli-web-<app>=cli_web.<app>.<app>_cli:main`
- All imports use `cli_web.<app>.*` prefix
- `python_requires=">=3.10"`

### 8. Code Quality (8 checks)

- No syntax errors, no import errors
- No hardcoded auth tokens or API keys
- No hardcoded API base URLs or credentials in source
- No hardcoded session tokens, CSRF tokens, build labels, or session IDs (must be extracted dynamically)
- No bare `except:` blocks
- Error messages include actionable guidance
- `<app>_cli.py` forces UTF-8 stdout/stderr on Windows (`sys.stdout.reconfigure(encoding="utf-8")`)
- HTML table parsers extract ALL visible columns (no empty fields for data the site displays)

### 9. REPL Quality (3 checks)

- REPL uses `shlex.split(line)` — not `line.split()` (quoted args must parse correctly)
- REPL dispatches with `cli.main(args=repl_args, standalone_mode=False)` — never `**ctx.params`
- Primary resource commands use `@click.argument` for positional params (not `--required-option`)

### 10. Error Handling & Resilience (6 checks)

- `core/exceptions.py` exists with typed hierarchy (not generic RuntimeError)
- Client maps HTTP status codes to domain exceptions
- Auth module supports `CLI_WEB_<APP>_AUTH_JSON` environment variable
- Polling operations use exponential backoff (not fixed `time.sleep()`)
- `--json` mode outputs structured error JSON (`{"error": true, "code": "...", "message": "..."}`)
- Long operations (>2s) show progress feedback when not in `--json` mode
- Generation commands support `--wait` (poll until complete) and `--retry N` (rate-limit retry)
- `--output <path>` flag on generation commands saves content to file

### 11. UX Patterns (4 checks)

- Partial ID resolution: get/rename/delete accept short prefixes (not full UUIDs only)
- Persistent context: `use <id>` saves to `context.json`, `status` shows current context
- `--notebook` optional when context is set (via `require_notebook()`)
- Regional Google cookie domains supported (60+ ccTLDs, not just `.google.com`)

## Key Rules

These are non-negotiable standards:

- **playwright-cli is the primary browser tool** -- verify with `npx @playwright/cli --version`
- **Content generation downloads the result** -- if the app generates content (audio,
  images, video), the CLI must trigger -> poll -> download -> save. Support `--output`.
- **CAPTCHAs pause and prompt** -- never crash or skip. Detect, tell user to solve in
  browser, wait for confirmation, retry.
- **Site assessment is built into Phase 1 capture** -- no separate recon report needed.
  Framework detection and protection checks happen in Step 2 of the capture skill.
- **Auth stored securely** -- `chmod 600 auth.json`, never hardcode tokens
- **Tests fail without auth** -- never skip, the CLI is useless without a live account
- **Every command supports `--json`** -- agents need structured output
- **E2E includes subprocess tests** -- test the installed package, not just source imports
- **REPL is the default** -- `invoke_without_command=True`, branded banner via `ReplSkin`
- **Rate limits respected** -- exponential backoff, never hammer endpoints
- **Response bodies verified** -- never trust status 200 alone

## Naming Conventions

| Convention | Value |
|-----------|-------|
| CLI command | `cli-web-<app>` |
| Python namespace | `cli_web.<app>` |
| App-specific SOP | `<APP>.md` |
| App names | No hyphens. Underscores OK (`monday_com`) |

---

## Related

- **`testing`** skill -- Phases 5-7 test planning/writing/documentation
- **`methodology`** skill -- Phases 2-4 analyze/design/implement
- **`capture`** skill -- Phase 1 traffic recording
- **`/cli-anything-web:validate`** -- Command to run the full 70-check validation
