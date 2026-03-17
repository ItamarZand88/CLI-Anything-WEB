# Suno.com Reconnaissance Report
**Target**: https://suno.com
**Date**: 2026-03-16
**Purpose**: Pre-capture analysis for CLI tool development

---

## 1. Framework and Architecture Detection

### How to Detect

The fastest approach is a multi-signal read of the raw HTML at `https://suno.com` without executing JavaScript — fetch the page source and scan for known fingerprints:

- **`__NEXT_DATA__` script tag** in the HTML body — presence confirms Next.js
- **`_next/static/chunks/`** paths in `<script src>` attributes — confirms Next.js file layout
- **`data-theme` attributes on `<html>` or `<body>`** — indicates Chakra UI
- **CSS custom property naming conventions** (e.g. `--chakra-colors-*`) — confirms Chakra UI
- **`window.__clerk_*`** or `@clerk/nextjs` in bundle references — confirms Clerk auth
- **`__next` DOM node** — React hydration marker
- **`buildId`** field inside `__NEXT_DATA__` — unique Next.js build identifier

### Confirmed Findings

| Signal | Value |
|--------|-------|
| **Frontend Framework** | Next.js (App Router, RSC) |
| **UI Component Library** | Chakra UI (dark theme, CSS variables) |
| **Styling** | Chakra UI + Tailwind CSS (both present across pages) |
| **Authentication** | Clerk (`@clerk/nextjs` v6.33.0) |
| **Content Management** | DatoCMS (about page assets at `datocms-assets.com`) |
| **Language** | TypeScript/JavaScript (Node.js runtime) |
| **Backend** | Python (ML inference), Node.js (API gateway) |
| **Build ID** | `t3JpA4GdkMBQJ3BoEuSVo` (extracted from `/about`) |
| **Clerk Publishable Key** | `pk_live_YXV0aC5zdW5vLmNvbSQ` |

### Architecture Summary

Suno operates a split-domain architecture:

```
suno.com          → Next.js frontend (App Router, SSG/SSR)
about.suno.com    → Separate Next.js static marketing site (DatoCMS-backed)
studio-api.prod.suno.com  → Core REST API backend (Python/Node)
auth.suno.com     → Clerk authentication domain
clerk.suno.com    → Clerk session management
cdn-o.suno.com    → Media CDN (images, audio assets)
```

**Asset paths**: Fonts and static assets are served from `/static-p/` prefix, not `/_next/static/`, suggesting a custom or proxied CDN setup.

---

## 2. API Endpoint Discovery

### How to Find Them

**Passive (no login required):**
1. Fetch `https://studio-api.prod.suno.com/api/session/` — returns unauthenticated feature flags and config (confirmed publicly accessible, returns JSON)
2. Scan JavaScript bundle files from `https://suno.com/_next/static/chunks/` — search for strings matching `"/api/"`, `"suno.ai"`, `"studio-api"`, `fetch(`, `axios.`
3. Check `https://suno.com/sitemap.xml`, `https://suno.com/hub-sitemap.xml`, `https://suno.com/landing-sitemap.xml` for route enumeration
4. Monitor Cloudflare headers in responses for internal routing hints

**Active (requires authenticated session):**
1. Open Chrome DevTools → Network tab → filter by `studio-api.prod.suno.com` or `XHR`
2. Perform a music generation, browse feed, open a song — capture all requests

### Confirmed Endpoint Map

#### Public / Unauthenticated

| Endpoint | Method | Description |
|----------|--------|-------------|
| `https://studio-api.prod.suno.com/api/session/` | GET | Feature flags, A/B test config, geolocation, user capabilities |

#### Authenticated REST API (base: `https://studio-api.prod.suno.com`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate/v2/` | POST | Generate song from prompt (custom or standard mode) |
| `/api/feed/` | GET | Paginated song feed (`?page=0`) |
| `/api/feed/v2` | GET | Feed v2 with user scoping |
| `/api/clips/get_songs_by_ids` | GET/POST | Batch fetch clip data by ID list |
| `/api/user/user_config/` | GET | User settings, subscription tier, feature access |
| `/api/discover` | GET | Discovery/trending songs |
| `/api/extend_audio` | POST | Extend an existing song clip |
| `/api/generate_stems` | POST | Separate vocal and instrumental tracks |
| `/api/get_aligned_lyrics` | GET | Word-level timestamped lyrics |
| `/api/concat` | POST | Stitch audio extensions into full song |

#### Clerk Authentication (base: `https://clerk.suno.com`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/client` | GET | Retrieve current session state and client object |
| `/v1/client/sessions/{session_id}/tokens` | POST | Refresh/obtain short-lived JWT bearer token |
| `/v1/client/sessions/{session_id}/touch` | POST | Keep session alive (heartbeat) |

