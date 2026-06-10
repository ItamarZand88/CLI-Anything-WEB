---
name: standards
version: 0.5.0
description: >
  Runs Phase 4 review/publish/verify for a cli-web-* CLI: implementation review by
  3 parallel agents, the tiered quality checklist (Tier 1 critical fail-fast, then
  comprehensive), pip install + smoke test, and per-CLI skill generation. Use when a
  CLI's tests pass and it is ready to be validated and published.
when_to_use: >
  Trigger phrases: "validate CLI", "publish CLI", "review CLI", "smoke test",
  "quality check", "start Phase 4", "quality checklist", "generate Claude skill",
  "verify implementation quality", or after the testing skill completes. Not for
  capture, implementation, or test writing.
---

# CLI-Anything-Web Standards (Phase 4: Review + Publish + Verify)

Quality gate for cli-web-* CLIs. This skill owns the complete Phase 4:
independent implementation review, structural quality checklist, publishing,
and end-user smoke testing. Nothing ships until this phase passes.

Copy this checklist and check off items as you complete them:

```
Phase 4 Progress:
- [ ] Prerequisites: tests 100% pass, TEST.md Parts 1+2, <APP>.md present
- [ ] Step 1: 3 review agents dispatched, Critical findings = 0
- [ ] Step 2: validate-checklist Tier 1 exits 0, then full run reviewed
- [ ] Step 3: pip install -e . verified (binary on PATH, --help, doctor)
- [ ] Step 4: end-user smoke test — auth, READ, WRITE all pass
- [ ] Step 5: per-CLI skill generated (passes test_skill_quality.py)
- [ ] Step 6: registry entry added, devkit gates green, repo docs updated
- [ ] phase-state marked complete
```

---

## Prerequisites (Hard Gate)

Do NOT start unless:
- [ ] All tests pass (100% pass rate from Phase 3)
- [ ] TEST.md has both Part 1 (plan) and Part 2 (results)
- [ ] All core modules are implemented and functional
- [ ] `<APP>.md` (API map) exists and documents all endpoints

If tests are not passing, invoke the `testing` skill first. If this gate or
the phase state is in a failed/inconsistent state, follow
`skills/shared/RECOVERY.md` §phase-state Check Failures.

**Optional pre-review coverage scan:** before dispatching the review agents,
you MAY run the `gap-analyzer` skill
(`${CLAUDE_PLUGIN_ROOT}/skills/gap-analyzer/SKILL.md`, pass
`APP_PATH=<app>/agent-harness`) to diff captured endpoints
(`<APP>.md` + `traffic-capture/traffic-analysis.json`) against implemented
commands. It is *optional* here because the traffic-fidelity-reviewer agent
covers endpoint coverage during Step 1; gap-analyzer is the *mandatory first
step* of `/refine`, where no reviewer pass exists. Run it here when coverage
looks doubtful and you want the structured report before the agents start.

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
- `harness-compliance-reviewer` — Code conventions incl. JSON envelope STRUCTURE (reads CONVENTIONS.md + all source)
- `output-ux-reviewer` — User experience (runs --help, checks REPL, validates JSON)

Pass each agent: APP_PATH=`{app}/agent-harness`, APP_NAME=`{app}`, and site
profile (auth_type, is_read_only). The agents are defined in the plugin's
`agents/` directory.

| Agent | Focus | What it reads | What it catches |
|-------|-------|---------------|-----------------|
| Traffic Fidelity | API coverage | `<APP>.md` + `client.py` + `commands/` | Missing endpoints, wrong params, broken response parsing, dead client methods, stale API map |
| HARNESS Compliance | Code quality + JSON envelope structure | CONVENTIONS.md + checklist + all source | click.ClickException bypass, missing to_dict(), retry_after lost, auth retry missing, stderr UTF-8 |
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

## Step 2: Structural Quality Checklist (tiered)

The checklist is tiered (see `references/quality-checklist.md` "Tiers"):
**Tier 1 (critical)** failures block publish; **Tier 2 (comprehensive)**
failures are warnings that should still be fixed.

**2a. Tier 1 fail-fast first.** Run only the critical checks and fix every
FAIL before doing anything else — there is no point reviewing a CLI whose
structure, packaging, or `--json` envelope is broken:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/validate-checklist.py \
  <app>/agent-harness --app-name <app> --auth-type <auth-type> --tier1-only
