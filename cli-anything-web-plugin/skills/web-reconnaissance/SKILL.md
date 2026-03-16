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

### Step 1.3: Network Traffic Analysis

Start a trace, navigate through 3-4 representative pages, then stop and parse.

```bash
# Start tracing network traffic
npx @playwright/cli@latest -s=recon tracing-start

# Click through representative internal links
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

- Type: SPA / SSR / Hybrid / Static
- Framework: Next.js / Nuxt / Remix / SvelteKit / React / Vue / None
- SSR Data: __NEXT_DATA__ / __NUXT__ / None

## API Surface

- Protocol: REST / GraphQL / batchexecute / None
- Endpoints discovered: (list)
- Auth required: Yes/No (type)

## Protections

- Cloudflare: Yes/No
- CAPTCHA: Yes/No
- Rate limits: Detected/Not
- Other WAF: None / Akamai / PerimeterX / DataDome

## Recommended Strategy

- Capture approach: API-first / SSR+API / Full trace / Protected-manual
- Rationale: (why)
- Warnings: (concerns)
```

Save this report alongside the project. It drives all downstream capture and
generation decisions.

---

## Reference Files

- [Framework Detection](references/framework-detection.md) — SSR framework eval commands
- [Protection Detection](references/protection-detection.md) — Anti-bot and WAF checks
- [API Discovery](references/api-discovery.md) — API finding priority chain
- [Strategy Selection](references/strategy-selection.md) — Decision tree for capture approach
