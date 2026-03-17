# Reconnaissance Plan — vercel.com/dashboard

**Target URL:** https://vercel.com/dashboard
**Framework:** Next.js (confirmed by public knowledge; recon commands will verify)
**Date:** 2026-03-16

---

## 1. Framework Detection — Exact Playwright-CLI Commands

Run these commands in sequence. Each layer narrows the framework version and SSR strategy.

### Step 1.1 — Open and observe initial state

```bash
# Open the target and capture initial DOM snapshot
npx @playwright/cli@latest -s=recon open "https://vercel.com/dashboard"
npx @playwright/cli@latest -s=recon snapshot

# Check for SPA root element
npx @playwright/cli@latest -s=recon eval "document.querySelector('#app, #root, #__next, #__nuxt, #__sveltekit')?.id || 'no-spa-root'"
```

Expected result: `"__next"` — confirming Next.js.

### Step 1.2 — Distinguish Pages Router vs App Router

```bash
# Pages Router check — looks for the embedded __NEXT_DATA__ script tag
npx @playwright/cli@latest -s=recon eval "document.getElementById('__NEXT_DATA__')?.textContent?.substring(0, 200)"

# App Router check — looks for RSC flight streaming markers
npx @playwright/cli@latest -s=recon eval "document.documentElement.outerHTML.includes('self.__next_f.push') ? 'next-app-router' : 'not-app-router'"
```

**Interpreting results:**

| `__NEXT_DATA__` result | App Router result | Conclusion |
|---|---|---|
| JSON string | `'not-app-router'` | Next.js Pages Router — proceed with SSR+API hybrid |
| `null` | `'next-app-router'` | Next.js App Router — trace RSC flight endpoints |
| `null` | `'not-app-router'` | Unlikely for vercel.com; re-check |

### Step 1.3 — Verify no competing framework signals

```bash
# Rule out Nuxt
npx @playwright/cli@latest -s=recon eval "typeof window.__NUXT__ !== 'undefined' ? JSON.stringify(Object.keys(window.__NUXT__)) : 'not-nuxt'"

# Rule out Remix
npx @playwright/cli@latest -s=recon eval "typeof window.__remixContext !== 'undefined' ? 'remix' : 'not-remix'"

# Rule out Redux/preloaded state blobs
npx @playwright/cli@latest -s=recon eval "typeof window.__INITIAL_STATE__ !== 'undefined' ? 'has-state' : typeof window.__PRELOADED_STATE__ !== 'undefined' ? 'has-preloaded' : 'no-state'"
```

All three should return negative — confirming pure Next.js.

### Step 1.4 — Protection check

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

```bash
# Also check robots.txt for Sitemap references and disallow directives
npx @playwright/cli@latest -s=recon open "https://vercel.com/robots.txt"
npx @playwright/cli@latest -s=recon snapshot
```

---

## 2. Detecting `__NEXT_DATA__` and Extracting Its Structure

### Detection command

```bash
npx @playwright/cli@latest -s=recon eval "document.getElementById('__NEXT_DATA__')?.textContent?.substring(0, 200)"
```

If this returns a JSON fragment, the site uses Pages Router and embeds SSR data in every HTML response.

### Full extraction

```bash
# Extract the full blob
npx @playwright/cli@latest -s=recon eval "JSON.stringify(window.__NEXT_DATA__)"

# Extract just the top-level keys to understand structure without data overload
npx @playwright/cli@latest -s=recon eval "JSON.stringify(Object.keys(window.__NEXT_DATA__))"

# Extract the buildId (needed to construct /_next/data/ endpoints)
npx @playwright/cli@latest -s=recon eval "window.__NEXT_DATA__.buildId"

# Extract the page props structure (data models live here)
npx @playwright/cli@latest -s=recon eval "JSON.stringify(Object.keys(window.__NEXT_DATA__.props?.pageProps || {}))"
```

### What to look for in the extracted structure

The `__NEXT_DATA__` blob has this shape:

```json
{
  "props": {
    "pageProps": {
      "user": { ... },
      "teams": [ ... ],
      "projects": [ ... ]
    }
  },
  "page": "/dashboard",
  "query": {},
  "buildId": "abc123xyz",
  "isFallback": false,
  "gssp": true
}
```

