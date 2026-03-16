# V2 Reconnaissance + SSR Patterns Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a web-reconnaissance skill with framework detection, protection detection, API discovery, and strategy selection — plus SSR pattern references — as an additive Phase 1a to the existing pipeline.

**Architecture:** Create a new `web-reconnaissance` skill with 5 reference files, add `ssr-patterns.md` to the methodology skill, update HARNESS.md/commands/skills to integrate reconnaissance as an optional pre-step before traffic capture.

**Tech Stack:** Markdown, playwright-cli eval commands, Bash

**Spec:** `docs/superpowers/specs/2026-03-16-v2-reconnaissance-design.md`

**Reference material:** `reference-skills/web-scraper/` (cloned, read-only — adapt patterns for playwright-cli)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `skills/web-reconnaissance/SKILL.md` | **CREATE** | Recon skill entry point — 5-step flow, RECON-REPORT template |
| `skills/web-reconnaissance/references/framework-detection.md` | **CREATE** | SSR framework eval commands |
| `skills/web-reconnaissance/references/protection-detection.md` | **CREATE** | Anti-bot detection eval script |
| `skills/web-reconnaissance/references/api-discovery.md` | **CREATE** | API finding priority chain |
| `skills/web-reconnaissance/references/strategy-selection.md` | **CREATE** | Decision tree from recon → strategy |
| `skills/cli-anything-web-methodology/references/ssr-patterns.md` | **CREATE** | SSR data extraction patterns |
| `commands/web-harness.md` | **POPULATE** | Recon command (currently empty) |
| `commands/record.md` | **UPDATE** | Add `--recon-only`, recon-first flow |
| `HARNESS.md` | **UPDATE** | Add Phase 1a Reconnaissance |
| `skills/cli-anything-web-methodology/SKILL.md` | **UPDATE** | Add companion skill + reference |
| `references/traffic-patterns.md` | **UPDATE** | Add SSR section |
| `skills/cli-anything-web-standards/SKILL.md` | **UPDATE** | Add recon checks |
| `verify-plugin.sh` | **UPDATE** | Add web-reconnaissance skill check |

---

## Chunk 1: New Skill Files (Tasks 1-5)

### Task 1: Create web-reconnaissance SKILL.md

**Files:**
- Create: `cli-anything-web-plugin/skills/web-reconnaissance/SKILL.md`

- [ ] **Step 1: Create directory and write SKILL.md**

Read `reference-skills/web-scraper/workflows/reconnaissance.md` for inspiration. Then write the full SKILL.md adapted for playwright-cli. Must include:

- YAML frontmatter with name, description (include trigger phrases), version
- 5-step reconnaissance flow with exact playwright-cli commands
- RECON-REPORT.md template (complete with all sections from the spec)
- When to skip recon (known sites, refine runs)
- Pointers to all 4 reference files

The description field must be "pushy" for triggering — include phrases like: "recon", "analyze site", "detect framework", "check protections", "what kind of site is this", "before recording", "Phase 1a".

- [ ] **Step 2: Commit**

```bash
git add cli-anything-web-plugin/skills/web-reconnaissance/SKILL.md
git commit -m "feat: create web-reconnaissance skill with 5-step recon flow"
```

---

### Task 2: Create framework-detection.md

**Files:**
- Create: `cli-anything-web-plugin/skills/web-reconnaissance/references/framework-detection.md`

- [ ] **Step 1: Write framework-detection.md**

Include ALL detection commands from the spec's Part 4, organized as a reference table. For each framework:
- The playwright-cli eval command
- What the return value means
- Which CLI generation strategy to use

Frameworks to cover: Next.js (Pages + App Router), Nuxt 2/3, Remix, SvelteKit, Gatsby, Google batchexecute, Generic SPA, Redux/Vuex state.

Also include the "Force SPA Navigation Trick" — when initial load shows no API calls because data is SSR-embedded, start tracing BEFORE clicking internal links to reveal hidden API endpoints.

- [ ] **Step 2: Commit**

```bash
git add cli-anything-web-plugin/skills/web-reconnaissance/references/framework-detection.md
git commit -m "docs: add framework detection reference (Next.js, Nuxt, Remix, etc.)"
```

