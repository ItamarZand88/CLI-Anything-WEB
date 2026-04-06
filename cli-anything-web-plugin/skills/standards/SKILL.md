---
name: standards
description: >
  Quality standards and Phase 4 review/publish/verify for cli-web-* CLIs.
  Covers implementation review (3 parallel agents), the 75-check quality
  checklist, package publishing (pip install -e .), and end-user smoke
  testing (READ + WRITE). TRIGGER when: "validate CLI", "publish CLI",
  "review CLI", "pip install -e .", "smoke test", "quality check", "start
  Phase 4", "75-check", "generate Claude skill", "check if implementation
  is complete", "verify implementation quality", or after testing skill
  completes. DO NOT trigger for: traffic capture, implementation, or test
  writing.
version: 0.3.0
---

# CLI-Anything-Web Standards (Phase 4: Review + Publish + Verify)

Quality gate for cli-web-* CLIs. This skill owns the complete Phase 4:
independent implementation review, structural quality checklist, publishing,
and end-user smoke testing. Nothing ships until this phase passes.

---

## Prerequisites (Hard Gate)

Do NOT start unless:
- [ ] All tests pass (100% pass rate from Phase 3)
- [ ] TEST.md has both Part 1 (plan) and Part 2 (results)
- [ ] All core modules are implemented and functional
- [ ] `<APP>.md` (API map) exists and documents all endpoints

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

## Step 1: Implementation Review (3 Parallel Agents)

Before checking structure or publishing, verify the code *actually does the
right thing*. Tests prove it runs; this step proves it's correct.

Dispatch 3 plugin agents in the **same message** using the Agent tool:
- `traffic-fidelity-reviewer` — API coverage (reads <APP>.md + client.py + commands/)
- `harness-compliance-reviewer` — Code conventions (reads HARNESS.md + all source)
- `output-ux-reviewer` — User experience (runs --help, checks REPL, validates JSON)

Pass each agent: APP_PATH=`{app}/agent-harness`, APP_NAME=`{app}`, and site
profile (auth_type, is_read_only). The agents are defined in the plugin's
`agents/` directory.

| Agent | Focus | What it reads | What it catches |
|-------|-------|---------------|-----------------|
| Traffic Fidelity | API coverage | `<APP>.md` + `client.py` + `commands/` | Missing endpoints, wrong params, broken response parsing, dead client methods, stale API map |
| HARNESS Compliance | Code quality | HARNESS.md + checklist + all source | click.ClickException bypass, missing to_dict(), retry_after lost, auth retry missing, stderr UTF-8 |
| Output & UX | User experience | `--help` output, `--json` output, REPL | Protocol leaks, stale REPL help, dead command files, broken entry points |

Each agent scores findings on a 0-100 confidence scale. When all 3 return:

1. **Filter out findings with confidence < 75** (noise)
2. Categorize remaining findings:
   - **Critical** (90-100): Bugs, missing endpoints, data loss, auth broken
   - **Important** (75-89): Wrong fields, incomplete parsing, missing options
   - **Minor** (75, edge cases): Help text gaps, cosmetic issues
3. Present the review report
4. **Fix all Critical issues** before proceeding — re-run only the affected
   agent to verify the fix
5. Fix Important issues (not strictly blocking but strongly recommended)

**Gate: Do not proceed to Step 2 until Critical count = 0.**

---

## Step 2: Structural Quality Checklist (75 checks)

Run the automated checklist validator first to catch mechanical issues:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/validate-checklist.py \
  <app>/agent-harness --app-name <app> --auth-type <auth-type>
