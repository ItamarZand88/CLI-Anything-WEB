# Plugin Restructure: Skill-Per-Phase Architecture

**Date:** 2026-03-17
**Status:** Approved
**Branch:** `playwright-migration`

---

## Goal

Restructure the plugin to follow Anthropic's official best practices: break the
856-line HARNESS.md into self-contained skills that each own their pipeline phase,
with skill-to-skill sequencing replacing central document references. This achieves
proper progressive disclosure — loading only the relevant phase's content, not
the entire methodology.

---

## Key Principles (from Anthropic's official best practices)

1. **SKILL.md under 500 lines** — move detailed content to references/
2. **Skills are self-contained** — each skill has all knowledge for its phase
3. **Skill sequencing = methodology** — "When done, invoke `skill-name`"
4. **Hard gates prevent skipping** — "Do NOT proceed until X is complete"
5. **References one level deep** — SKILL.md → references/, never deeper
6. **Commands invoke skills** — thin entry points, not duplicate documentation
7. **Progressive disclosure** — metadata always loaded, SKILL.md on trigger, references on demand
8. **No central HARNESS.md methodology** — skills own the methodology

---

## New Architecture

### HARNESS.md → Lean Orchestrator (~200 lines)

HARNESS.md becomes a high-level overview that:
- States the core philosophy (30 lines)
- Lists the tool hierarchy (15 lines)
- Shows the **pipeline sequence** as a skill chain (40 lines)
- Lists all reference materials with phase mapping (25 lines)
- States the critical rules (non-negotiable standards) (40 lines)
- States naming conventions (15 lines)
- Provides the generated CLI structure template (35 lines)

**HARNESS.md does NOT contain:**
- Phase implementation details (moved to skills)
- Exploration checklists (moved to capture skill)
- Test patterns (moved to testing skill)
- Auth implementation (moved to references)
- Parallel dispatch guidance (moved to methodology skill)

### Skill Ownership Map

| Skill | Phases Owned | Lines (target) | Key Content |
|-------|-------------|----------------|-------------|
| `web-reconnaissance` | 1a | ~250 | 5-step recon flow, RECON-REPORT template (already exists, minor updates) |
| `capture` | 1 | ~300 | **NEW** — setup, tracing, exploration checklist, parse-trace.py, auth save, WRITE verification |
| `methodology` | 2, 3, 4 | ~400 | Analyze, Design, Implement with parallel dispatch. Absorbs Phase 2-4 from HARNESS |
| `testing` | 5, 6, 7 | ~350 | Plan tests, write tests, document. Already mostly there, absorbs Phase 5-7 from HARNESS |
| `standards` | 8 + validation | ~300 | Publish, smoke test (READ+WRITE), 50-check validation. Absorbs Phase 8 from HARNESS |
| `auto-optimize` | (meta) | ~200 | Unchanged — optimization loop methodology |

### Skill Sequencing (replaces HARNESS.md phases)

Each skill ends with a **Next Step** section that invokes the next skill:

```
web-reconnaissance (Phase 1a)
  → "Next: invoke capture to start recording"

capture (Phase 1)
  → "Next: invoke methodology to analyze traffic"

methodology (Phase 2-4)
  → "Next: invoke testing to plan and write tests"

testing (Phase 5-7)
  → "Next: invoke standards to publish and verify"

standards (Phase 8)
  → "Pipeline complete. Verify all smoke tests pass."
```

### Hard Gates (in each skill)

Each skill starts with a gate that verifies prerequisites:

```markdown
## Prerequisites (Hard Gate)

Do NOT proceed unless:
- [ ] RECON-REPORT.md exists (from Phase 1a) OR site is already known
- [ ] raw-traffic.json exists with WRITE operations (from Phase 1)

If any prerequisite is missing, invoke the relevant earlier skill first.
```

---

## New Skill: `capture`

Currently Phase 1 content lives in HARNESS.md (108 lines). This becomes its own skill:

```yaml
---
name: capture
description: >
  Capture HTTP traffic from web apps using playwright-cli tracing. Handles browser
  setup, trace recording, systematic exploration (READ + WRITE operations), auth
  state persistence, and trace parsing. Use when recording traffic, starting Phase 1,
  or when the agent needs to capture API calls from a web app.
version: 0.1.0
---
```

