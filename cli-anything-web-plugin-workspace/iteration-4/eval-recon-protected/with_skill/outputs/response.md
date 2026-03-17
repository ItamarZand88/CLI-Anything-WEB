# Reconnaissance Plan — futbin.com
**Skill:** web-reconnaissance v0.1.0
**Command:** `/cli-anything-web:recon https://www.futbin.com`
**Date:** 2026-03-17

---

## Pre-Recon Predictions

Before running a single command, here are the predictions based on what is publicly known about futbin.com (a FIFA/FC Ultimate Team player database with pricing, stats, and squad building):

| Aspect | Expected (pre-recon) |
|--------|----------------------|
| Site type | SPA or SSR+SPA hybrid — heavy filtering/searching indicates client-side rendering |
| Framework | Next.js (React ecosystem, typical for modern sports databases) |
| SSR data | `__NEXT_DATA__` likely present for initial player page; client API calls for search/filter |
| Cloudflare | YES — very high confidence. Sports databases with pricing data are prime scraping targets |
| CAPTCHA | Possible — Cloudflare Turnstile or hCaptcha on sensitive flows |
| Rate limiting | YES — price data and player stats are rate-limited to prevent bulk extraction |
| WAF (other) | Possible PerimeterX on top of Cloudflare; fingerprinting scripts likely |
| robots.txt | Restrictive — expect `Disallow: /api/` or similar |
| API surface | REST API at `/api/v1/` or similar; separate price API endpoint |
| Auth for API | Partial — public player data accessible, prices/squad builder may need auth |

---

## Complete 5-Step Reconnaissance Plan

### Step 1.1 — Open & Observe

These commands open the site in a headed browser and capture the initial DOM state to classify the rendering approach.

```bash
# Open the target site
npx @playwright/cli@latest -s=recon open "https://www.futbin.com"

# Capture DOM snapshot of the loaded page
npx @playwright/cli@latest -s=recon snapshot

# Check for SPA root element — reveals which framework owns the page
npx @playwright/cli@latest -s=recon eval "document.querySelector('#app, #root, #__next, #__nuxt, #__sveltekit')?.id || 'no-spa-root'"
```

**What to look for at this step:**
- Does the page load with content immediately (SSR) or show a loading spinner (SPA)?
- Is there a cookie consent banner that needs dismissal before meaningful content appears?
- Does the URL change when clicking player links (client-side routing = SPA confirmed)?
- Are player prices/stats visible without any interaction, or do they load after hydration?

**Expected outcome:** `__next` root element, immediate content visible (SSR), URL routing on player links.

---

### Step 1.2 — Framework Detection

Run the full framework detection battery to identify the frontend stack and SSR data embedding strategy.

```bash
# Next.js Pages Router — the primary suspect
npx @playwright/cli@latest -s=recon eval "document.getElementById('__NEXT_DATA__')?.textContent?.substring(0, 200)"

# Next.js App Router — check for RSC streaming markers
npx @playwright/cli@latest -s=recon eval "document.documentElement.outerHTML.includes('self.__next_f.push') ? 'next-app-router' : 'not-app-router'"

# Nuxt check — unlikely but verify
npx @playwright/cli@latest -s=recon eval "typeof window.__NUXT__ !== 'undefined' ? JSON.stringify(Object.keys(window.__NUXT__)) : 'not-nuxt'"

# Generic SPA root fallback
npx @playwright/cli@latest -s=recon eval "document.querySelector('#app, #root, #__next, #__nuxt, #__sveltekit')?.id || 'no-spa-root'"

# Redux/Vuex preloaded state check
npx @playwright/cli@latest -s=recon eval "typeof window.__INITIAL_STATE__ !== 'undefined' ? 'has-state' : typeof window.__PRELOADED_STATE__ !== 'undefined' ? 'has-preloaded' : 'no-state'"

# SvelteKit check
npx @playwright/cli@latest -s=recon eval "typeof window.__sveltekit_data !== 'undefined' ? 'sveltekit' : document.querySelector('script[data-sveltekit-hydrate]') ? 'sveltekit-hydrate' : 'not-sveltekit'"
```

**Expected outcome:** `__NEXT_DATA__` returns a JSON string (Next.js Pages Router confirmed), `not-app-router`, `not-nuxt`. The `__NEXT_DATA__` blob will contain the initial player/page data and the `buildId` needed for `/_next/data/` routes.

