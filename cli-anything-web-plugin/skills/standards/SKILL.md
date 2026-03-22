---
name: standards
description: >
  Quality standards and Phase 4 publish/verify for cli-web-* CLIs. Covers the
  75-check quality checklist, package publishing (pip install -e .), end-user
  smoke testing (READ + WRITE), and final pipeline verification.
  TRIGGER when: "validate CLI", "publish CLI", "pip install -e .", "smoke test",
  "quality check", "start Phase 4", "75-check", "generate Claude skill", "check
  if implementation is complete", or after testing skill completes.
  DO NOT trigger for: traffic capture, implementation, or test writing.
version: 0.2.0
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

## Phase 4: Publish and Verify

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

After smoke tests pass, three tasks remain — all independent, dispatch in parallel:

```
┌─ Agent 1: Generate Claude Skill (.claude/skills/<app>-cli/SKILL.md)
├─ Agent 2: Update repository README.md (add CLI to examples table)
└─ Agent 3: Write/update cli_web/<app>/README.md (package docs)
All 3 are independent — launch in one message with run_in_background: true
```

### Generate Claude Skill

**Goal:** Create a project-local Claude skill so that Claude can use this CLI
automatically in future conversations — no manual lookup required.

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

---

## Pipeline Complete

The pipeline is done when:
- Auth works (login + status, or N/A for no-auth)
- At least one READ returns real data
- At least one WRITE succeeds (or N/A for read-only)
- `.claude/skills/<app>-cli/SKILL.md` exists
- README.md updated

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
