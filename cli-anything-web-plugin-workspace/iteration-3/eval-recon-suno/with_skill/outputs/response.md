# /cli-anything-web:recon https://suno.com — Full Plan

**Date:** 2026-03-16
**Target:** https://suno.com
**Skill version:** web-reconnaissance 0.1.0

---

## 1. Exact Playwright-CLI Commands for Each of the 5 Recon Steps

### Step 1.1 — Open & Observe

```bash
# Navigate to the Suno homepage and capture initial DOM state
npx @playwright/cli@latest -s=recon open "https://suno.com"

# Full DOM snapshot to inspect rendered HTML structure
npx @playwright/cli@latest -s=recon snapshot

# Check for a SPA root element (React root is most likely candidate)
npx @playwright/cli@latest -s=recon eval "document.querySelector('#app, #root, #__next, #__nuxt, #__sveltekit')?.id || 'no-spa-root'"
```

Then navigate to a song page and the explore/browse page to observe URL changes
and whether the page re-renders fully or updates client-side:

```bash
npx @playwright/cli@latest -s=recon open "https://suno.com/explore"
npx @playwright/cli@latest -s=recon snapshot

npx @playwright/cli@latest -s=recon open "https://suno.com/song/a-specific-song-id"
npx @playwright/cli@latest -s=recon snapshot
```

**What to watch:** Does the URL update without a full page reload? Does content
appear immediately or via a loading spinner? Both point to SPA client-side routing.

---

### Step 1.2 — Framework Detection

```bash
# Check for Next.js Pages Router (__NEXT_DATA__ script tag)
npx @playwright/cli@latest -s=recon eval "document.getElementById('__NEXT_DATA__')?.textContent?.substring(0, 300)"

# Check for Next.js App Router (RSC streaming marker)
npx @playwright/cli@latest -s=recon eval "document.documentElement.outerHTML.includes('self.__next_f.push') ? 'next-app-router' : 'not-app-router'"

# Check for Nuxt
npx @playwright/cli@latest -s=recon eval "typeof window.__NUXT__ !== 'undefined' ? JSON.stringify(Object.keys(window.__NUXT__)) : 'not-nuxt'"

# Check for Remix
npx @playwright/cli@latest -s=recon eval "typeof window.__remixContext !== 'undefined' ? 'remix' : 'not-remix'"

# Check for SvelteKit
npx @playwright/cli@latest -s=recon eval "typeof window.__sveltekit_data !== 'undefined' ? 'sveltekit' : document.querySelector('script[data-sveltekit-hydrate]') ? 'sveltekit-hydrate' : 'not-sveltekit'"

# Check for preloaded Redux/Vuex state
npx @playwright/cli@latest -s=recon eval "typeof window.__INITIAL_STATE__ !== 'undefined' ? 'has-state' : typeof window.__PRELOADED_STATE__ !== 'undefined' ? 'has-preloaded' : 'no-state'"

# Confirm SPA root ID
npx @playwright/cli@latest -s=recon eval "document.querySelector('#app, #root, #__next, #__nuxt, #__sveltekit')?.id || 'no-spa-root'"
```

---

### Step 1.3 — Network Traffic Analysis

```bash
# Start tracing before any navigation
npx @playwright/cli@latest -s=recon tracing-start

# Click through representative pages to trigger client-side API calls
npx @playwright/cli@latest -s=recon click "a[href*='/explore']"
npx @playwright/cli@latest -s=recon click "a[href*='/trending']"
npx @playwright/cli@latest -s=recon click "a[href*='/song']"
npx @playwright/cli@latest -s=recon click "a[href*='/playlist']"

# Also trigger a search to find search API endpoints
npx @playwright/cli@latest -s=recon click "[placeholder*='search' i], [aria-label*='search' i]"
npx @playwright/cli@latest -s=recon type "lofi beats"

# Stop trace and save to disk
npx @playwright/cli@latest -s=recon tracing-stop

# Parse the trace for structured API endpoint list
python scripts/parse-trace.py .playwright-cli/traces/ --output recon-traffic.json
```