### Generation Request Payload

```json
POST https://studio-api.prod.suno.com/api/generate/v2/
Content-Type: application/json
Authorization: Bearer <clerk_jwt_token>

{
  "prompt": "[verse]\nlyrics here",
  "tags": "indie pop upbeat female vocals",
  "title": "My Song",
  "mv": "chirp-v3-5",
  "continue_clip_id": null,
  "continue_at": null,
  "infill_start_s": null,
  "infill_end_s": null
}
```

Response returns an array of clip objects. Audio availability progresses: `queued` → `streaming` → `complete`. Poll `/api/feed/?page=0` or `/api/clips/get_songs_by_ids?song_ids=<id>` at ~5-second intervals to detect completion.

---

## 3. Anti-Bot Protections

### How to Check

- Examine HTTP response headers for `cf-ray`, `cf-cache-status`, `x-frame-options`, `x-content-type-options`
- Look for Cloudflare challenge pages (`cf-challenge`, Turnstile widget injection)
- Check if JS must execute before content is accessible (headless browser detection)
- Test unauthenticated API calls and note 401/403/429 patterns
- Look for CAPTCHA requirements during auth flows

### Confirmed Protections

| Layer | Protection | Details |
|-------|-----------|---------|
| **CDN/WAF** | Cloudflare | Analytics beacon at `static.cloudflareinsights.com`, token `ab1dff532cc64f0da79eb9c4070ee1e7`; CF proxies all traffic |
| **Authentication** | Clerk session JWTs | Short-lived tokens (~60s TTL) require continuous refresh via `/v1/client/sessions/{id}/tokens`; tokens embedded in `Authorization: Bearer` header |
| **CAPTCHA** | Active (post-Nov 2024) | CAPTCHA verification required on certain operations (e.g., account creation, high-volume generation); gcui-art/suno-api uses 2Captcha integration to handle this |
| **Rate Limiting** | Enforced at API level | Generation is quota-controlled per user account; `GET /api/user/user_config/` exposes remaining quota |
| **Geolocation gating** | Feature flags by region | `studio-api.prod.suno.com/api/session/` returns `non_us` property; certain features (e.g., video-to-song) disabled outside US |
| **Brute-force protection** | Minimal on Clerk | Disclosed vulnerability: 100 failed login attempts allowed before account lock (as of security disclosure date) |
| **Bot fingerprinting** | TLS + browser fingerprinting via Cloudflare | Headless browsers may trigger JS challenges on initial page load |
| **A/B / Feature flags** | Statsig integration | Used for gradual feature rollout; `statsig_custom_properties` returned in session endpoint |

### Robots.txt Analysis

```
User-agent: *
Allow: /
Disallow: /profile/*/followers
Disallow: /profile/*/following
Disallow: /style/*
Disallow: /login
```

Sitemaps declared:
- `https://suno.com/sitemap.xml`
- `https://suno.com/hub-sitemap.xml`
- `https://suno.com/landing-sitemap.xml`

The permissive `Allow: /` indicates Suno does not attempt to block crawlers via robots.txt. Real protection is at the infrastructure/API layer.

---

## 4. Recommended Capture Strategy

### Recommended Approach: Authenticated Browser Capture with Token Harvesting

**Rationale**: The API uses short-lived Clerk JWTs (not long-lived API keys). The cleanest capture strategy is to authenticate once in a real browser session, then capture the token refresh mechanism and replicate it programmatically.

### Step-by-Step Plan

#### Phase 1: Static Analysis (No Login)
1. Fetch `https://suno.com` source — extract JS bundle chunk URLs from `<script>` tags
2. Download key bundles from `https://suno.com/_next/static/chunks/` and search for:
   - String literals matching `studio-api`, `/api/`, endpoint path patterns
   - `fetch(`, `axios.`, `XMLHttpRequest` calls with their URL constructions
3. Fetch `https://studio-api.prod.suno.com/api/session/` — document all feature flags
4. Parse all three sitemaps for a complete URL/route map

#### Phase 2: Authenticated Traffic Capture
1. Launch Chrome with `--remote-debugging-port=9222` (debug mode)
2. Log in manually at `https://suno.com/login`
3. Attach Chrome DevTools Protocol (CDP) network interceptor
4. Perform these actions while capturing:
   - Open `/create` → generate a song (custom mode + standard mode)
   - Navigate to feed → scroll (pagination)
   - Open a song detail page
   - Open a playlist / hub page
   - Check subscription info at `/subscribe`
5. Record: URL, method, request headers (especially `Authorization`, `Cookie`), request body, response schema