---

### Task 3: Create protection-detection.md

**Files:**
- Create: `cli-anything-web-plugin/skills/web-reconnaissance/references/protection-detection.md`

- [ ] **Step 1: Write protection-detection.md**

Adapt from `reference-skills/web-scraper/strategies/anti-blocking.md` but translate all `playwright_evaluate` calls to `playwright-cli eval`. Include:

- The all-in-one protection detection eval script from the spec
- Cloudflare detection (cf-ray header, __cf_bm cookie, challenge page)
- Rate limit detection (429, retry-after, x-ratelimit-* headers)
- CAPTCHA detection (reCAPTCHA, hCaptcha)
- WAF detection (Akamai, Imperva, PerimeterX, DataDome)
- robots.txt analysis command
- What each finding means for CLI generation strategy

- [ ] **Step 2: Commit**

```bash
git add cli-anything-web-plugin/skills/web-reconnaissance/references/protection-detection.md
git commit -m "docs: add protection detection reference (Cloudflare, CAPTCHA, WAF)"
```

---

### Task 4: Create api-discovery.md

**Files:**
- Create: `cli-anything-web-plugin/skills/web-reconnaissance/references/api-discovery.md`

- [ ] **Step 1: Write api-discovery.md**

Adapt from `reference-skills/web-scraper/strategies/api-discovery.md`. Include:

- Priority chain (8 levels from the spec: REST → GraphQL → Next.js data → ... → HTML scraping last resort)
- Common API path patterns with examples
- Force SPA Navigation trick with exact playwright-cli commands
- How to identify pagination (offset vs cursor vs page) from trace data
- How to detect auth requirements from captured headers
- Why APIs are better than scraping for CLI generation (adapted from reference)

- [ ] **Step 2: Commit**

```bash
git add cli-anything-web-plugin/skills/web-reconnaissance/references/api-discovery.md
git commit -m "docs: add API discovery reference with priority chain"
```

---

### Task 5: Create strategy-selection.md

**Files:**
- Create: `cli-anything-web-plugin/skills/web-reconnaissance/references/strategy-selection.md`

- [ ] **Step 1: Write strategy-selection.md**

Include the full decision tree from the spec (markdown flowchart format). Also include:

