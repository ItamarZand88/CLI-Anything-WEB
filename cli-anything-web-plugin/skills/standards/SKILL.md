---
name: standards
description: >
  Quality standards and Phase 4 publish/verify for cli-web-* CLIs. Covers the
  75-check quality checklist, package publishing (pip install -e .), end-user
  smoke testing (READ + WRITE), and final pipeline verification. Use when building,
  reviewing, or checking quality of a cli-web-* CLI package, during implementation
  (Phase 2), validation, code review, Phase 4 publish and verify, or when checking
  if an implementation is complete.
version: 0.1.0
---

# CLI-Anything-Web Standards (Phase 4 + Quality)

Quality standards, publishing, and final verification for cli-web-* CLIs.
This skill owns the 75-check quality checklist and Phase 4 of the pipeline:
publish the CLI and verify it works end-to-end as a real user would.

---

## Prerequisites (Hard Gate)

Do NOT start unless:
- [ ] All tests pass (100% pass rate from Phase 3)
- [ ] TEST.md has both Part 1 (plan) and Part 2 (results)
- [ ] All core modules are implemented and functional

If tests are not passing, invoke the `testing` skill first.

### Site Profile Exceptions

Not all checks apply to every CLI. When evaluating, consider the site profile:

- **No-auth sites** (public APIs): Skip auth-related checks (auth.py required,
  auth commands, auth smoke test). Mark as N/A.
- **Read-only sites** (no write operations): Skip write operation smoke test.
  Verify reads return real data instead.
- **API-key auth sites**: `auth login` takes a key argument, not playwright-cli.
  `auth refresh` is not applicable — use `auth logout` instead.

Mark inapplicable checks as "N/A — [reason]" rather than creating dead-code stubs.

---

## Phase 8: Publish and Verify (Phase 4)

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

**If no-auth site:** Skip steps 5-6 (auth). Go directly to step 7 (READ).

**If read-only site:** Skip step 8 (WRITE). Verify reads return real data.

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

- [ ] `auth login` works (playwright-cli, API key, or N/A for no-auth)
- [ ] `auth status` shows valid (or N/A for no-auth)
- [ ] At least one READ returns real data
- [ ] **At least one WRITE/CREATE/GENERATE succeeds** (or N/A for read-only)
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

## Generate Claude Skill (Post-Pipeline)

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
- `auth login` works (via playwright-cli, API key, or N/A for no-auth sites)
- `auth status` shows valid (or N/A for no-auth sites)
- At least one READ returns real data
- **At least one WRITE/CREATE/GENERATE succeeds** (or N/A for read-only sites)
- The CLI works standalone -- no debug Chrome, no port 9222, no MCP
- **`.claude/skills/<app>-cli/SKILL.md` exists and documents all commands**

**Final Step:** Pipeline complete. All checks pass.

---

## Package Structure

See HARNESS.md "Generated CLI Structure" for the complete package template.
Key points: `cli_web/` namespace (NO `__init__.py`), `<app>/` sub-package (HAS `__init__.py`),
`core/`, `commands/`, `utils/`, `tests/` directories.

## Quality Checklist

The full checklist is in `references/quality-checklist.md` (11 categories, 75 checks).

**Quick summary of categories:**

| # | Category | Checks |
|---|----------|--------|
| 1 | Directory Structure | 6 |
| 2 | Required Files | 13 |
| 3 | CLI Implementation | 9 |
| 4 | Core Modules | 8 |
| 5 | Test Standards | 8 |
| 6 | Documentation | 3 |
| 7 | PyPI Packaging | 5 |
| 8 | Code Quality | 8 |
| 9 | REPL Quality | 3 |
| 10 | Error Handling & Resilience | 8 |
| 11 | UX Patterns | 4 |

Run `/cli-anything-web:validate` to check all items automatically.

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

## Integration

| Relationship | Skill |
|-------------|-------|
| **Preceded by** | `testing` (Phase 3) |
| **Followed by** | None — this is the final phase |
| **References** | HARNESS.md (Generated CLI Structure, Naming Conventions) |

---

## Related

- **`testing`** skill -- Phase 3 test planning/writing/documentation
- **`methodology`** skill -- Phase 2 analyze/design/implement
- **`capture`** skill -- Phase 1 traffic recording
- **`/cli-anything-web:validate`** -- Command to run the full 75-check validation