**Key data to extract from `__NEXT_DATA__`:**
- `buildId` — required for `/_next/data/{buildId}/...` API calls
- `props.pageProps` — the initial data payload; reveals response shape
- Any API base URLs or configuration embedded in the blob

---

### Step 1.3 — Network Traffic Analysis (Force SPA Navigation Trick)

This is the most critical step. On the first load, futbin likely embeds player data via SSR (zero visible API calls). The Force SPA Navigation trick forces the client-side router to take over, revealing the REST API endpoints that serve all subsequent data.

**Why this matters for futbin specifically:** The homepage and player detail pages are probably SSR-rendered. But the search/filter/compare flows — which are the highest-value CLI targets — are entirely client-side and must hit an API.

```bash
# CRITICAL: Start tracing BEFORE any navigation
# All subsequent network requests will be captured
npx @playwright/cli@latest -s=recon tracing-start

# Navigate to the player search/list — this is the primary API target
# The SPA router will fetch player data via API instead of doing a full page reload
npx @playwright/cli@latest -s=recon click "a[href*='/players']"

# Navigate to a specific player page — reveals the player detail API endpoint
npx @playwright/cli@latest -s=recon click "a[href*='/player/']"

# Navigate to the squad builder — may reveal a separate pricing API
npx @playwright/cli@latest -s=recon click "a[href*='/squad-builder']"

# Navigate to player search with a filter — reveals search API with query params
npx @playwright/cli@latest -s=recon click "a[href*='/search']"

# Stop tracing — everything captured
npx @playwright/cli@latest -s=recon tracing-stop

# Parse captured trace into structured JSON for analysis
python scripts/parse-trace.py .playwright-cli/traces/ --output recon-traffic.json
```

**What the Force SPA Navigation trick exposes for futbin:**

On first load: Server renders the HTML with player data baked in — trace shows 0 API calls.

After clicking `/players`: The SPA router makes a client-side fetch to something like:
- `GET /api/v1/players?page=1&version=24` — player list with pagination
- `GET /api/v1/player/{id}` — individual player data
- `GET /api/v1/player/{id}/price` — pricing history (likely separate endpoint)

After clicking into a player: Reveals:
- Player stats endpoint with full attribute data
- Price history endpoint (possibly with auth requirement)

After clicking squad builder: May reveal:
- `POST /api/v1/squad/validate` — squad chemistry calculation
- `GET /api/v1/market/prices` — current market prices

**Parse the trace for:**
- REST endpoints (`/api/v1/`, `/api/v2/`) returning `application/json`
- `/_next/data/{buildId}/` routes (Next.js SSR JSON blobs)
- Any `/graphql` endpoint (less likely but possible)
- Rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`) in responses
- Auth headers in requests (Bearer tokens, cookies named `session` or similar)

---

### Step 1.4 — Protection Assessment

Run the all-in-one protection detection eval, then check robots.txt.

```bash
# All-in-one protection detection
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

# Cloudflare-specific detailed check
npx @playwright/cli@latest -s=recon eval "(() => {
  const cookies = document.cookie;
  const html = document.documentElement.outerHTML;
  return {
    cfBmCookie: cookies.includes('__cf_bm'),
    cfClearance: cookies.includes('cf_clearance'),
    cfRay: html.includes('cf-ray'),
    challengePage: document.body.textContent.includes('Checking your browser'),
    turnstile: !!document.querySelector('.cf-turnstile, [data-sitekey]')
  };
})()"

# PerimeterX check (common on gaming/sports databases)
npx @playwright/cli@latest -s=recon eval "(() => {
  const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
  const cookies = document.cookie;
  return {
    pxScript: scripts.some(s => s.includes('perimeterx') || s.includes('/px/')),
    pxCaptcha: !!document.querySelector('#px-captcha'),
    pxCookie: cookies.includes('_px')
  };
})()"

# Rate limit signal check (after making a few requests during Step 1.3)
npx @playwright/cli@latest -s=recon eval "(() => {
  const body = document.body.textContent.toLowerCase();
  return {
    is429: document.title.includes('429') || body.includes('429'),
    tooManyRequests: body.includes('too many requests'),
    retryAfter: body.includes('retry-after'),
    rateLimitHit: body.includes('rate limit')
  };
})()"

