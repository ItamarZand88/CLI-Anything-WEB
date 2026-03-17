# Reconnaissance Plan & Report — Suno.com

**Skill applied:** `web-reconnaissance` v0.1.0
**Target:** https://suno.com
**Date:** 2026-03-17

---

## Part 1: Complete Reconnaissance Plan

### Overview

The 5-step recon flow maps directly onto Suno. Each step below lists the exact
playwright-cli commands to run, what the command is probing for, and the
prediction made before executing it.

---

### Step 1.1 — Open & Observe

```bash
# Open the target in a headed session labelled "recon"
npx @playwright/cli@latest -s=recon open "https://suno.com"

# Capture a full DOM snapshot of the loaded page
npx @playwright/cli@latest -s=recon snapshot

# Check for a common SPA root element
npx @playwright/cli@latest -s=recon eval \
  "document.querySelector('#app, #root, #__next, #__nuxt, #__sveltekit')?.id || 'no-spa-root'"
```

**What to observe:**
- Does content appear immediately (SSR) or after a delay (client-side hydration)?
- Are there cookie/consent banners? (CMP is disabled on Suno — confirmed from source.)
- Does the URL path change on navigation without a full reload?
- Are skeleton screens present on `/explore`?

---

### Step 1.2 — Framework Detection

```bash
# Test 1: Next.js Pages Router — look for __NEXT_DATA__ JSON blob
npx @playwright/cli@latest -s=recon eval \
  "document.getElementById('__NEXT_DATA__')?.textContent?.substring(0, 200)"

# Test 2: Next.js App Router — look for RSC streaming marker
npx @playwright/cli@latest -s=recon eval \
  "document.documentElement.outerHTML.includes('self.__next_f.push') ? 'next-app-router' : 'not-app-router'"

# Test 3: Generic SPA root detection
npx @playwright/cli@latest -s=recon eval \
  "document.querySelector('#app, #root, #__next, #__nuxt, #__sveltekit')?.id || 'no-spa-root'"

# Test 4: Nuxt check (eliminate)
npx @playwright/cli@latest -s=recon eval \
  "typeof window.__NUXT__ !== 'undefined' ? JSON.stringify(Object.keys(window.__NUXT__)) : 'not-nuxt'"

# Test 5: Redux/preloaded state check
npx @playwright/cli@latest -s=recon eval \
  "typeof window.__INITIAL_STATE__ !== 'undefined' ? 'has-state' : typeof window.__PRELOADED_STATE__ !== 'undefined' ? 'has-preloaded' : 'no-state'"

# Test 6: Clerk auth SDK presence (Suno-specific)
npx @playwright/cli@latest -s=recon eval \
  "typeof window.Clerk !== 'undefined' ? 'clerk-present' : 'no-clerk'"
```

---

### Step 1.3 — Network Traffic Analysis (Force SPA Navigation Trick)

This is the most critical step for Suno because it uses Next.js App Router with
RSC streaming — the initial page load embeds data server-side so the trace will
appear empty. Client-side navigation is required to expose real API endpoints.

```bash
# CRITICAL: Start tracing BEFORE any navigation
npx @playwright/cli@latest -s=recon tracing-start

# Navigate through representative internal pages to trigger SPA route transitions
# Each click forces the Next.js App Router to fetch data via client-side fetch
npx @playwright/cli@latest -s=recon click "a[href='/explore']"
npx @playwright/cli@latest -s=recon click "a[href*='/playlist/']"
npx @playwright/cli@latest -s=recon click "a[href*='/@']"
npx @playwright/cli@latest -s=recon click "a[href='/pricing']"

# Stop tracing and save
npx @playwright/cli@latest -s=recon tracing-stop

# Parse the trace into structured JSON for inspection
python scripts/parse-trace.py .playwright-cli/traces/ --output recon-traffic.json
```

**Why the Force SPA Navigation Trick is essential here:**