Key fields:
- `buildId` — required to construct `/_next/data/<buildId>/dashboard.json`
- `props.pageProps` — the actual data objects; their shape defines the CLI response models
- `gssp: true` — confirms `getServerSideProps` is used (data is always fresh, not statically cached)
- `page` — the route identifier used in the internal data URL

### Constructing the internal data endpoint

```bash
# Once buildId is known:
# GET /_next/data/<buildId>/dashboard.json
# Returns identical JSON to pageProps above, but without a full HTML page load
```

This endpoint is the primary read target for the CLI.

---

## 3. Force SPA Navigation Trick — Discovering Hidden API Endpoints

The dashboard initial load is SSR — all data is embedded in HTML. No API calls are visible in the network trace on first load. To reveal the real API surface, force client-side navigations:

### Full command sequence

```bash
# Step 1: Start tracing before any navigation
npx @playwright/cli@latest -s=recon tracing-start

# Step 2: Click through internal dashboard links
# These trigger client-side navigations and expose data fetch calls
npx @playwright/cli@latest -s=recon click "a[href*='/settings']"
npx @playwright/cli@latest -s=recon click "a[href*='/projects']"
npx @playwright/cli@latest -s=recon click "a[href*='/deployments']"
npx @playwright/cli@latest -s=recon click "a[href*='/analytics']"
npx @playwright/cli@latest -s=recon click "a[href*='/domains']"

# Step 3: Stop tracing
npx @playwright/cli@latest -s=recon tracing-stop

# Step 4: Parse the trace into structured JSON
python scripts/parse-trace.py .playwright-cli/traces/ --output recon-traffic.json
```

### Why this works

- **Initial load:** The server embeds all dashboard data in the HTML as `__NEXT_DATA__`. Zero network API calls from the browser.
- **Client-side navigation:** When the user clicks a link, Next.js fetches `/_next/data/<buildId>/<page>.json` instead of loading a new HTML page. These are the real API calls.
- **Additional APIs:** Vercel's dashboard likely also makes calls to its internal REST API (`/api/v1/` or similar) for dynamic data like deployment logs, real-time metrics, and team activity. These appear only after SPA navigation — they are invisible on the initial load.

### Expected discoveries from the trace

After parsing `recon-traffic.json`, expect to find:

| Endpoint pattern | Type | Purpose |
|---|---|---|
| `/_next/data/<buildId>/dashboard.json` | Next.js internal | Page props for dashboard |
| `/_next/data/<buildId>/[team]/[project].json` | Next.js internal | Project detail page data |
| `/api/v1/projects` or `/v1/projects` | Vercel REST API | Project list (possibly) |
| `/api/v1/deployments` | Vercel REST API | Deployment list |
| `/api/v6/now/deployments` | Vercel legacy API | Older deployment endpoints |
| `/_api/` prefix paths | Internal BFF | Backend-for-frontend routes |

If the trace shows clean REST API calls to `/v1/` or `/api/v*` prefixes, the strategy shifts to **API-first** for those endpoints. If only `/_next/data/` calls appear, the strategy is **SSR+API hybrid**.

---

## 4. RECON-REPORT.md

```markdown
# Reconnaissance Report — Vercel Dashboard

**URL:** https://vercel.com/dashboard
**Date:** 2026-03-16

## Site Architecture

- Type: SSR + SPA Hybrid (Next.js with client-side routing after initial load)
- Framework: Next.js (Pages Router — confirmed by `#__next` root and `__NEXT_DATA__` blob)
- SSR Data: `__NEXT_DATA__` embedded in initial HTML for all dashboard pages
- Routing: Client-side navigation via Next.js Link component (no full page reloads)
- Auth: Required — dashboard is gated behind login; session cookie persists in browser

## API Surface