```

Non-zero exit = Tier 1 failures. Fix and re-run until it exits 0.

**2b. Full run.** Then run the complete checklist (both tiers):

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/validate-checklist.py \
  <app>/agent-harness --app-name <app> --auth-type <auth-type>
```

The summary shows per-tier counts. Exit is non-zero only on Tier 1 failures
(add `--strict` to make Tier 2 failures blocking too). Fix Tier 2 FAILs
before publishing unless explicitly deferred with a reason.

The validator automates the mechanical checks; the remaining judgment-based
items (documentation quality, error message guidance, fixture realism) are
reviewed manually per `references/quality-checklist.md`.

---

## Step 3: Install and Verify

`setup.py` was generated by scaffold-cli.py in Phase 2 (namespace packages,
entry point, profile-correct dependencies) — verify it, don't rewrite it.

```bash
cd <app>/agent-harness
pip install -e .
which cli-web-<app>          # entry point on PATH
cli-web-<app> --help         # command tree renders
cli-web-<app> doctor         # environment self-diagnosis (install, auth, deps)
```

If `doctor` reports fail-level findings, fix them before the smoke test —
they are exactly the problems an end user would hit first.

---

## Step 4: End-User Smoke Test (MANDATORY)

Run the automated smoke test first for quick validation:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/smoke-test.py cli-web-<app> --auth-type <auth-type>
```

This checks CLI binary resolution, --help, --version, auth status, and --json
output for protocol leaks. Then proceed with manual verification below.

This is the most critical verification step. The agent MUST simulate what a real
end user would do after `pip install cli-web-<app>`. If this fails, the pipeline
is NOT complete -- go back and fix the issue.

**If no-auth site:** Skip items 1-2 (auth). Go directly to item 3 (READ).

**If read-only site:** Skip item 4 (WRITE). Verify reads return real data.

**1. Authenticate as an end user would:**
```bash
cli-web-<app> auth login
```
This uses Python sync_playwright() -- opens a browser, user logs in,
cookies saved. This is what end users will run. If this fails, the CLI is
broken for end users.

**2. Verify auth status shows LIVE VALIDATION OK:**
```bash
cli-web-<app> auth status
```
Must show: cookies present, tokens valid. If it shows "expired", "redirect",
or any auth failure -- STOP. Fix auth before proceeding.

**3. Run a READ operation and verify real data:**
```bash
cli-web-<app> --json <first-resource> list
```
This must return real data from the live API -- NOT an error, NOT empty,
NOT "auth not configured". Verify the JSON response contains expected fields.

**4. Run a WRITE operation and verify it actually worked:**
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

**5. Only after items 1-4 ALL pass, continue to Step 5.**

### Smoke Test Checklist

- [ ] `auth login` works (Python playwright, API key, or N/A for no-auth)
- [ ] `auth status` shows valid (or N/A for no-auth)
- [ ] At least one READ returns real data
- [ ] **At least one WRITE/CREATE/GENERATE succeeds** (or N/A for read-only)
- [ ] The CLI works standalone -- no debug Chrome, no port 9222, no MCP
- [ ] **Output sanity: no raw protocol data leaks in `--json` output** (see below)

### Output Sanity

Run every command with `--json` and check for raw protocol leaks (`wrb.fr`, `af.httprm`,
empty `[]`, null required fields). Full red-flags table:
`skills/shared/CONVENTIONS.md` §Protocol-Leak Smoke Check.

**#1 gap to watch for:** Agent runs `list` (GET with auth — easy), declares done, but
never tests create/generate (POST with CSRF, encoding). Always test at least one write.

---

## Step 5: Generate the Per-CLI Skill

See "Generate Claude Skill" below. The skill must pass the quality gate
before Step 6.

## Step 6: Register the CLI (registry-driven — most repo docs are generated)

`registry.json` is the source of truth: the CI test matrix, the README fleet
table, and the install block are all **generated from it**. Add the registry
entry, then run the generators — never edit those outputs by hand:

```bash
# 1. Add the entry to registry.json (schema below), then:
cli-web-devkit registry validate     # entry <-> fleet cross-check
cli-web-devkit docs                  # regenerates README table + install block
cli-web-devkit about --apply         # syncs the GitHub "About" CLI count (needs gh admin)
cli-web-devkit resync --app <app>    # vendored files in sync + manifest updated
cli-web-devkit drift                 # must report 0 drifted/missing