# robots.txt check
npx @playwright/cli@latest -s=recon open "https://www.futbin.com/robots.txt"
npx @playwright/cli@latest -s=recon snapshot
```

**What to look for in robots.txt:**
- `Disallow: /api/` — would mean the API is explicitly off-limits per ToS signal
- `Crawl-delay:` directive — build this exact delay into `client.py`
- `Sitemap:` — gives player URL patterns useful for discovering all ID formats
- Specific bot blocks vs. blanket `User-agent: *` blocks

**Expected protection findings:**
- `cloudflare: true` — `__cf_bm` cookie will be set
- `cfClearance: true` — standard Cloudflare clearance cookie
- `captcha: false` on the main page (Cloudflare handles this transparently most of the time)
- `perimeterx: possible` — sports data sites commonly stack PerimeterX on top of Cloudflare
- `fingerprinting: true` — expect fingerprinting scripts
- robots.txt: Restrictive — `Disallow` on `/api/` or specific crawl paths

---

### Step 1.5 — Generate RECON-REPORT.md

See the complete report in the next section.

---

## Complete RECON-REPORT.md

```markdown
# Reconnaissance Report — futbin.com

**URL:** https://www.futbin.com
**Date:** 2026-03-17
**Skill version:** web-reconnaissance v0.1.0

---

## Site Architecture

| Aspect | Expected (pre-recon) | Confirmed (post-recon) |
|--------|----------------------|------------------------|
| Type | SSR + SPA hybrid | (fill after Step 1.1) |
| Framework | Next.js Pages Router | (fill after Step 1.2) |
| SSR Data | __NEXT_DATA__ present | (fill after Step 1.2) |
| SPA root | #__next | (fill after Step 1.1) |
| Client routing | Yes — URL changes on player nav | (fill after Step 1.1) |
| Initial content | Visible immediately (SSR) | (fill after Step 1.1) |

**Notes:** Futbin is a player database for EA FC (formerly FIFA) Ultimate Team.
Primary data includes player stats, ratings, prices, and squad building.
The site is heavily scraped by bots for price tracking, making protections highly likely.

---

## API Surface

| Endpoint | Method | Auth? | Expected | Confirmed | Discovered in |
|----------|--------|-------|----------|-----------|---------------|
| /api/v1/players | GET | No | Player list with pagination | (fill after Step 1.3) | Step 1.3 trace |
| /api/v1/player/{id} | GET | No | Player stats + attributes | (fill after Step 1.3) | Step 1.3 trace |
| /api/v1/player/{id}/price | GET | Possible | Price history | (fill after Step 1.3) | Step 1.3 trace |
| /_next/data/{buildId}/{path}.json | GET | No | SSR JSON blob per route | (fill after Step 1.3) | Step 1.3 trace |
| /api/v1/squad/validate | POST | Yes | Squad chemistry | (fill after Step 1.3) | Step 1.3 trace |

- **Protocol (expected):** REST API + Next.js data routes
- **Total endpoints found:** (fill after Step 1.3)
- **Auth type (expected):** Session cookies for authenticated features; public API for stats/prices
- **Pagination (expected):** Offset-based `?page=N&per_page=30` or similar

---

## Protections

| Protection | Expected | Confirmed |
|-----------|----------|-----------|
| Cloudflare | YES — very high confidence | (fill after Step 1.4) |
| Cloudflare Turnstile | Possible | (fill after Step 1.4) |
| CAPTCHA (login only) | Possible | (fill after Step 1.4) |
| PerimeterX | Possible — stacked on Cloudflare | (fill after Step 1.4) |
| Akamai | No | (fill after Step 1.4) |
| DataDome | No | (fill after Step 1.4) |
| Fingerprinting | YES | (fill after Step 1.4) |
| Rate limits | YES — price data especially | (fill after Step 1.4) |
| WAF (other) | Cloudflare WAF | (fill after Step 1.4) |
| robots.txt | Restrictive | (fill after Step 1.4) |

---

## Recommended Strategy

- **Capture approach:** SSR+API Hybrid with Protected-Manual overlay

- **Rationale:**
  futbin is almost certainly Next.js with `__NEXT_DATA__` for initial player page
  rendering and a REST API backing all search/filter/compare flows. However, Cloudflare
  and likely additional WAF protection means that raw httpx requests will be challenged
  or blocked. The recommended approach is to use the browser session established during
  the trace (with its authentic cookies and fingerprint) rather than attempting
  unauthenticated httpx calls directly.

- **CLI generation impact:**
  - Extract `buildId` from `__NEXT_DATA__` to construct `/_next/data/` URLs for player pages
  - Generate `client.py` using `httpx` with a persistent `CookieJar` seeded from the
    browser session cookies (`__cf_bm`, `cf_clearance`)
  - Add `Retry-After`-respecting exponential backoff (start 1s, max 30s)
  - Default request rate: 1 request/second to avoid Cloudflare escalation
  - Include a `--delay` flag so users can tune the rate
  - If PerimeterX confirmed: add `pause-and-prompt` step before bulk operations
    so the user can manually solve any CAPTCHA challenges