- Strategy comparison table (from spec's Pattern C adapted for CLI generation)
- What each strategy means for the generated CLI's architecture
- When to flag "site may not be CLI-suitable"
- Anti-patterns to avoid (from `reference-skills/web-scraper/reference/anti-patterns.md`)

- [ ] **Step 2: Commit**

```bash
git add cli-anything-web-plugin/skills/web-reconnaissance/references/strategy-selection.md
git commit -m "docs: add strategy selection reference with decision tree"
```

---

## Chunk 2: SSR Patterns + Existing File Updates (Tasks 6-10)

### Task 6: Create ssr-patterns.md

**Files:**
- Create: `cli-anything-web-plugin/skills/cli-anything-web-methodology/references/ssr-patterns.md`

- [ ] **Step 1: Write ssr-patterns.md**

Adapt from `reference-skills/web-scraper/strategies/hybrid-approaches.md`. Include:

- What SSR means for CLI generation
- Framework-specific data extraction (how to get data from __NEXT_DATA__, __NUXT__, etc.)
- Force SPA Navigation trick (detailed with playwright-cli commands)
- SSR+API hybrid strategy: extract read data from SSR blobs, capture write endpoints from trace
- When SSR data extraction is viable vs when to wait for client-side fetches
- Decision: SSR data for models, API calls for mutations

- [ ] **Step 2: Commit**

```bash
git add cli-anything-web-plugin/skills/cli-anything-web-methodology/references/ssr-patterns.md
git commit -m "docs: add SSR patterns reference for server-rendered sites"
```

---

### Task 7: Populate commands/web-harness.md (recon command)

**Files:**
- Modify: `cli-anything-web-plugin/commands/web-harness.md`

- [ ] **Step 1: Write the recon command**

Replace the empty file with a full command definition:

```markdown
---
name: cli-anything-web:recon
description: Run reconnaissance on a web app to detect framework, API patterns, and protections before traffic capture.
argument-hint: <url>
allowed-tools: Bash(*), Read, Write, Edit
---

## CRITICAL: Read HARNESS.md First

**Before running recon, read `${CLAUDE_PLUGIN_ROOT}/HARNESS.md`.** Phase 1a defines the reconnaissance methodology.

# CLI-Anything-Web: Reconnaissance

Read the methodology SOP:
@${CLAUDE_PLUGIN_ROOT}/HARNESS.md

Target URL: $ARGUMENTS

## Process

This command runs Phase 1a only — reconnaissance without traffic capture.

1. Check playwright-cli: !`npx @playwright/cli@latest --version 2>&1 && echo "OK" || echo "FAIL"`
2. Open browser: `npx @playwright/cli@latest -s=recon open $ARGUMENTS --headed --persistent`
3. Run the 5-step recon flow from the web-reconnaissance skill
4. Generate RECON-REPORT.md at `<app>/agent-harness/RECON-REPORT.md`
5. Close browser: `npx @playwright/cli@latest -s=recon close`
6. Present findings and recommended capture strategy to user

## Output

- `<app>/agent-harness/RECON-REPORT.md` — structured reconnaissance report
- Recommended capture strategy for Phase 1b

## When to Use

- Before first `/cli-anything-web` run on an unfamiliar site
- When you want to understand a site before committing to full traffic capture
- To detect SSR frameworks, protections, or unusual API patterns
```

- [ ] **Step 2: Commit**

```bash
git add cli-anything-web-plugin/commands/web-harness.md
git commit -m "feat: populate web-harness.md as recon command"
```

---

### Task 8: Update commands/record.md (add --recon-only)

**Files:**
- Modify: `cli-anything-web-plugin/commands/record.md`

- [ ] **Step 1: Update argument-hint and add recon-first flow**

Change the argument-hint line in frontmatter to:
```
argument-hint: <url> [--recon-only] [--duration <minutes>]
```

After the Prerequisites section, before the Process section, add:

```markdown
## Reconnaissance (runs first)

If `--recon-only` is specified, run ONLY the recon flow:
1. Follow the web-reconnaissance skill's 5-step flow
2. Output RECON-REPORT.md
3. Done — no traffic capture

If full recording (no `--recon-only`):
1. Run recon first (Steps 1.1-1.5)
2. Show RECON-REPORT.md to user
3. Confirm recommended capture strategy
4. Proceed with traffic capture using the recommended approach
```

- [ ] **Step 2: Commit**

```bash
git add cli-anything-web-plugin/commands/record.md
git commit -m "feat: add --recon-only flag and recon-first flow to record command"
```

---

### Task 9: Update HARNESS.md (add Phase 1a)

**Files:**
- Modify: `cli-anything-web-plugin/HARNESS.md`

- [ ] **Step 1: Insert Phase 1a before Phase 1**

Find `### Phase 1 — Record (Traffic Capture)` and insert BEFORE it:

```markdown
### Phase 1a — Reconnaissance (Optional but Recommended)

Before capturing traffic, run reconnaissance to understand the site architecture.

```bash
/cli-anything-web:recon <url>
# Or the agent runs recon automatically as the first step of /cli-anything-web
```

**When to run recon:**
- Always for unfamiliar sites (first time targeting this web app)
- Skip for known sites (e.g., running /cli-anything-web:refine on existing CLI)
- Skip if user provides a RECON-REPORT.md from a previous run

**What recon discovers:**
- Site type: SPA / SSR / Hybrid
- Framework: Next.js / Nuxt / Remix / SvelteKit / React / Vue
- API protocol: REST / GraphQL / batchexecute / None
- Protections: Cloudflare / CAPTCHA / Rate limits / WAF
- Recommended capture strategy

**Output:** `<app>/agent-harness/RECON-REPORT.md`

See the `web-reconnaissance` skill for the full 5-step flow.

---
```

- [ ] **Step 2: Commit**

```bash
git add cli-anything-web-plugin/HARNESS.md
git commit -m "docs: add Phase 1a Reconnaissance to HARNESS.md pipeline"
```

---

### Task 10: Update remaining files (methodology, traffic-patterns, standards, verify)

**Files:**
- Modify: `cli-anything-web-plugin/skills/cli-anything-web-methodology/SKILL.md`
- Modify: `cli-anything-web-plugin/skills/cli-anything-web-methodology/references/traffic-patterns.md`
- Modify: `cli-anything-web-plugin/skills/cli-anything-web-standards/SKILL.md`
- Modify: `cli-anything-web-plugin/verify-plugin.sh`

- [ ] **Step 1: Update methodology SKILL.md**

Add to the companion skills table:
```
| **web-reconnaissance** | Analyzing unfamiliar sites, detecting frameworks, choosing capture strategy |
```

Add to Reference Files:
```
- **`references/ssr-patterns.md`** — SSR framework patterns and data extraction strategies
```

- [ ] **Step 2: Update traffic-patterns.md**

Add a new section "SSR / Server-Rendered Sites" after the existing sections:

```markdown
## SSR / Server-Rendered Sites

Sites that render data server-side (Next.js, Nuxt, Remix, SvelteKit, Gatsby).

### Detection signals:
- HTML contains full page data on initial load (no XHR/fetch on first render)
- Presence of __NEXT_DATA__, __NUXT__, __remixContext, or similar global objects
- SPA root element (#__next, #__nuxt) with pre-rendered content
- /_next/data/ or /__data.json endpoints in network trace

### CLI mapping:
- Initial data from SSR blobs → use for data models and read endpoints
- Client-side navigation reveals hidden API endpoints (Force SPA Navigation trick)
- Mutation endpoints (create/update/delete) usually go through standard API calls
- Read endpoints may use SSR data routes (/_next/data/) or client-side API

### Reference:
See `references/ssr-patterns.md` for framework-specific extraction patterns
and the Force SPA Navigation trick.
```

- [ ] **Step 3: Update standards SKILL.md**

Add to the Key Rules section or as optional checks:
```
- **Reconnaissance recommended for unfamiliar sites** — RECON-REPORT.md should exist
  in `<app>/agent-harness/` for SSR or protected sites. Framework and strategy documented
  in `<APP>.md`.
```

- [ ] **Step 4: Update verify-plugin.sh**

Add check for the new skill:
```bash
# In the skills loop, add web-reconnaissance:
for skill in cli-anything-web-methodology cli-anything-web-testing cli-anything-web-standards web-reconnaissance; do
```

- [ ] **Step 5: Run verify-plugin.sh to confirm all checks pass**

```bash
cd cli-anything-web-plugin && bash verify-plugin.sh
```
Expected: 18/18 checks pass (was 17, +1 for new skill).

- [ ] **Step 6: Commit**

```bash
git add cli-anything-web-plugin/skills/cli-anything-web-methodology/SKILL.md \
       cli-anything-web-plugin/skills/cli-anything-web-methodology/references/traffic-patterns.md \
       cli-anything-web-plugin/skills/cli-anything-web-standards/SKILL.md \
       cli-anything-web-plugin/verify-plugin.sh
git commit -m "docs: integrate reconnaissance into methodology, standards, and verification"
```

---

### Task 11: Final verification

- [ ] **Step 1: Run verify-plugin.sh**
```bash
cd cli-anything-web-plugin && bash verify-plugin.sh
```
Expected: 18/18 checks pass.

- [ ] **Step 2: Verify all new files exist**
```bash
ls cli-anything-web-plugin/skills/web-reconnaissance/SKILL.md \
   cli-anything-web-plugin/skills/web-reconnaissance/references/framework-detection.md \
   cli-anything-web-plugin/skills/web-reconnaissance/references/protection-detection.md \
   cli-anything-web-plugin/skills/web-reconnaissance/references/api-discovery.md \
   cli-anything-web-plugin/skills/web-reconnaissance/references/strategy-selection.md \
   cli-anything-web-plugin/skills/cli-anything-web-methodology/references/ssr-patterns.md
```

- [ ] **Step 3: Verify web-harness.md is no longer empty**
```bash
wc -l cli-anything-web-plugin/commands/web-harness.md
```
Expected: >30 lines.

- [ ] **Step 4: Verify Phase 1a exists in HARNESS.md**
```bash
grep "Phase 1a" cli-anything-web-plugin/HARNESS.md
```
Expected: match found.