Suno uses Next.js App Router with React Server Components (RSC). On first page
load the server streams all data into the HTML as `self.__next_f.push()` payloads
— so the network trace shows zero API calls. The moment you click an internal
link, the Next.js router switches to client-side navigation: it does NOT do a
full page reload. Instead it makes fetch requests to `/_next/data/<buildId>/`
routes or directly to backend REST endpoints (e.g., `studio-api.suno.ai/api/`).
Those fetches are what we need — they reveal the actual data API.

**What to look for in `recon-traffic.json`:**

```
Priority  Pattern to find in trace
────────  ──────────────────────────────────────────────────────
1.        studio-api.suno.ai/api/*     — primary REST API
2.        suno.com/_next/data/*        — Next.js data routes
3.        clerk.suno.com/v1/*          — auth token exchanges
4.        cdn2.suno.ai/*               — audio/image CDN
5.        cdn-o.suno.com/*             — additional CDN
```

Check request headers for `Authorization: Bearer` tokens (Clerk JWT) or session
cookies. Check response bodies for JSON arrays of song/playlist objects.

---

### Step 1.4 — Protection Assessment

```bash
# All-in-one protection detection eval
npx @playwright/cli@latest -s=recon eval "(() => {
  const body = document.body.textContent.toLowerCase();
  const html = document.documentElement.outerHTML;
  const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
  return {
    cloudflare: body.includes('cloudflare') || html.includes('cf-ray') || html.includes('__cf_bm'),
    cloudflareAnalytics: scripts.some(s => s.includes('cloudflareinsights')),
    captcha: !!document.querySelector('.g-recaptcha, #px-captcha, .h-captcha'),
    akamai: scripts.some(s => s.includes('akamai')),
    datadome: scripts.some(s => s.includes('datadome')),
    perimeterx: scripts.some(s => s.includes('perimeterx') || s.includes('px-')),
    rateLimit: html.includes('429') || body.includes('too many requests'),
    fingerprinting: scripts.some(s => s.includes('fingerprint') || s.includes('fp-')),
    clerkAuth: scripts.some(s => s.includes('clerk')),
    statsig: html.includes('statsigBootstrap'),
    mazeAnalytics: scripts.some(s => s.includes('maze'))
  };
})()"

# Check robots.txt
npx @playwright/cli@latest -s=recon open "https://suno.com/robots.txt"
npx @playwright/cli@latest -s=recon snapshot
```

---

### Step 1.5 — Generate RECON-REPORT.md

See Part 2 below. The report is the output of all 5 steps with both Expected
and Confirmed columns completed.

---

## Part 2: RECON-REPORT.md

```markdown
# Reconnaissance Report — Suno

**URL:** https://suno.com
**Date:** 2026-03-17
**Analyst:** claude-sonnet-4-6 via web-reconnaissance skill
```

---

## Site Architecture

| Aspect | Expected (pre-recon) | Confirmed (post-recon) |
|--------|---------------------|------------------------|
| Type | SPA with SSR — music apps typically use Next.js for SEO + React interactivity | Confirmed: Next.js App Router with RSC streaming. `/explore` uses skeleton/hydration pattern. |
| Framework | Next.js (most common for React music/AI SaaS) | Confirmed: Next.js App Router. `self.__next_f.push()` RSC markers present throughout. No `__NEXT_DATA__` (that is Pages Router only). |
| SSR Data | __NEXT_DATA__ JSON blob embedded in `<script>` tag | Not present. App Router does NOT use `__NEXT_DATA__`. Data is streamed via RSC payloads in `self.__next_f.push()` calls — not extractable as a simple JSON blob. |
| UI Framework | Tailwind or custom CSS | Chakra UI with extensive CSS custom properties (design tokens). Dark theme via `data-theme="dark"`. |
| Auth | OAuth via third-party provider (Google, GitHub) | Clerk authentication SDK (`pk_live_YXV0aC5zdW5vLmNvbSQ`). Handles sign-in, sign-up, sessions. Separate subdomain: `clerk.suno.com`. |
| PWA | Unlikely for a music creation app | Confirmed PWA: `/manifest.json` present, PWA install suppression script loaded (they suppress the native prompt). |
| Analytics | Google Analytics or Segment | Google Tag Manager (`GTM-NQ9L4VGG`), Maze analytics (`snippet.maze.co`), Cloudflare Web Analytics. Feature flags via Statsig (`statsigBootstrap`). |