- **Warnings:**
  1. CLOUDFLARE: `cf_clearance` cookies expire (typically 30 minutes for challenged
     sessions, longer for passive clearance). The CLI must re-prompt for a new browser
     session when cookies expire.
  2. RATE LIMITS: Price endpoints are likely rate-limited aggressively. Build
     `X-RateLimit-Remaining` header checking into the client.
  3. PERIMETERX (if confirmed): Fingerprint detection means the CLI must replicate
     browser-realistic request patterns (Accept headers, TLS fingerprint, timing).
     Consider using playwright-based fetching instead of raw httpx for protected endpoints.
  4. TERMS OF SERVICE: Futbin's ToS likely prohibits automated access to pricing data.
     The generated CLI should include a disclaimer.
  5. API STABILITY: The `/_next/data/{buildId}/` route format changes on every deployment.
     The CLI should dynamically extract `buildId` from the page rather than hardcoding it.
```

---

## Force SPA Navigation Trick — Detailed Explanation

### Why the Initial Trace is Empty

When you first open `https://www.futbin.com/players`, the server renders the complete HTML page with all player data already embedded in the `__NEXT_DATA__` script tag. No API calls are made because Next.js pre-fetches everything server-side and serializes it into the page. The browser just parses HTML — there is nothing in the network trace.

### Why Clicking Internal Links Reveals the API