**Body contains:**
- Setup (create dirs, open browser, save auth)
- Tracing flow (tracing-start → explore → tracing-stop)
- Exploration checklist by app type (CRUD, Generation, Search, Chat)
- WRITE operations requirement ("trace MUST contain POST/PUT before stopping")
- Post-capture verification script
- "Use the feature, don't reverse-engineer JS" guidance
- MCP fallback instructions
- **Next Step:** "Invoke `methodology` to analyze the captured traffic"
- **Hard Gate at end:** "Do NOT proceed to Phase 2 until raw-traffic.json has WRITE operations"

**References (from existing methodology references, MOVED here):**
- `playwright-cli-tracing.md` → moves to `capture/references/`
- `playwright-cli-sessions.md` → moves to `capture/references/`
- `playwright-cli-advanced.md` → moves to `capture/references/`

---

## Updated Skills

### `methodology` (Phases 2, 3, 4)

Currently 63 lines (just a pointer to HARNESS.md). Absorbs:
- Phase 2: Analyze (parse raw-traffic.json, identify protocol, map endpoints) — from HARNESS.md:270-314
- Phase 3: Design (CLI command tree, auth design, REPL design) — from HARNESS.md:315-346
- Phase 4: Implement (package structure, parallel subagent dispatch, auth.py patterns) — from HARNESS.md:347-472

**References stay:**
- `traffic-patterns.md` (used in Phase 2)
- `auth-strategies.md` (used in Phase 4)
- `google-batchexecute.md` (used in Phase 2+4)
- `ssr-patterns.md` (used in Phase 2)

**Sequencing:**
- **Gate:** "Do NOT start unless raw-traffic.json exists"
- **Next:** "Invoke `testing` to plan and write tests"

### `testing` (Phases 5, 6, 7)

Currently 214 lines. Already mostly self-contained. Absorbs:
- Phase 5: Plan tests (TEST.md Part 1) — from HARNESS.md:473-514
- Phase 6: Test (write tests, parallel dispatch, auth-first) — from HARNESS.md:515-590
- Phase 7: Document (append TEST.md Part 2) — from HARNESS.md:591-615

**Sequencing:**
- **Gate:** "Do NOT start unless Phase 4 implementation is complete"
- **Next:** "Invoke `standards` to publish and verify"

### `standards` (Phase 8 + validation)

Currently 155 lines. Absorbs:
- Phase 8: Publish and verify (install, smoke test READ+WRITE) — from HARNESS.md:616-690

**Sequencing:**
- **Gate:** "Do NOT start unless all tests pass"
- **Next:** "Pipeline complete. All smoke tests must pass including WRITE operations."

### `web-reconnaissance` (Phase 1a)

Currently 224 lines. Already self-contained. Only change:
- Add explicit **Next Step:** "Invoke `capture` to start recording"
- Add **Hard Gate:** "Do NOT proceed to capture until RECON-REPORT.md strategy is confirmed"

### `auto-optimize` (meta)

Unchanged — already self-contained at 203 lines.

---

## Updated HARNESS.md (~200 lines)

New structure:

```markdown
# HARNESS.md — CLI-Anything-Web Methodology

## Core Philosophy
(30 lines — what this plugin does, authentic integration, dual interaction)

## Tool Hierarchy
(15 lines — playwright-cli PRIMARY, chrome-devtools FALLBACK, claude-in-chrome NEVER)

## Pipeline: Skill Sequence
(40 lines — the 8-phase pipeline as skill invocations)

| Phase | Skill | What it does |
|-------|-------|-------------|
| 1a (optional) | `web-reconnaissance` | Detect framework, APIs, protections |
| 1 | `capture` | Trace traffic, explore app, save auth |
| 2-4 | `methodology` | Analyze, design, implement CLI |
| 5-7 | `testing` | Plan tests, write tests, document |
| 8 | `standards` | Publish, verify, smoke test |

Each skill invokes the next when done. Hard gates prevent skipping.

## Reference Materials
(25 lines — table mapping all 11 references to phases)

## Critical Rules
(40 lines — non-negotiable standards: auth secure, tests fail not skip,
--json everywhere, WRITE smoke test, CAPTCHA handling, content download)

## Naming Conventions
(15 lines — CLI command, namespace, SOP doc patterns)

## Generated CLI Structure
(35 lines — the package template that Phase 4 produces)
```