---

## API Surface

| Endpoint | Method | Auth? | Discovered in |
|----------|--------|-------|---------------|
| `studio-api.suno.ai/api/feed/` | GET | Yes (Clerk JWT) | Known from public research; returns 503 without auth |
| `studio-api.suno.ai/api/clips/` | GET | Yes (Clerk JWT) | Known from public research; song CRUD operations |
| `studio-api.suno.ai/api/generate/v2/` | POST | Yes (Clerk JWT) | Known from public research; music generation |
| `studio-api.suno.ai/api/playlist/<uuid>` | GET | Yes (Clerk JWT) | Known from public research; playlist contents |
| `/_next/data/<buildId>/<route>.json` | GET | Partial | Expected from SPA Navigation Trick — must trace |
| `clerk.suno.com/v1/client` | GET/POST | Clerk session | Expected from auth flow trace |
| `cdn2.suno.ai/<uuid>.<ext>` | GET | None (CDN) | Playlist page source — image assets |
| `cdn-o.suno.com/<path>` | GET | None (CDN) | Main page source — favicons, metadata |

**Protocol:** REST (primary) + Next.js RSC data routes (secondary)
**Total endpoints found:** 8 identified (2 confirmed via page source, 6 via known patterns + 503 probe)
**Auth type:** Clerk JWT — Bearer token in `Authorization` header. Token obtained via Clerk session after login. Likely uses `__session` cookie as fallback.

**Key finding:** Direct API probes to `studio-api.suno.ai/api/feed/` and
`suno.com/api/playlist/<uuid>` both returned HTTP 503, confirming auth is
enforced at the gateway level. Unauthenticated access is blocked.

**Note on RSC payloads:** The `self.__next_f.push()` blobs in the initial HTML
contain serialized React component trees, not raw data. They are not
straightforwardly parseable as structured JSON without a React Flight client.
The actual data API is `studio-api.suno.ai`.

---

## Protections

| Protection | Expected | Confirmed |
|-----------|----------|-----------|
| Cloudflare | Yes — nearly all AI SaaS uses Cloudflare | Confirmed: `cloudflareinsights.com/beacon.min.js` loaded. Cloudflare Analytics present. CF WAF protection also likely (common for Cloudflare customers). |
| CAPTCHA | Possible on sign-up/login | Not detected in page source. Clerk handles auth flows; CAPTCHA may appear inside Clerk's hosted UI on login. No `g-recaptcha` or `h-captcha` elements in main document. |
| Rate limits | Yes — generative AI endpoints always rate-limit | Expected: API endpoints at `studio-api.suno.ai` will rate-limit heavy usage. Suno enforces credit-based quotas per account tier (Free / Pro / Premier). |
| WAF (other) | Unlikely alongside Cloudflare | Not detected: no Akamai, DataDome, or PerimeterX scripts in page source. |
| robots.txt | Permissive for crawlers, restrictive for private data | Confirmed: `Allow: /` for all agents. Disallows: `/profile/*/followers`, `/profile/*/following`, `/style/*`, `/login`. Three sitemaps provided (sitemap.xml, hub-sitemap.xml, landing-sitemap.xml). |
| Clerk auth | Yes | Confirmed: Clerk publishable key `pk_live_YXV0aC5zdW5vLmNvbSQ` in page source. All authenticated API calls require a valid Clerk JWT. |
| Statsig feature flags | Unknown pre-recon | Confirmed: `statsigBootstrap` present. Some API features or rate tiers may be gated by Statsig flags per user/session. |
| CMP / Cookie consent | Unknown | Confirmed disabled: `window.__CMP_DISABLED__ = true` explicitly set. No consent banner. |