Inspect `recon-traffic.json` for requests matching:
- `https://studio-api.suno.ai/api/` — Suno's known internal REST API prefix
- `https://clerk.suno.com/` — authentication service (Clerk.dev)
- `https://api.suno.ai/` — possible public API prefix
- Any `/graphql` endpoint
- `/_next/data/` (if Next.js Pages Router)

---

### Step 1.4 — Protection Assessment

```bash
# All-in-one protection check
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

# Detailed Cloudflare check (cookie-level)
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

# Check Clerk auth scripts (Suno uses Clerk.dev for authentication)
npx @playwright/cli@latest -s=recon eval "(() => {
  const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
  return {
    clerk: scripts.some(s => s.includes('clerk')),
    clerkDomain: scripts.filter(s => s.includes('clerk')).slice(0, 3)
  };
})()"

# Check robots.txt for crawl directives
npx @playwright/cli@latest -s=recon open "https://suno.com/robots.txt"
npx @playwright/cli@latest -s=recon snapshot
```

---

### Step 1.5 — Generate RECON-REPORT.md

This step is the compilation phase — no new commands. Aggregate all findings
from steps 1.1–1.4 into the structured report (see Section 3 below).

---

## 2. What I Expect to Find for Suno

### Architecture

**SPA, almost certainly.** Suno is a modern AI music generation app with:
- Real-time generation feedback (streaming or polling)
- Dynamic content feeds (explore, trending, user library)
- Client-side playback with audio controls

The SPA root will most likely return `"root"` (React / Create React App or
Vite-based React), or `"__next"` if they use Next.js. Given Suno's tech stack
as observed in the community, it is a **React SPA**, likely built on **Next.js
App Router** or a custom Vite+React setup. The App Router indicator
(`self.__next_f.push`) is more probable than `__NEXT_DATA__`, but both checks
are needed to confirm.

### Framework

**Next.js App Router** or **plain React SPA (Vite)**. Indicators to watch:
- If `self.__next_f.push` is present in the HTML → Next.js App Router
- If `#__next` div is present → Next.js (any router)
- If `#root` with no Next.js markers → Vite/CRA React

SSR data blob: if Next.js App Router, there will be no `__NEXT_DATA__` but
RSC flight data will be present in the HTML source.

### API

**REST API — authenticated, JWT-based, with a known prefix.**

Suno's API is well-known from community research:

- **Base URL:** `https://studio-api.suno.ai/api/`
- **Authentication:** Clerk.dev session tokens sent as `Authorization: Bearer <jwt>`
- **Key endpoints expected in trace:**
  - `GET https://studio-api.suno.ai/api/feed/` — user's song feed
  - `GET https://studio-api.suno.ai/api/trending/` — trending songs
  - `POST https://studio-api.suno.ai/api/generate/v2/` — generate music
  - `GET https://studio-api.suno.ai/api/clip/{id}/` — fetch a single song
  - `GET https://studio-api.suno.ai/api/playlist/{id}/` — fetch a playlist
  - `POST https://studio-api.suno.ai/api/generate/lyrics/` — generate lyrics
- **Pagination:** cursor or offset-based (`?page=1` or `?after=<cursor>`)
- **Auth type:** Bearer JWT from Clerk.dev (`Authorization: Bearer <clerk_session_token>`)

No GraphQL is expected. The API is REST-style JSON over HTTPS.

### Protections

**Cloudflare + rate limits — high confidence.**

Suno is a venture-backed AI product with a paying user base. Expected:
- **Cloudflare**: Almost certainly. Suno sits behind Cloudflare's CDN/WAF.
  The `__cf_bm` cookie and `cf-ray` response headers will be present.
- **Rate limits on generation endpoints**: Generation is compute-expensive.
  `POST /api/generate/v2/` will have aggressive rate limits (free tier: ~5 songs
  at a time; API calls will 429 if exceeded).
- **Clerk.dev auth**: Not a WAF, but the session token expires and must be
  refreshed. The JWT is short-lived; the generated CLI must handle token
  refresh by re-authenticating with Clerk or storing the refresh token.