---

## Updated Commands

All commands become thin invocations of skills:

### `cli-anything-web.md` (full pipeline)

```markdown
## Execution Plan

Run the full pipeline by invoking skills in sequence:

1. `/cli-anything-web:recon <url>` (optional for unfamiliar sites)
2. Invoke `capture` skill for Phase 1
3. Invoke `methodology` skill for Phases 2-4
4. Invoke `testing` skill for Phases 5-7
5. Invoke `standards` skill for Phase 8

Each skill handles its phases and invokes the next when done.
See HARNESS.md for the pipeline overview and critical rules.
```

### `record.md`

```markdown
Invoke the `capture` skill for Phase 1 traffic recording.
If --recon-only: invoke `web-reconnaissance` skill instead.
```

---

## File Changes Summary

### New files:
| File | Lines | Content |
|------|-------|---------|
| `skills/capture/SKILL.md` | ~300 | Phase 1 methodology (from HARNESS.md:161-269) |
| `skills/capture/references/playwright-cli-tracing.md` | 129 | MOVED from methodology refs |
| `skills/capture/references/playwright-cli-sessions.md` | 218 | MOVED from methodology refs |
| `skills/capture/references/playwright-cli-advanced.md` | 211 | MOVED from methodology refs |

### Major rewrites:
| File | From | To | Change |
|------|------|------|--------|
| `HARNESS.md` | 856 lines | ~200 lines | Strip phases → lean orchestrator |
| `methodology/SKILL.md` | 63 lines | ~400 lines | Absorb Phases 2-4 from HARNESS |
| `testing/SKILL.md` | 214 lines | ~350 lines | Absorb Phases 5-7 from HARNESS |
| `standards/SKILL.md` | 155 lines | ~300 lines | Absorb Phase 8 from HARNESS |

### Minor updates:
| File | Change |
|------|--------|
| `web-reconnaissance/SKILL.md` | Add Next Step + Hard Gate |
| `commands/cli-anything-web.md` | Thin wrapper invoking skill sequence |
| `commands/record.md` | Thin wrapper invoking capture skill |
| `commands/test.md` | Thin wrapper invoking testing skill |
| `commands/validate.md` | Thin wrapper invoking standards skill |
| `verify-plugin.sh` | Add `capture` skill check |

### Moved (not deleted):
| From | To |
|------|------|
| `methodology/references/playwright-cli-tracing.md` | `capture/references/playwright-cli-tracing.md` |
| `methodology/references/playwright-cli-sessions.md` | `capture/references/playwright-cli-sessions.md` |
| `methodology/references/playwright-cli-advanced.md` | `capture/references/playwright-cli-advanced.md` |

---

## Token Impact

| Scenario | Before (tokens loaded) | After (tokens loaded) |
|----------|----------------------|---------------------|
| Agent starts Phase 1 capture | 856 (all HARNESS) | ~300 (capture skill only) |
| Agent writes tests (Phase 6) | 856 (all HARNESS) + 214 (testing skill) | ~350 (testing skill only) |
| Agent validates (Phase 8) | 856 (all HARNESS) + 155 (standards skill) | ~300 (standards skill only) |
| Agent does recon (Phase 1a) | 856 (all HARNESS) + 224 (recon skill) | ~250 (recon skill only) |

**Average reduction: ~60% fewer tokens per phase.**

---

## What Does NOT Change

- Reference file content (traffic-patterns.md, auth-strategies.md, etc.) — only location of 3 files
- Generated CLI structure (cli_web namespace, setup.py, etc.)
- auto-optimize skill and infrastructure
- All Python scripts (parse-trace.py, grade_output.py, etc.)
- eval-suite.json and integration-suite.json
- Plugin manifest (plugin.json)
- .mcp.json
- ReplSkin

---

## Out of Scope

- Rewriting reference file content
- Changing eval assertions
- Modifying generated CLIs (notebooklm, futbin, suno)
- Adding new features
