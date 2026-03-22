---
name: sync-check
description: Use after fixing a bug, adding a command, changing auth behavior, or modifying any CLI code to ensure all related documentation stays synchronized. Also use before committing changes, after refactoring, or when you notice documentation drift. Triggers on "sync check", "update docs", "propagate changes", "did I forget to update", "what else needs updating", or "before I commit".
---

# Sync Check

After any code change, verify all related files are synchronized. This catches
the "fixed the bug but forgot to update the skill/SOP/plugin docs" problem.

## How to Use

Run `/sync-check` after making changes. It will:
1. Detect what changed (from git diff or conversation context)
2. Check all downstream files that depend on the change
3. Report what's out of sync
4. Offer to fix each one

## The Dependency Web

Every change touches multiple files. Here's the full map:

### Code Change → Documentation Updates

```
CLI code changed (client.py, commands/*.py, auth.py)
  ├── .claude/skills/<app>-cli/SKILL.md     (commands, output fields, examples)
  ├── <app>/agent-harness/<APP>.md           (SOP: rpcid table, data models)
  ├── <app>/agent-harness/cli_web/<app>/README.md  (usage examples, deps)
  ├── <app>/agent-harness/setup.py           (dependencies)
  └── <app>_cli.py _print_repl_help()        (REPL help must list all commands)
```

### Bug Fix → Plugin Lesson Updates

```
Bug found and fixed in any CLI
  ├── Was it a pattern that could repeat in future CLIs?
  │   YES → Add to the relevant plugin reference file:
  │   ├── auth-strategies.md "Known Pitfalls" table    (auth bugs)
  │   ├── google-batchexecute.md                       (RPC/batchexecute bugs)
  │   ├── ssr-patterns.md "HTML Scraping Pitfalls"     (scraping bugs)
  │   ├── protection-detection.md                      (anti-bot/WAF bugs)
  │   └── traffic-patterns.md                          (protocol detection bugs)
  │
  ├── Is it a universal lesson (applies to ALL CLIs)?
  │   YES → Add to HARNESS.md "Lessons Learned" cross-reference table
  │
  └── Does it change a critical convention?
      YES → Update CLAUDE.md "Critical Conventions" section
```

### New Command Added → Full Update Chain

```
New command added to a CLI
  ├── .claude/skills/<app>-cli/SKILL.md     (add command + options + output fields)
  ├── <app>_cli.py _print_repl_help()        (add to REPL help)
  ├── <app>/agent-harness/<APP>.md           (add endpoint to API map)
  ├── README.md (repo root)                  (if it changes the CLI's capabilities)
  └── Run: cli-web-<app> <new-cmd> --json    (verify output matches skill docs)
```

### Auth/Protection Change → Cross-Cutting Updates

```
Auth behavior changed
  ├── auth-strategies.md                     (patterns, pitfalls, code examples)
  ├── HARNESS.md lessons table               (cross-reference)
  ├── testing/SKILL.md                       (auth prereqs)
  ├── standards/SKILL.md                     (smoke test steps)
  └── CLAUDE.md                              (critical conventions)

Anti-bot/protection change (e.g., httpx → curl_cffi)
  ├── protection-detection.md                (strategy, detection)
  ├── <app>/agent-harness/<APP>.md           (site profile, HTTP client)
  ├── <app>/agent-harness/setup.py           (dependencies)
  ├── <app>/agent-harness/cli_web/<app>/README.md  (deps section)
  ├── CLAUDE.md generated CLIs table         (protocol column)
  └── README.md (repo root)                  (protocol column)
```

## Sync Check Procedure

### Step 1: Identify What Changed

```bash
# Check git diff for changed files
git diff --name-only HEAD
# Or if already committed:
git diff --name-only HEAD~1
```

### Step 2: Classify the Change

Ask yourself:
- **Which CLI?** Extract from file path (booking, futbin, notebooklm, etc.)
- **What type of change?**
  - Bug fix → needs lesson propagation?
  - New command → needs skill + REPL + SOP update?
  - Auth change → cross-cutting update?
  - Dependency change → setup.py + README?
  - RPC/protocol change → SOP + batchexecute ref?

### Step 3: Run Verification Commands

For the affected CLI:

```bash
# Verify commands match skill docs
cli-web-<app> --help
cli-web-<app> <subgroup> --help

# Verify output fields match skill docs
cli-web-<app> <primary-command> --json | head -20

# Verify auth works (if auth CLI)
cli-web-<app> auth status --json
```

### Step 4: Check Each Downstream File

For each file in the dependency chain above:
1. Read the file
2. Find the section that relates to your change
3. Verify it matches the current code behavior
4. Update if stale

### Step 5: Plugin Lesson Check (Bug Fixes Only)

If you fixed a bug, ask:

> "Would this bug happen again if someone generated a new CLI tomorrow?"

If YES, add it to the appropriate plugin reference file:

| Bug Category | Add To |
|-------------|--------|
| Auth (cookies, login, tokens, refresh) | `auth-strategies.md` Known Pitfalls |
| RPC (wrong IDs, wrong params, parsing) | `google-batchexecute.md` |
| HTML scraping (selectors, noise, slugs) | `ssr-patterns.md` HTML Scraping Pitfalls |
| Anti-bot (blocked, 401, 403, challenges) | `protection-detection.md` |
| Output (raw data leak, wrong fields) | `testing/SKILL.md` CLI Output Sanity Checks |
| Downloads (URLs, cookies, formats) | `auth-strategies.md` Known Pitfalls |
| General (UTF-8, Windows, rate limits) | HARNESS.md Lessons table + relevant ref |

Format for Known Pitfalls: `| Symptom | Cause | Fix |`

### Step 6: Verify with --json

After all updates, run one command per affected CLI with `--json` to confirm
the output still matches what the skill documents.

## Quick Reference: File Locations

| What | Where |
|------|-------|
| CLI skills | `.claude/skills/<app>-cli/SKILL.md` |
| CLI SOPs | `<app>/agent-harness/<APP>.md` |
| CLI READMEs | `<app>/agent-harness/cli_web/<app>/README.md` |
| Plugin capture skill | `cli-anything-web-plugin/skills/capture/SKILL.md` |
| Plugin methodology skill | `cli-anything-web-plugin/skills/methodology/SKILL.md` |
| Plugin testing skill | `cli-anything-web-plugin/skills/testing/SKILL.md` |
| Plugin standards skill | `cli-anything-web-plugin/skills/standards/SKILL.md` |
| Auth strategies ref | `cli-anything-web-plugin/skills/methodology/references/auth-strategies.md` |
| Batchexecute ref | `cli-anything-web-plugin/skills/methodology/references/google-batchexecute.md` |
| SSR patterns ref | `cli-anything-web-plugin/skills/methodology/references/ssr-patterns.md` |
| Protection ref | `cli-anything-web-plugin/skills/capture/references/protection-detection.md` |
| HARNESS.md | `cli-anything-web-plugin/HARNESS.md` |
| CLAUDE.md | `CLAUDE.md` (repo root) |
| README.md | `README.md` (repo root) |
