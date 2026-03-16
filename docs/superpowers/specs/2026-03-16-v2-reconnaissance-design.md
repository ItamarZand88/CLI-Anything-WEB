# V2 Reconnaissance + SSR Patterns Design

**Date:** 2026-03-16
**Status:** Approved
**Branch:** `playwright-migration` (building on top of V1)

---

## Goal

Add intelligent reconnaissance as a pre-step to Phase 1 traffic capture. Before
blindly recording all traffic, the agent first discovers the site's architecture
(SPA vs SSR, API protocol, framework, protections) and selects the optimal capture
strategy. Also add SSR framework detection patterns for sites like Next.js, Nuxt,
Remix, and SvelteKit where data is embedded in the HTML rather than fetched via API.

---

## Why

Currently Phase 1 jumps straight to `tracing-start` and captures everything. This
wastes time on static assets and misses SSR-embedded data. Problems observed:

| Problem | How reconnaissance fixes it |
|---------|---------------------------|
| Agent captures 1000+ requests but most are static assets | Recon identifies API patterns first, agent targets them |
| SSR site has data in `__NEXT_DATA__` but agent doesn't know | Framework detection finds embedded data blobs |
| Site has Cloudflare protection, agent gets blocked | Protection detection warns before capture starts |
| No API found but agent spends hours trying | Recon flags "pure SSR — may not be CLI-suitable" early |
| Agent doesn't know if GraphQL, REST, or batchexecute | Protocol identification in recon guides client architecture |

---

## New Skill: `web-reconnaissance`

### `skills/web-reconnaissance/SKILL.md`

Entry point for the reconnaissance flow. Triggers on: "recon", "analyze site",
"detect framework", "check protections", before Phase 1 when `--recon-only` is used.

**5-step flow** (adapted from yfe404/web-scraper `workflows/reconnaissance.md`,
translated from Playwright MCP to playwright-cli Bash commands):

```
Step 1.1: Open & Observe
  → playwright-cli -s=recon open <url> --headed --persistent
  → playwright-cli -s=recon snapshot
  → Observe: loading spinners? skeleton screens? SPA root (#app, #root, #__next)?

Step 1.2: Framework Detection
  → Run eval scripts for Next.js, Nuxt, Remix, SvelteKit, Gatsby, Google WIZ
  → Detect SPA root element
  → Check for SSR data blobs (__NEXT_DATA__, __NUXT__, etc.)
  → See references/framework-detection.md for all eval commands

Step 1.3: Network Traffic Analysis (quick probe)
  → playwright-cli -s=recon tracing-start
  → Click 3-4 internal navigation links (force SPA client-side fetches)
  → playwright-cli -s=recon tracing-stop
  → Parse trace → identify API patterns (/api/, /graphql, /_next/data/, batchexecute)
  → See references/api-discovery.md for priority chain

Step 1.4: Protection Assessment
  → Run anti-bot detection eval script
  → Check for Cloudflare, CAPTCHA, rate limits, WAF
  → See references/protection-detection.md

Step 1.5: Generate RECON-REPORT.md
  → Structured report with findings
  → Recommended capture strategy
  → See references/strategy-selection.md for decision tree
```

**RECON-REPORT.md template:**

```markdown
# Reconnaissance Report — <app>

**URL:** <url>
**Date:** YYYY-MM-DD

## Site Architecture
- **Type:** SPA / SSR / Hybrid / Static
- **Framework:** Next.js / Nuxt / Remix / SvelteKit / React / Vue / None detected
- **SSR Data:** __NEXT_DATA__ found / __NUXT__ found / None

## API Surface
- **Protocol:** REST / GraphQL / batchexecute / None found
- **Endpoints discovered:** (list from quick probe)
- **Auth required:** Yes/No (type: cookies / Bearer / API key)

## Protections
- **Cloudflare:** Yes/No
- **CAPTCHA:** Yes/No (type)
- **Rate limits:** Detected/Not detected
- **Other WAF:** None / Akamai / PerimeterX / DataDome

## Recommended Strategy
- **Capture approach:** API-first / SSR+API hybrid / Full trace / Protected-manual
- **Rationale:** (why this strategy)
- **Warnings:** (any concerns)
```

### `references/framework-detection.md`

All playwright-cli eval commands for detecting SSR frameworks:

- Next.js Pages Router: `eval "document.getElementById('__NEXT_DATA__')?.textContent?.substring(0, 200)"`
- Next.js App Router: check for `_next/data/` in network trace
- Nuxt 2/3: `eval "typeof window.__NUXT__"`
- Remix: `eval "typeof window.__remixContext"`
- SvelteKit: `eval "typeof window.__sveltekit_data"` or `data-sveltekit-hydrate`
- Gatsby: `eval "typeof window.___gatsby"`
- Google batchexecute: `eval "typeof WIZ_global_data"`
- Generic SPA: `eval "document.querySelector('#app, #root, #__next, #__nuxt')?.id"`
- Redux/Vuex state: `eval "typeof window.__INITIAL_STATE__"`

Each entry includes: the eval command, what the return value means, and which
CLI generation strategy to use.

### `references/protection-detection.md`

Single playwright-cli eval script that checks all protections at once:

```bash
playwright-cli -s=recon eval "(() => {
  const body = document.body.textContent.toLowerCase();
  const html = document.documentElement.outerHTML;
  const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
  return {
    cloudflare: body.includes('cloudflare') || html.includes('cf-ray') || html.includes('__cf_bm'),
    captcha: !!document.querySelector('.g-recaptcha, #px-captcha, .h-captcha'),
    akamai: scripts.some(s => s.includes('akamai')),
    datadome: scripts.some(s => s.includes('datadome')),
    perimeterx: scripts.some(s => s.includes('perimeterx') || s.includes('px-')),
    rateLimit: html.includes('429') || body.includes('too many requests'),
    fingerprinting: scripts.some(s => s.includes('fingerprint') || s.includes('fp-'))
  };
})()"
```

Plus: robots.txt check, Cloudflare cf-ray header detection, rate limit header analysis.

### `references/api-discovery.md`

Priority chain (fastest → slowest):

```
1. REST API (/api/v1/, /api/v2/) → direct JSON, fastest
2. GraphQL (/graphql) → single endpoint, structured queries
3. Next.js data (/_next/data/BUILD_ID/...) → SSR JSON blobs
4. WordPress API (/wp-json/wp/v2/) → if WordPress site
5. Shopify API (/products.json) → if Shopify
6. Google batchexecute (/_/<Service>/data/batchexecute) → Google apps
7. Internal APIs (/_api/, /internal/api/) → undocumented
8. HTML scraping → LAST RESORT, may not be CLI-suitable
```

Plus: Force SPA Navigation trick (start tracing → click internal links → SPA
router makes client-side fetches revealing hidden API endpoints).

### `references/strategy-selection.md`

Decision tree from reconnaissance findings to capture strategy:

```
Reconnaissance Complete
├── API endpoints found in trace?
│   ├── YES (many) → API-first: Standard trace capture
│   │   └── Generates: standard client.py with httpx
│   ├── YES (few, mutations only) → Check for SSR data blobs
│   │   ├── __NEXT_DATA__/__NUXT__ found → SSR+API hybrid
│   │   └── No blobs → Force SPA trick, re-check
│   └── YES (GraphQL) → GraphQL capture
│       └── Generates: client.py with query templates
│
├── No API endpoints found?
│   ├── Google WIZ_global_data → batchexecute protocol
│   │   └── Generates: rpc/ subpackage
│   ├── Pure SSR, no client fetches → ⚠️ May not be CLI-suitable
│   └── APIs blocked by protection → Protected-manual strategy
│
└── Protection detected?
    ├── Cloudflare → Add delays, respect limits
    ├── Rate limits → Build backoff into client.py
    └── CAPTCHA → Add pause-and-prompt to auth flow
```

---

## New Reference: `ssr-patterns.md`

**File:** `skills/cli-anything-web-methodology/references/ssr-patterns.md`

Covers:
- What SSR means for CLI generation (data is in HTML, not API)
- Framework-specific data extraction patterns
- Force SPA Navigation trick (detailed explanation with playwright-cli commands)
- When SSR data extraction is viable vs when to wait for client-side fetches
- Strategy: extract initial data from SSR blobs, capture mutations from API calls

---

## Updates to Existing Files

### `commands/record.md`

Add `--recon-only` to argument-hint:
```
argument-hint: <url> [--recon-only] [--duration <minutes>]
```

New flow: if `--recon-only`, run recon skill only, output RECON-REPORT.md, done.
If full recording: run recon first → show report → confirm strategy → proceed.

### `commands/web-harness.md` (currently empty)

Populate as the reconnaissance-focused command:
```yaml
name: cli-anything-web:recon
description: Run reconnaissance on a web app before traffic capture. Detects framework, API patterns, and protections.
argument-hint: <url>
allowed-tools: Bash(*), Read, Write, Edit
```

This gives users a standalone `/cli-anything-web:recon <url>` command.

### `HARNESS.md`

Add Step 1a to Phase 1:

```markdown
### Phase 1a — Reconnaissance (Optional but Recommended)

Before capturing traffic, run reconnaissance to understand the site:

```bash
/cli-anything-web:recon <url>
# Or during full pipeline, the agent runs recon automatically
```

Skip for known sites (e.g., second run of /cli-anything-web:refine).
Always do for unfamiliar sites.

Output: `<app>/agent-harness/RECON-REPORT.md`
```

### `skills/cli-anything-web-methodology/SKILL.md`

Add `web-reconnaissance` to companion skills table:
```
| **web-reconnaissance** | Analyzing unfamiliar sites, detecting frameworks, choosing capture strategy |
```

Add `references/ssr-patterns.md` to Reference Files list.

### `references/traffic-patterns.md`

Add new section "SSR / Server-Rendered Sites":
- Detection signals (HTML contains full data, no XHR on initial load)
- Common frameworks (Next.js, Nuxt, Remix, SvelteKit)
- Force SPA Navigation trick
- Reference to `ssr-patterns.md` for full patterns

### `skills/cli-anything-web-standards/SKILL.md`

Add optional recon checks:
- RECON-REPORT.md exists for unfamiliar sites
- Framework documented in `<APP>.md`
- Capture strategy documented

---

## What Does NOT Change

- 8-phase pipeline structure (recon is Phase 1a, additive)
- Phase 1b capture flow (unchanged)
- Phases 2-8 (unchanged)
- Generated CLI structure
- All 3 existing skills (methodology, testing, standards — minor updates only)
- ReplSkin, parse-trace.py, verify-plugin.sh
- All reference docs content (google-batchexecute.md, auth-strategies.md)

---

## Out of Scope

- Auth cleanup across 3 showcases (separate session)
- Building new showcase CLIs
- Changes to existing generated CLIs
- Deleting any existing files