# 2. Offline fleet contract for the new CLI (help/version/REPL/MCP/doctor):
python -m pytest tests/contract -q -k <app>
```

Remaining hand-edited files (independent — update in parallel if you like):
- `CHANGELOG.md` — entry under [Unreleased] -> Added
- `CLAUDE.md` — row in the Generated CLIs table
- `docs/registry/index.html` — entry in the JS data array
- `README.md` hero badge counts (outside the generated markers)
- `cli_web/<app>/README.md` — fill in the scaffolded skeleton

**Start from the scaffolded skeletons.** `scaffold-cli.py` (v2) already
rendered `README.md` and the per-CLI `SKILL.md` skeletons from
`templates/README.md.tpl` and `templates/SKILL.md.tpl` during Phase 2 —
fill in the remaining placeholders with actual CLI data from `<app> --help`
and `<APP>.md` rather than writing from scratch.

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

1. **Read `references/skill-authoring.md` first** — it defines the frontmatter
   rules, description format, body limits, and the standard section structure.
   The skeleton rendered from `templates/SKILL.md.tpl` during Phase 2 already
   follows it; fill in the FILL_IN markers.
2. Run `cli-web-<app> --help` and each group's `--help` — every command you
   document must be verified against the real surface (a stale example is
   worse than no example).
3. Validate before publishing: the skill must pass
   `python -m pytest ${CLAUDE_PLUGIN_ROOT}/scripts/tests/test_skill_quality.py`
   (frontmatter fields, description ≤1024 chars third-person, body ≤500 lines,
   reference links resolve).

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
- [ ] Based on the scaffolded skeleton from `templates/SKILL.md.tpl`

### Package
- [ ] `setup.py` has `package_data={"": ["skills/*.md", "*.md"]}`
- [ ] `__main__.py` exists for `python -m cli_web.<app>` support

### Documentation
- [ ] `cli_web/<app>/README.md` exists (filled in from the `templates/README.md.tpl` skeleton)
- [ ] `<APP>.md` API map exists
- [ ] `tests/TEST.md` has Part 1 (plan) + Part 2 (results)

### Repo-Level Updates
- [ ] `registry.json` — entry with name, website, protocol, auth, commands,
      install, description, skill path (+ `canary` read-only invocations for
      no-auth CLIs). The CI matrix and README table derive from this entry.
- [ ] `cli-web-devkit registry validate` + `docs` + `drift` all green
- [ ] `python -m pytest tests/contract -k <app>` passes (offline contract)
- [ ] `CHANGELOG.md` — entry added under [Unreleased] → Added
- [ ] `CLAUDE.md` — new row in Generated CLIs table
- [ ] `docs/registry/index.html` — entry added to JS data array
- [ ] `README.md` hero badge counts updated (outside the generated markers)
- [ ] Branch protection: if required status checks are pinned by job name, add
      the new matrix job names — the matrix itself updates automatically from
      registry.json (never edit tests.yml)

All key rules (naming, auth, --json, REPL, rate limits) are defined in
`skills/shared/CONVENTIONS.md` — HARNESS.md and CLAUDE.md only index them.

When every box above is checked, mark the pipeline finished:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/phase-state.py complete <app> --phase standards
```

---

## Integration

| Relationship | Skill |
|-------------|-------|
| **Preceded by** | `testing` (Phase 3) |
| **Followed by** | None — this is the final phase |
| **References** | HARNESS.md (Generated CLI Structure), `skills/shared/CONVENTIONS.md` (all rules), `skills/shared/RECOVERY.md` (gate failures) |

---

## Related

- **`testing`** skill -- Phase 3 test planning/writing/documentation
- **`methodology`** skill -- Phase 2 analyze/design/implement
- **`capture`** skill -- Phase 1 traffic recording
- **`/cli-anything-web:validate`** -- Command to run the full tiered checklist validation
- **`gap-analyzer`** skill -- Optional coverage scan (mandatory first step of `/refine`)