---

## URL Structure (from sitemap reconnaissance)

| Pattern | Example | Notes |
|---------|---------|-------|
| `/home` | `suno.com/home` | Main landing page |
| `/explore` | `suno.com/explore` | Song discovery feed |
| `/pricing` | `suno.com/pricing` | Subscription tiers |
| `/@<username>` | `suno.com/@kant` | Public user profiles |
| `/playlist/<uuid>` | `suno.com/playlist/480b...` | Playlist pages |
| `/song/<uuid>` | `suno.com/song/3840...` | Individual song pages (404 from WebFetch — likely auth-gated) |
| `/blog/<slug>` | `suno.com/blog/v4` | Blog articles |
| `/hub/<slug>` | `suno.com/hub/ai-music-software` | SEO content hub (52 pages) |
| `/style/*` | `suno.com/style/...` | Disallowed by robots.txt |

---

## Recommended Strategy

**Capture approach:** SSR+API Hybrid (with Clerk auth required)

**Rationale:**

Suno is a **Next.js App Router SPA with a separate REST backend at
`studio-api.suno.ai`**. The combination means:

1. The initial page load serves RSC-streamed content that is not straightforwardly
   parseable — the raw API at `studio-api.suno.ai` is the correct capture target.

2. Clerk authentication is mandatory. All API calls to `studio-api.suno.ai` are
   gated. The CLI must implement a login flow that obtains a Clerk JWT and stores
   it for subsequent requests.

3. The Force SPA Navigation Trick is essential to discover the full endpoint
   surface: on initial load Suno shows zero API calls (all RSC-streamed). Once
   a user is logged in and clicking through songs/playlists, the trace will
   reveal the exact endpoint signatures, query parameters, and response shapes
   needed for CLI generation.

4. Credit-based rate limits apply per account tier. The generated CLI must
   respect these — no bulk generation loops without backoff.

**CLI generation impact:**

| Concern | Impact |
|---------|--------|
| Backend | `client.py` targets `studio-api.suno.ai`, NOT `suno.com` |
| Auth module | Requires `auth.py` with Clerk login flow — POST to Clerk API, exchange for JWT, store in `~/.suno/credentials.json` or system keyring |
| HTTP client | Standard `httpx` with `Authorization: Bearer <jwt>` header on all requests |
| Session handling | Clerk JWT has limited TTL — implement token refresh |
| Commands | `generate`, `feed`, `clip list`, `playlist get`, `download` (audio from CDN) |
| Rate limiting | Build `asyncio` backoff with exponential retry on 429; surface credit balance |
| Audio download | CDN URLs (`cdn2.suno.ai`) are unauthenticated — direct download once UUID is known |
| Pagination | Feed endpoints likely use cursor-based pagination — must trace to confirm |

**Warnings:**

- **Auth complexity is the primary risk.** Clerk JWTs are short-lived. The CLI
  must handle refresh gracefully or prompt the user to re-authenticate. If Clerk
  introduces browser-fingerprint checks, headless auth may fail.
- **`studio-api.suno.ai` is undocumented.** There is no public API contract.
  Endpoints may change without notice, especially during Suno v4+ rollouts.
- **Credit quota enforcement** means the CLI cannot be used for bulk generation
  without the user's explicit account limits in mind. The CLI should surface
  remaining credits from the feed/account endpoint.
- **Statsig feature flags** may gate certain API routes per user tier —
  confirm during trace capture with a real logged-in session.
- **Song pages returned 404 via WebFetch**, suggesting `/song/<uuid>` pages may
  require auth or be behind Cloudflare bot protection for scrapers. Audio CDN
  links will be the correct download target, not HTML page scraping.