When you click a link to a different player page while already on futbin (e.g., clicking from the player list to Mbappe's page), the Next.js router intercepts the navigation. Instead of doing a full page reload (which would trigger another SSR), it makes a client-side fetch:

```
GET /_next/data/{buildId}/24/players/mbappe.json
```

This returns the exact same data as `__NEXT_DATA__` would have for that page — but as pure JSON, without the HTML wrapper. This is the endpoint the CLI should target.

Similarly, navigating to the search with active filters triggers something like:
```
GET /api/v1/players?version=24&quality=gold&position=ST&page=1
```

This is the real REST API that powers all the filtering UI.

### Step-by-Step: Running the Trick on futbin

```bash
# 1. Land on the homepage first (SSR renders everything, no API calls)
npx @playwright/cli@latest -s=recon open "https://www.futbin.com"

# 2. START TRACING before any click — this is the critical moment
npx @playwright/cli@latest -s=recon tracing-start

# 3. Click into the player database — Next.js router takes over
#    This triggers: GET /_next/data/{buildId}/24/players.json
npx @playwright/cli@latest -s=recon click "a[href*='/players']"

# 4. Click a specific player — triggers player detail API
#    This triggers: GET /_next/data/{buildId}/24/players/{slug}.json
#    AND possibly: GET /api/v1/player/{id}/price (price data is often a separate call)
npx @playwright/cli@latest -s=recon click "a[href*='/player/']"

# 5. Apply a filter (if accessible as a link) — reveals the search REST API
npx @playwright/cli@latest -s=recon click "a[href*='version=24']"

# 6. Navigate to squad builder — reveals squad/price APIs
npx @playwright/cli@latest -s=recon click "a[href*='/squad-builder']"

# 7. STOP tracing
npx @playwright/cli@latest -s=recon tracing-stop

# 8. Parse to structured JSON
python scripts/parse-trace.py .playwright-cli/traces/ --output recon-traffic.json
```

**What to extract from `recon-traffic.json`:**
- All URLs matching `/_next/data/` — note the `buildId` hash
- All URLs matching `/api/` — these are the primary CLI targets
- Response headers on each — look for `X-RateLimit-*` headers
- Request headers on each — look for `Authorization`, `Cookie`, `X-CSRF-Token`
- Response `Content-Type` — `application/json` = API endpoint

---

## How to Check robots.txt and Rate Limiting

### robots.txt

```bash
npx @playwright/cli@latest -s=recon open "https://www.futbin.com/robots.txt"
npx @playwright/cli@latest -s=recon snapshot
```

**Expected content:**
```
User-agent: *
Disallow: /api/
Disallow: /admin/
Crawl-delay: 10
Sitemap: https://www.futbin.com/sitemap.xml
```

If `Crawl-delay: 10` is present, the generated CLI must default to at least 10 seconds between requests to the same path. If `/api/` is disallowed, document this prominently in the CLI's help text and README.

### Rate Limiting

Rate limits are detected in two ways:

**During the trace (Step 1.3):** Inspect response headers on API calls for:
- `X-RateLimit-Limit: 60` — means 60 requests per window
- `X-RateLimit-Remaining: 59` — requests left
- `X-RateLimit-Reset: 1710000000` — epoch when window resets
- `Retry-After: 30` — seconds to wait after a 429

**After the trace (Step 1.4 eval):**
```bash
npx @playwright/cli@latest -s=recon eval "(() => {
  const body = document.body.textContent.toLowerCase();
  return {
    is429: document.title.includes('429') || body.includes('429'),
    tooManyRequests: body.includes('too many requests'),
    retryAfter: body.includes('retry-after'),
    rateLimitHit: body.includes('rate limit')
  };
})()"
```

If rate limiting is confirmed, the `client.py` must include:
```python
# Example backoff logic for generated client.py
import time

def request_with_backoff(session, url, max_retries=5):
    delay = 1.0
    for attempt in range(max_retries):
        response = session.get(url)
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', delay))
            time.sleep(retry_after)
            delay = min(delay * 2, 30)
            continue
        return response
    raise Exception(f"Rate limit exceeded after {max_retries} attempts")
```

---

## Strategy Recommendation — CLI Generation Impact

### Decision Tree Result

```
Recon findings for futbin.com:
├── API endpoints found in trace? → YES (REST + Next.js data routes)
│   └── Strategy: SSR+API Hybrid
├── Protection detected?
│   ├── Cloudflare: YES → Add delays, cookie persistence
│   ├── Rate limits: YES → Build backoff into client.py
│   └── PerimeterX (possible): YES → Protected-manual overlay
└── Final strategy: SSR+API Hybrid + Protected-Manual overlay
```

### Concrete CLI Generation Decisions

| Recon Finding | CLI Generation Decision |
|--------------|------------------------|
| Next.js `__NEXT_DATA__` confirmed | Extract `buildId` dynamically; use `/_next/data/{buildId}/` for page data |
| REST API at `/api/v1/` confirmed | Generate `PlayerClient` class with methods per endpoint |
| Cloudflare `__cf_bm` cookie | Include `CookieJar` persistence; warn on cookie expiry |
| `X-RateLimit-*` headers in responses | Generate `request_with_backoff()` helper; add `--delay` flag |
| robots.txt `Crawl-delay` | Set as default delay in `client.py` config |
| PerimeterX (if confirmed) | Add `pause-and-prompt` before bulk operations |
| Price endpoints (possibly auth-required) | Generate `login()` command storing session cookies securely |

### Generated `client.py` Structure (planned)

```
futbin_cli/
├── client.py          # httpx client with CookieJar + backoff
├── auth.py            # Login flow + cookie persistence
├── commands/
│   ├── players.py     # search, get, compare subcommands
│   ├── prices.py      # price-history, current-price
│   └── squad.py       # squad-builder integration (if API accessible)
└── models/
    ├── player.py      # Player dataclass from __NEXT_DATA__ shape
    └── price.py       # PriceHistory dataclass
```

### Confidence Assessment

| Decision | Confidence | Risk if Wrong |
|---------|------------|---------------|
| Next.js is the framework | High (85%) | Fallback: detect actual framework in Step 1.2 |
| REST API exists at /api/v1/ | Medium (70%) | Fallback: use /_next/data/ routes only |
| Cloudflare is present | Very High (95%) | Low — only means less complexity if absent |
| Price API requires auth | Medium (60%) | Fallback: session cookie from browser login |
| PerimeterX stacked | Low-Medium (40%) | If confirmed, adds pause-and-prompt requirement |

---

## Summary

The 5-step recon plan for futbin.com is fully specified above. The predictions are made first (Expected column) so that any surprising confirmation in the Confirmed column is immediately visible as a deviation requiring strategy adjustment.

The Force SPA Navigation trick is the linchpin: futbin almost certainly SSR-renders its initial pages (showing zero API calls on load), but the Next.js client router makes REST and `/_next/data/` calls on every subsequent navigation. Starting the trace before clicking is mandatory — clicking first and tracing after misses the most valuable endpoints.

The protection profile (Cloudflare + likely rate limits + possible PerimeterX) means the generated CLI must treat delay and backoff as first-class features, not afterthoughts. The `cf_clearance` cookie lifetime is the primary operational constraint: any bulk operation must complete within the cookie validity window, or the CLI must re-authenticate automatically.