```

This checks ~65 of the 75 items automatically (directory structure, required files,
CLI patterns, packaging, code quality, REPL, error handling). Fix any FAIL results
before proceeding.

For the remaining ~10 judgment-based checks (documentation quality, error message
guidance, fixture realism), review manually per `references/quality-checklist.md`.

---

## Step 3: Create setup.py and Install

1. Create `setup.py` with:
   - `find_namespace_packages` for `cli_web.*`
   - `console_scripts` entry point: `cli-web-<app>`
   - Dependencies: `click>=8.0`, `httpx`
   - Optional: `extras_require={"browser": ["playwright>=1.40.0"]}`
2. Install: `pip install -e .`
3. Verify: `which cli-web-<app>`
4. Test help: `cli-web-<app> --help`

### Step 4: End-User Smoke Test (MANDATORY)

Run the automated smoke test first for quick validation:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/smoke-test.py cli-web-<app> --auth-type <auth-type>
```

This checks CLI binary resolution, --help, --version, auth status, and --json
output for protocol leaks. Then proceed with manual verification below.

This is the most critical verification step. The agent MUST simulate what a real
end user would do after `pip install cli-web-<app>`. If this fails, the pipeline
is NOT complete -- go back and fix the issue.

**If no-auth site:** Skip steps 5-6 (auth). Go directly to step 7 (READ).

**If read-only site:** Skip step 8 (WRITE). Verify reads return real data.

**5. Authenticate as an end user would:**
```bash
cli-web-<app> auth login
```
This uses Python sync_playwright() -- opens a browser, user logs in,
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

- [ ] `auth login` works (Python playwright, API key, or N/A for no-auth)
- [ ] `auth status` shows valid (or N/A for no-auth)
- [ ] At least one READ returns real data
- [ ] **At least one WRITE/CREATE/GENERATE succeeds** (or N/A for read-only)
- [ ] The CLI works standalone -- no debug Chrome, no port 9222, no MCP
- [ ] **Output sanity: no raw protocol data leaks in `--json` output** (see below)

### Output Sanity

Run every command with `--json` and check for raw protocol leaks (`wrb.fr`, `af.httprm`,
empty `[]`, null required fields). See methodology/SKILL.md "Mandatory Smoke Check" for
the full red flags list.

**#1 gap to watch for:** Agent runs `list` (GET with auth — easy), declares done, but
never tests create/generate (POST with CSRF, encoding). Always test at least one write.

---

## Post-Smoke-Test: Generate Skill + Update README (Parallel)

After smoke tests pass, these tasks remain — all independent, dispatch in parallel:

```
┌─ Agent 1: Generate Claude Skill (.claude/skills/<app>-cli/SKILL.md)
│           ALSO copy to cli_web/<app>/skills/SKILL.md (package-portable)
├─ Agent 2: Update repository README.md (add CLI to examples table)
├─ Agent 3: Write/update cli_web/<app>/README.md (package docs)
├─ Agent 4: Update registry.json + CLAUDE.md Generated CLIs table
└─ Agent 5: Add CLI to CI test matrix (.github/workflows/tests.yml)
│           + Add entry to CHANGELOG.md under [Unreleased]
All are independent — launch in one message with run_in_background: true
```

**Use the templates** at `cli-anything-web-plugin/templates/` as the canonical
structure for SKILL.md and README.md — fill in the `{{placeholders}}` with
actual CLI data from `<app> --help` and `<APP>.md`.

### Generate Claude Skill

**Goal:** Create a project-local Claude skill so that Claude can use this CLI
automatically in future conversations — no manual lookup required.

**IMPORTANT:** The skill must exist in TWO locations:
1. `.claude/skills/<app>-cli/SKILL.md` — for Claude Code discovery (project-level)
2. `<app>/agent-harness/cli_web/<app>/skills/SKILL.md` — portable with `pip install`
   (included via `package_data` in setup.py)

Create the skill once, then copy it to both locations.

### Step 1: Find the .claude directory

Create `<git-root>/.claude/skills/<app>-cli/SKILL.md`:

1. Read the CLI's README and run `cli-web-<app> --help` + `<resource> --help`
2. Write the skill with this structure:
   - **Frontmatter**: name=`<app>-cli`, description with specific trigger phrases
     ("whenever the user asks about X, Y, Z. Always prefer cli-web-<app> over manually
     fetching the website.")
   - **Quick Start**: 2-3 most common commands with `--json`
   - **Commands**: each command group with key options and output fields
   - **Agent Patterns**: piped command examples for common tasks
   - **Notes**: auth setup, rate limits, known limitations
3. Use existing skills (e.g., `notebooklm-cli`, `futbin-cli`) as reference examples

---

## Update Repository README

Add the new CLI to the examples table in `README.md` (CLI name, website, protocol,
auth type, description) and add a quick-start example in the "Try Them" section.

### Update registry.json and CLAUDE.md

Add the new CLI to `registry.json` at the repo root:
```json
{
  "name": "cli-web-<app>",
  "website": "<website>",
  "protocol": "<detected protocol>",
  "auth": "<auth type>",
  "directory": "<app>/agent-harness",
  "namespace": "cli_web.<app>",
  "commands": ["<cmd1>", "<cmd2>", ...],
  "install": "pip install -e <app>/agent-harness"
}
```

Also add to the Generated CLIs table in `CLAUDE.md`.

---

## Pipeline Complete

The pipeline is NOT done until ALL of these are checked:

### Smoke Tests
- [ ] Auth works (login + status, or N/A for no-auth)
- [ ] At least one READ returns real data
- [ ] At least one WRITE succeeds (or N/A for read-only)

### Skills (TWO copies)
- [ ] `.claude/skills/<app>-cli/SKILL.md` exists (Claude Code discovery)
- [ ] `cli_web/<app>/skills/SKILL.md` exists (portable with pip install)
- [ ] Used `cli-anything-web-plugin/templates/SKILL.md.template` as starting point

### Package
- [ ] `setup.py` has `package_data={"": ["skills/*.md", "*.md"]}`
- [ ] `__main__.py` exists for `python -m cli_web.<app>` support

### Documentation
- [ ] `cli_web/<app>/README.md` exists (used `templates/README.md.template`)
- [ ] `<APP>.md` API map exists
- [ ] `tests/TEST.md` has Part 1 (plan) + Part 2 (results)

### Repo-Level Updates
- [ ] `README.md` — new row in examples table + "Try them" section
- [ ] `README.md` — badge count updated (`CLIs_generated-N` and `N_CLIs` hero badge)
- [ ] `CLAUDE.md` — new row in Generated CLIs table
- [ ] `registry.json` — entry with name, website, protocol, auth, commands, install
- [ ] `docs/registry/index.html` — entry added to JS data array with correct category
- [ ] `CHANGELOG.md` — entry added under [Unreleased] → Added
- [ ] `.github/workflows/tests.yml` — new CLI added to CI test matrix (see below)

### CI Test Matrix Update (MANDATORY)

Every new CLI MUST be added to `.github/workflows/tests.yml` so unit tests run
on every push/PR. **Do both steps — missing either blocks merges.**

**Step 1: Add to test matrix** in `.github/workflows/tests.yml`:

```yaml
- { name: <app>, dir: <app>/agent-harness, pkg: <app_underscore> }
```

Where `<app_underscore>` replaces hyphens with underscores (e.g., `gh-trending` → `gh_trending`).

**Step 2: Add to branch protection required checks** so PRs require the new check:

```bash
# Get current checks, append the new one, update
gh api repos/<owner>/<repo>/branches/main/protection/required_status_checks \
  -X PATCH --input - <<EOF
{"strict": true, "contexts": [...existing..., "<app>"]}
EOF
```

Verify the entry runs: `python -m pytest <dir>/cli_web/<pkg>/tests/test_core.py -v`

All key rules (naming, auth, --json, REPL, rate limits) are defined in
HARNESS.md "Critical Rules" and CLAUDE.md "Critical Conventions".

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
