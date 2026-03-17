---
name: web-reconnaissance
description: >
  Analyze any website before building a CLI. Detects frameworks, APIs, and protections.
  Trigger phrases: "recon", "analyze site", "detect framework", "check protections",
  "what kind of site", "before recording"
version: 0.1.0
---

# Web Reconnaissance Skill

Systematic site analysis before any capture or CLI generation. Run reconnaissance
**first** on every new target to avoid wasted effort and wrong strategies.

## When to Run Recon

- **Always** before the first capture of a new site
- When a previous capture strategy failed or returned incomplete data
- When you suspect the site uses protections (Cloudflare, CAPTCHA, WAF)
- When the user says "recon", "analyze site", "detect framework", "check protections",
  "what kind of site", or "before recording"

## When to Skip Recon

- **Known sites** where you already have a working RECON-REPORT.md
- **Refine runs** — iterating on an existing capture that already works
- **Simple static pages** the user has confirmed are plain HTML

---

## 5-Step Reconnaissance Flow

### Step 1.1: Open & Observe

Open the target in a headed browser and take a snapshot of the initial state.

```bash
# Launch browser and navigate to the target
npx @playwright/cli@latest -s=recon open "https://target-site.com"

# Capture a DOM snapshot of the loaded page
npx @playwright/cli@latest -s=recon snapshot

# Check for a common SPA root element
npx @playwright/cli@latest -s=recon eval "document.querySelector('#app, #root, #__next, #__nuxt, #__sveltekit')?.id || 'no-spa-root'"
```

**What to look for:**

- Immediate content vs. loading spinners (SSR vs. SPA)
- Cookie consent banners or popups that need dismissing
- Whether the URL changes on navigation (client-side routing)
- Skeleton screens indicating API-driven dynamic content

---

### Step 1.2: Framework Detection

Run eval scripts to identify the frontend framework and SSR data strategy.
See [framework-detection.md](references/framework-detection.md) for the full
list of detection commands.

```bash
# Next.js Pages Router — check for __NEXT_DATA__
npx @playwright/cli@latest -s=recon eval "document.getElementById('__NEXT_DATA__')?.textContent?.substring(0, 200)"

# Nuxt 2/3 — check for __NUXT__
npx @playwright/cli@latest -s=recon eval "typeof window.__NUXT__ !== 'undefined' ? JSON.stringify(Object.keys(window.__NUXT__)) : 'not-nuxt'"

# Generic SPA root detection
npx @playwright/cli@latest -s=recon eval "document.querySelector('#app, #root, #__next, #__nuxt, #__sveltekit')?.id || 'no-spa-root'"
```

Record the framework, SSR data embedding method, and any hydration markers.

---

### Step 1.3: Network Traffic Analysis (Force SPA Navigation Trick)

**This is the most important recon step.** Many sites (especially SSR) show zero
API calls on initial page load because data is embedded in the HTML. The trick:
start tracing BEFORE clicking internal links — SPA client-side navigation reveals
hidden API endpoints that the initial load hides.

This works because: on first load, the server renders everything. But when you
click a link, the SPA router takes over and fetches data via API instead of
doing a full page reload. Those API calls are what we need for CLI generation.

```bash
# Start tracing BEFORE navigation — this is critical
npx @playwright/cli@latest -s=recon tracing-start

# Click through 3-4 representative internal links
# SPA router will make client-side API fetches!
npx @playwright/cli@latest -s=recon click "a[href*='/products']"
npx @playwright/cli@latest -s=recon click "a[href*='/about']"
npx @playwright/cli@latest -s=recon click "a[href*='/search']"
npx @playwright/cli@latest -s=recon click "a[href*='/category']"

# Stop tracing and save
npx @playwright/cli@latest -s=recon tracing-stop

# Parse the captured trace into structured JSON
python scripts/parse-trace.py .playwright-cli/traces/ --output recon-traffic.json
```

Inspect `recon-traffic.json` for:
- REST endpoints (`/api/v1/`, `/api/v2/`)
- GraphQL endpoints (`/graphql`)
- SSR data routes (`/_next/data/`, `/__data.json`)
- Internal/undocumented APIs (`/_api/`, `/internal/`)

**Missing an endpoint? Use the feature, don't reverse-engineer JS.**

If you see a button or feature in the UI (e.g., "Create", "Generate", "Submit")
but its API endpoint doesn't appear in the trace, it means you didn't trigger
that feature during the trace. The fix:

1. Start a new trace: `tracing-start`
2. Take a screenshot to see the UI: `screenshot`
3. Use the feature: `click` the button, `fill` the form, submit
4. Stop: `tracing-stop` → parse → the endpoint is now captured

Never spend more than 2 minutes searching for an endpoint. If you can see it
in the UI, capture it by using it. The browser IS the API documentation.

---

### Step 1.4: Protection Assessment

Run the all-in-one detection eval to check for anti-bot measures.
See [protection-detection.md](references/protection-detection.md) for details.

```bash
npx @playwright/cli@latest -s=recon eval "(() => {
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

Also check robots.txt:

```bash
npx @playwright/cli@latest -s=recon open "https://target-site.com/robots.txt"
npx @playwright/cli@latest -s=recon snapshot
```

---

### Step 1.5: Generate RECON-REPORT.md

Compile all findings into a structured report using this template:

```markdown
# Reconnaissance Report — <app>

**URL:** <url>
**Date:** YYYY-MM-DD

## Site Architecture

| Aspect | Expected (pre-recon) | Confirmed (post-recon) |
|--------|---------------------|----------------------|
| Type | SPA / SSR / Hybrid | (fill after Step 1.1) |
| Framework | Next.js / Nuxt / React / Vue / None | (fill after Step 1.2) |
| SSR Data | __NEXT_DATA__ / __NUXT__ / None | (fill after Step 1.2) |

**Always make predictions BEFORE running commands.** This helps you know
what to look for and catches unexpected findings faster.

## API Surface

| Endpoint | Method | Auth? | Discovered in |
|----------|--------|-------|---------------|
| /api/... | GET | Yes | Step 1.3 trace |
| ... | ... | ... | ... |

- **Protocol:** REST / GraphQL / batchexecute / None
- **Total endpoints found:** X
- **Auth type:** cookies / Bearer JWT / API key / None

## Protections

| Protection | Expected | Confirmed |
|-----------|----------|-----------|
| Cloudflare | Yes/No | (fill after Step 1.4) |
| CAPTCHA | Yes/No | (fill after Step 1.4) |
| Rate limits | Yes/No | (fill after Step 1.4) |
| WAF (other) | None / Akamai / PerimeterX | (fill after Step 1.4) |
| robots.txt | Permissive / Restrictive | (fill after Step 1.4) |

## Recommended Strategy

- **Capture approach:** API-first / SSR+API hybrid / Full trace / Protected-manual
- **Rationale:** (explain why this strategy based on findings above)
- **CLI generation impact:** (what kind of client.py — standard httpx / query templates / rpc codec)
- **Warnings:** (rate limits, token expiry, protection concerns, viability risks)
```

**Make predictions first, confirm after.** Fill the "Expected" column based on
what you know about the site (e.g., "Suno is likely a React SPA with REST API").
Then fill "Confirmed" after running each step. This catches surprises early.

Save this report alongside the project. It drives all downstream capture and
generation decisions.

---

## Reference Files

- [Framework Detection](references/framework-detection.md) — SSR framework eval commands
- [Protection Detection](references/protection-detection.md) — Anti-bot and WAF checks
- [API Discovery](references/api-discovery.md) — API finding priority chain
- [Strategy Selection](references/strategy-selection.md) — Decision tree for capture approach