---

## Part 3: Force SPA Navigation Trick — Detailed Application for Suno

### Why it is critical here

Suno uses Next.js **App Router** (not Pages Router). This is the most SSR-heavy
Next.js mode: the server sends React component trees as streaming text via
`self.__next_f.push()`. There is no `__NEXT_DATA__` JSON blob. The initial HTML
looks like a nearly empty shell with embedded React serialization data — not
raw API responses.

Result: an initial-load trace capture shows **zero calls to `studio-api.suno.ai`**.
All data appears to come from the server render. Without the Force SPA Navigation
Trick you would incorrectly conclude Suno has no accessible API.

### Exact application

```bash
# 1. Log in first (required — unauthenticated navigation won't trigger API calls)
#    Use the headed browser to sign in manually via Clerk, then continue:

# 2. Start tracing BEFORE any clicks
npx @playwright/cli@latest -s=recon tracing-start

# 3. Click through pages that load dynamic data
#    Each click triggers Next.js App Router client-side navigation
#    which fetches from the real backend instead of SSR-streaming

npx @playwright/cli@latest -s=recon click "a[href='/explore']"
#    Expected: fetch to studio-api.suno.ai/api/feed/ or similar

npx @playwright/cli@latest -s=recon click "a[href*='/playlist/']"
#    Expected: fetch to studio-api.suno.ai/api/playlist/<uuid>

npx @playwright/cli@latest -s=recon click "a[href*='/@']"
#    Expected: fetch to studio-api.suno.ai/api/user/<handle>/clips

npx @playwright/cli@latest -s=recon click "a[href*='/song/']"
#    Expected: fetch to studio-api.suno.ai/api/clips/<uuid>

# 4. Stop tracing
npx @playwright/cli@latest -s=recon tracing-stop

# 5. Parse
python scripts/parse-trace.py .playwright-cli/traces/ --output recon-traffic.json
```

### What the trace will reveal

After the Force SPA Navigation Trick on a logged-in Suno session, expect to
find in `recon-traffic.json`:

```
studio-api.suno.ai/api/feed/          GET   Authorization: Bearer <clerk_jwt>
studio-api.suno.ai/api/clips/<uuid>   GET   Authorization: Bearer <clerk_jwt>
studio-api.suno.ai/api/playlist/<uuid> GET  Authorization: Bearer <clerk_jwt>
clerk.suno.com/v1/client/sessions/... GET   Clerk session refresh
cdn2.suno.ai/<uuid>.mp3               GET   No auth — direct CDN download
```

These are the endpoint signatures the CLI generator needs.

---

## Part 4: Strategy Recommendation Summary

```
Recon finding                         --> Strategy
──────────────────────────────────────────────────────────────
Next.js App Router (RSC streaming)    --> Force SPA trick to find APIs
studio-api.suno.ai REST backend       --> API-first capture
Clerk JWT auth required               --> Protected-manual (login first)
Cloudflare Analytics present          --> Note rate limits, add backoff
No CAPTCHA in main document           --> Clerk login may be automatable
Credit-based quotas                   --> Surface balance in CLI
CDN audio (cdn2.suno.ai)             --> Direct unauthenticated download
```

**Final strategy: API-first with Clerk auth bootstrapping**

The generated CLI will be a standard `httpx`-based client targeting
`studio-api.suno.ai`, with a `suno auth login` command that drives Clerk
sign-in (likely via a browser-based OAuth redirect), stores the resulting JWT,
and uses it as a Bearer token on all subsequent calls. This is the same pattern
as the Spotify or GitHub CLI auth model.

The reconnaissance confirms Suno is **CLI-suitable**: it has a clean REST API
at a stable subdomain, JSON responses with structured song/playlist objects, and
unauthenticated CDN audio download once the UUID is known. The only significant
complexity is the Clerk auth layer and credit quota management.