#### Phase 3: Token Refresh Analysis
1. Observe the Clerk token refresh cycle in the Network tab
2. Identify the interval at which `POST /v1/client/sessions/{id}/tokens` is called
3. Replicate this in the CLI: refresh token before each API call using the stored session cookie

### Authentication Implementation for CLI

```python
# Pattern to implement in CLI
import httpx

CLERK_BASE = "https://clerk.suno.com"
API_BASE = "https://studio-api.prod.suno.com"

# Step 1: Get session from cookies (harvested from browser)
# Store __client cookie from Clerk after browser login

# Step 2: Refresh JWT token
def refresh_token(session_id: str, clerk_cookies: dict) -> str:
    r = httpx.post(
        f"{CLERK_BASE}/v1/client/sessions/{session_id}/tokens",
        cookies=clerk_cookies
    )
    return r.json()["jwt"]

# Step 3: Make authenticated API calls
def generate_song(jwt: str, prompt: str, tags: str, title: str):
    r = httpx.post(
        f"{API_BASE}/api/generate/v2/",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"prompt": prompt, "tags": tags, "title": title, "mv": "chirp-v3-5"}
    )
    return r.json()
```

### Capture Tool Recommendation

| Tool | Use Case |
|------|----------|
| **Chrome DevTools Protocol (CDP)** | Primary capture — catches all XHR/fetch with headers and bodies |
| **mitmproxy** | Secondary — useful for inspecting TLS traffic if CDP is insufficient |
| **Playwright** | Automation layer for authenticated flows; can extract `request` events with full payload |
| **httpx / requests** | Final CLI transport layer after API is mapped |

### Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Token expiry (60s JWT TTL) | Implement automatic refresh before each request |
| CAPTCHA on generation | Start with manual CAPTCHA solve; optionally integrate Turnstile-bypass service |
| Rate limiting on generation | Respect quota endpoint; implement exponential backoff on 429 |
| API schema changes (Suno v5 re-architecture) | Version-lock captures; add schema validation on responses |
| Domain migration (suno.ai → suno.com) | Target `suno.com` and `studio-api.prod.suno.com`; `suno.ai` redirects are legacy |

---

## 5. Summary and Predictions

### Architecture Prediction (High Confidence)

Suno.com is a **Next.js App Router SPA** fronting a **Python-based ML inference backend** exposed through a REST API at `studio-api.prod.suno.com`. Authentication is fully delegated to **Clerk** with short-lived JWT tokens. Cloudflare sits in front of everything as WAF + CDN.

The session/feature-flag endpoint (`/api/session/`) is intentionally public and serves as a capability negotiation layer — the CLI should call this first to understand what the authenticated user can access.

### Key Predictions for CLI Behavior

1. **Song generation is async**: `POST /api/generate/v2/` returns clip IDs immediately; actual audio URL appears after polling the feed (~15–90 seconds depending on queue)
2. **Quota is per-account, not per-IP**: Rate limiting is tied to the authenticated user's subscription tier, not network identity
3. **The `mv` parameter selects model version**: Values like `chirp-v3-5`, `chirp-v4`, and (post-Sept 2025) `chirp-v5` control which generation model is used
4. **Token refresh is mandatory**: JWTs expire in ~60 seconds; any CLI that holds a token for longer than one request cycle must refresh before each call
5. **Audio assets are on a separate CDN**: Final audio files will be served from `cdn-o.suno.com` or a similar asset CDN, not from `studio-api.prod.suno.com`

### CLI Command Surface (Predicted)

```
suno generate --prompt "upbeat pop song about summer" --style "pop female vocals"
suno generate --custom --lyrics "verse\n..." --style "indie rock" --title "My Song"
suno feed --page 0
suno get --id <clip_id>
suno extend --id <clip_id> --at 60
suno stems --id <clip_id>
suno quota
suno auth login
suno auth status
```

---

## References

- [gcui-art/suno-api (GitHub)](https://github.com/gcui-art/suno-api) — Open-source reverse-engineered wrapper
- [suno-security-disclosure (GitHub)](https://github.com/theelderemo/suno-security-disclosure) — API infrastructure vulnerability disclosure
- [Suno API Documentation (unofficial)](https://docs.sunoapi.org/) — Community-maintained endpoint docs
- [cjbrigato Gist](https://gist.github.com/cjbrigato/232e77a3005d4d33a64751bd8182c25a) — Raw API script with endpoint details
- [Himalayas Tech Stack](https://himalayas.app/companies/suno/tech-stack) — Suno confirmed languages
- [aimlapi.com — Suno API Reality](https://aimlapi.com/blog/the-suno-api-reality) — Ecosystem overview
- [Clerk Session Token Docs](https://clerk.com/docs/guides/sessions/session-tokens) — JWT authentication model