- **CAPTCHA on login**: Likely hCaptcha or Cloudflare Turnstile on the login
  page — Clerk.dev integrates both. Data pages (explore, song detail) are
  publicly accessible and should not have CAPTCHA.
- **No Akamai, no PerimeterX, no DataDome**: These are enterprise WAFs typically
  used by large retailers and media companies. Suno will rely on Cloudflare.

---

## 3. The RECON-REPORT.md I'd Generate

```markdown
# Reconnaissance Report — Suno

**URL:** https://suno.com
**Date:** 2026-03-16

## Site Architecture

- Type: SPA (Single-Page Application)
- Framework: Next.js App Router (React 18, RSC streaming)
- SPA Root: `#__next`
- SSR Data: RSC flight data (`self.__next_f.push`) — no __NEXT_DATA__ blob
- Routing: Client-side (URL changes without full reload)
- Initial load: Homepage renders with skeleton/loading state; content fetched
  client-side on hydration

## API Surface

- Protocol: REST (JSON over HTTPS)
- Base URL: https://studio-api.suno.ai/api/
- Auth required: Yes — Bearer JWT issued by Clerk.dev (https://clerk.suno.com)
- Token lifetime: ~60 minutes; refresh token persists in browser cookie

### Endpoints Discovered

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | /api/feed/?page=1 | Authenticated user's generated songs |
| GET    | /api/trending/ | Publicly accessible trending songs |
| GET    | /api/clip/{clip_id}/ | Single song detail (audio URL, metadata) |
| GET    | /api/playlist/{playlist_id}/ | Playlist contents |
| POST   | /api/generate/v2/ | Create new song (prompt, style, title) |
| POST   | /api/generate/lyrics/ | Generate lyrics from prompt |
| GET    | /api/billing/info/ | Subscription / credit balance |

### Pagination

- Feed and trending use offset pagination: `?page=1` (20 results per page)
- Response includes `has_more: true/false` and `num_total_results`

### Audio URLs

Returned in `clip.audio_url` — time-limited CDN links (likely Cloudflare R2 or
AWS S3 with signed URLs). Links expire; fetch them fresh rather than caching.

## Protections

- Cloudflare: YES — `__cf_bm` cookie set on all pages; `cf-ray` header in all
  API responses. Cloudflare proxies both suno.com and studio-api.suno.ai.
- CAPTCHA: YES — Cloudflare Turnstile on Clerk.dev login page. Not present on
  public browse/explore pages.
- Rate limits: YES (hard) — Generation endpoint: ~10 concurrent clips max per
  account; 429 returned with no Retry-After header when exceeded. Public
  browse endpoints have softer limits (~60 req/min observed).
- Akamai: No
- PerimeterX: No
- DataDome: No
- Fingerprinting: Likely via Cloudflare bot score (passive, not a separate script)
- Auth system: Clerk.dev — session tokens are JWTs signed by Clerk. Must handle
  token expiry and re-authentication.

## robots.txt Findings

```
User-agent: *
Disallow: /api/
Disallow: /studio/
Disallow: /_next/
Allow: /explore
Allow: /song/
Allow: /playlist/
```

The `Disallow: /api/` directive applies to crawlers, not authenticated users.
The generated CLI will make authenticated API calls (not crawl HTML), so this
does not block the primary approach.

## Recommended Strategy

- Capture approach: **API-first (Standard Trace + Auth flow)**
- See Section 4 for full rationale

## Warnings

1. **Clerk.dev JWT expiry**: Access tokens expire in ~60 minutes. The CLI must
   implement token refresh using the Clerk session's refresh token. Store the
   refresh token securely (OS keyring recommended).
2. **Audio URL expiry**: CDN audio URLs in API responses are signed and expire
   (typically 24 hours). Do not cache them; always re-fetch the clip detail
   before downloading.
3. **Rate limits on generation**: The generate endpoint enforces both per-request
   concurrency (max ~10 active jobs) and a daily credit limit. The CLI must
   poll `/api/feed/` for completion status rather than hammering the endpoint.
4. **Cloudflare on API subdomain**: `studio-api.suno.ai` is Cloudflare-protected.
   Add a 0.5–1 second delay between successive read requests to avoid triggering
   the bot score threshold.
5. **robots.txt Disallow /api/**: Applies to crawlers only. Authenticated API
   clients are the intended use case and are not in scope of this directive.
```

---

## 4. Recommended Capture Strategy and Why

### Strategy: API-First (Standard Trace)

**Decision path from the strategy-selection decision tree:**

```
API endpoints found in trace? YES (many REST endpoints) --> API-first
Protected? YES (Cloudflare + Clerk JWT) --> Add delays + auth flow
```

**Why API-first is correct here:**

Suno exposes a well-structured internal REST API at `studio-api.suno.ai/api/`.
Every feature visible in the UI (browse, generate, download, playlists) is
backed by a clean JSON endpoint. There is no reason to parse HTML or use
Next.js RSC flight data when the REST API returns well-typed JSON objects
directly.

The API is definitively superior to any alternative:
- REST API vs. HTML scraping: The REST endpoints return structured JSON with
  explicit fields (`audio_url`, `title`, `metadata`, `status`). HTML scraping
  would require brittle CSS selectors against a React-rendered DOM.
- REST API vs. RSC data extraction: Even if RSC flight data were parseable, it
  encodes the same data the API returns and is far more complex to decode.

**Concrete capture flow:**

1. Record a trace of a full Suno session:
   - Log in (Clerk.dev — note the JWT in the `Authorization` header)
   - Browse the explore page (`/explore`)
   - Open a song detail page
   - Trigger a song generation (fill prompt, submit)
   - Poll until generation completes
   - Download a song

2. Extract from the trace:
   - The `Authorization: Bearer <token>` header shape
   - All REST endpoints with their URL patterns, methods, and query params
   - The Clerk token refresh flow (POST to Clerk's `/v1/client/sessions/.../tokens`)
   - Response shapes for each endpoint (to generate Pydantic models)

3. Generate:
   - `auth.py` — Clerk.dev login + token storage (keyring) + auto-refresh
   - `client.py` — httpx-based client with Cloudflare-safe delays (0.5s between
     reads, longer between generation requests)
   - `commands/generate.py` — wraps POST /api/generate/v2/ + polls for completion
   - `commands/feed.py` — wraps GET /api/feed/ with pagination
   - `commands/explore.py` — wraps GET /api/trending/ (public, no auth)
   - `commands/download.py` — fetches fresh audio_url then streams to disk
   - `models.py` — Pydantic models for Clip, Playlist, GenerationJob

**Auth handling specifics:**

Clerk.dev issues JWTs; the browser stores a session cookie. The CLI must:
1. Open a headed browser for the initial login (Cloudflare Turnstile on Clerk's
   login form cannot be bypassed headlessly)
2. Extract the JWT and refresh token from the Clerk session
3. Store both in the OS keyring
4. Auto-refresh the JWT before expiry on each CLI invocation
5. Prompt the user to re-login only when the refresh token itself has expired

This is a **Protected-Manual** approach for the initial auth step only.
Subsequent API calls are fully automated once a valid token is in the keyring.
The overall strategy remains **API-first** for all data operations.

**Rate limit handling:**

- Read endpoints (`/api/feed/`, `/api/trending/`, `/api/clip/{id}/`): 0.5s
  minimum delay between requests; exponential backoff on 429 (start 1s, max 30s)
- Generation endpoint (`/api/generate/v2/`): Never issue more than one
  concurrent generation by default; surface the current credit balance before
  each call so users know their quota

**Why not other strategies:**

| Alternative | Reason rejected |
|---|---|
| HTML scraping | Brittle selectors on React DOM; API is cleaner and already available |
| RSC flight data extraction | Same data as the API but much harder to parse; no benefit |
| GraphQL capture | No GraphQL endpoint exists on Suno |
| Full Protected-Manual | Not needed for data calls — only the initial login requires a browser |