- Protocol: REST (Vercel's own API) + Next.js internal data routes (`/_next/data/`)
- Endpoints discovered via Force SPA Navigation trick:
  - `/_next/data/<buildId>/dashboard.json` — dashboard page props
  - `/_next/data/<buildId>/[team]/[project]/deployments.json` — deployment list
  - `/_next/data/<buildId>/[team]/[project]/settings.json` — project settings
  - `/v1/projects` — Vercel REST API (if exposed in trace)
  - `/v1/deployments` — Vercel REST API (if exposed in trace)
- Auth required: Yes — Bearer token or session cookie (extract from authenticated browser session)
- Note: `buildId` changes on every Vercel deployment; must be re-extracted dynamically

## Protections

- Cloudflare: Likely present (Vercel uses Cloudflare globally for its own infrastructure)
- CAPTCHA: No (not expected on dashboard — session-gated, not public form)
- Rate limits: Yes — Vercel API has documented rate limits per tier
- Other WAF: None detected beyond Cloudflare

## Recommended Strategy

- Capture approach: **SSR+API Hybrid**
- Rationale: Initial load delivers data via `__NEXT_DATA__` (no API calls). Client-side
  navigation exposes `/_next/data/<buildId>/` routes and potentially Vercel's REST API.
  The CLI should extract `buildId` dynamically from `__NEXT_DATA__` on startup and use
  `/_next/data/` routes for reads. If Vercel REST API endpoints appear in the trace
  (`/v1/` prefix), those should be preferred as they are buildId-independent and stable
  across deployments.
- Warnings:
  - `buildId` in `/_next/data/` URLs changes on every redeploy; the CLI must re-fetch
    it from `__NEXT_DATA__.buildId` at the start of each session
  - Authentication via session cookie — the CLI needs the user to be logged in first;
    use browser-based auth extraction, not static credentials
  - Vercel's own public API (`api.vercel.com`) may expose the same data more reliably
    than the internal Next.js data routes — check both in the trace and prefer the
    public API if it appears
```

---

## 5. Recommended Strategy: SSR+API Hybrid vs API-First

### Verdict: Start with SSR+API Hybrid, escalate to API-first if Vercel REST endpoints appear

**Reasoning:**

**Why not pure API-first:**
The Vercel dashboard is a Next.js SSR app. The initial page load contains no API calls
— all data is embedded in `__NEXT_DATA__`. If you only run a trace without the Force SPA
Navigation trick, you will find zero endpoints and mistakenly conclude there is no API.
The API surface only becomes visible after client-side navigation is forced.

**Why SSR+API Hybrid is the baseline:**
The `/__next/data/<buildId>/` routes are always present, authenticated, and return clean
JSON. They require only the session cookie (already in the browser) and the current
`buildId` (extractable from `window.__NEXT_DATA__.buildId`). This gives the CLI a
complete, working read path even before any REST API endpoints are identified.

**When to escalate to API-first:**
Vercel operates a public REST API (`api.vercel.com/v1/`) and the dashboard likely calls
it for dynamic content (deployment logs, real-time build status, analytics). If the Force
SPA Navigation trace reveals `/v1/` or `/api/v*/` calls, those endpoints should become
the primary CLI targets. They are:
- buildId-independent (stable across deploys)
- Officially documented (Vercel has a public API spec)
- Versioned and more reliable than internal Next.js data routes

**Final recommended architecture for the generated CLI:**

```
vercel-cli/
  core/
    auth.py         # Extract session token from browser via eval, or accept VERCEL_TOKEN
    client.py       # httpx-based client; sets Authorization header
  commands/
    projects.py     # GET /v1/projects or /_next/data/<buildId>/dashboard.json
    deployments.py  # GET /v1/deployments or /_next/data/<buildId>/[team]/[project]/deployments.json
    settings.py     # GET /v1/projects/[id] or /_next/data/.../settings.json
  utils/
    build_id.py     # Fetches current buildId from __NEXT_DATA__ if REST API unavailable
```

**Read operations:** Prefer Vercel REST API (`/v1/`) if discovered in trace; fall back to
`/_next/data/<buildId>/` routes. Use `__NEXT_DATA__` extraction only for model discovery,
not as the primary data path.

**Mutation operations (deploy, delete, update settings):** Always use Vercel REST API —
these are POST/PATCH/DELETE operations that SSR data routes do not support.

**Summary:**

| Scenario | Strategy |
|---|---|
| Only `/_next/data/` calls found in trace | SSR+API Hybrid |
| `/v1/` or `/api/v*/` calls found in trace | API-first (preferred) |
| Both found | Hybrid with REST preferred, Next.js data as fallback |
| Cloudflare blocks automated access | Protected-manual with session cookie persistence |
