# Futbin.com Anti-Bot & Protection Reconnaissance Report

**Target:** https://www.futbin.com
**Date:** 2026-03-16
**Recon Method:** Live browser inspection (Chrome DevTools MCP + WebFetch)
**Scope:** Public player database, anti-bot detection, rate limiting, robots.txt analysis

---

## 1. Cloudflare and WAF Detection

### Cloudflare: CONFIRMED — Moderate Tier

Cloudflare is definitively present and operating at the CDN, WAF, and bot-management layers.

**Evidence collected:**

| Signal | Value | Significance |
|--------|-------|--------------|
| HTTP `Server` header | `cloudflare` | Confirmed on every response |
| `CF-Ray` header | `9dd70185ccca935b-TLV` (example) | Present on all responses; datacenter = TLV (Tel Aviv) |
| `CF-Cache-Status` header | `HIT` / `EXPIRED` / `DYNAMIC` | Cache layer active |
| Cloudflare Beacon script | `https://static.cloudflareinsights.com/beacon.min.js/vcd15cbe77...` | RUM telemetry loaded |
| `window.__cfBeacon` object | `{rayId, version: "2025.9.1", token: "53dbe8b6...", load: "single"}` | Real-time telemetry reporting back to CF |
| Challenge-platform oneshot POST | `POST /cdn-cgi/challenge-platform/h/g/jsd/oneshot/{siteKey}/{token}:{ts}:{secret}/{rayId}` | JavaScript-based bot challenge executed on page load |
| `cdn-cgi/rum` POST | HTTP 204 | Real User Monitoring beacon active |

**Cloudflare protection level:** The site uses Cloudflare's **Bot Management / Challenge Platform** in "managed challenge" mode. The challenge resolves silently in JavaScript (no visible CAPTCHA or interstitial was presented) but a cryptographic proof-of-work token is submitted via the oneshot endpoint on every page load. This is Cloudflare's `BotFight Mode` or `Super Bot Fight Mode` — it runs browser integrity checks silently.

**No `cf_clearance` cookie was issued** during the session, which indicates the challenge was satisfied inline (the browser passed the JS challenge automatically), or the headless browser was not flagged at the WAF level despite being detected at the analytics layer.

**CF Worker infrastructure:** Cloudflare Workers are deployed on the origin. The `html` element carries obfuscated data attributes:
- `data-yndwvdwtdr="https://pavbo.futbin.com"` — internal ads/telemetry worker subdomain
- `data-vyandvhfgw="futbin2"` — worker version identifier

The worker rewrites HTML at the edge (comments visible: `<!--Active rewriter version: fallback-->`).

---

## 2. Rate Limiting Analysis

### Result: No explicit rate limiting observed at this request volume

**Test methodology:** 10 sequential `GET /26/players?page=N` requests fired in rapid succession (< 1.2 seconds total for 10 requests) from within the browser context (same session, cookies included).

**Results:**

| Request # | Status | CF-Cache-Status | Response Time |
|-----------|--------|-----------------|---------------|
| 1–5 | 200 | `HIT` | 26–34ms |
| 6–10 | 200 | `EXPIRED` | 173–288ms |

- No `429 Too Many Requests` response received
- No `Retry-After` header observed
- No `X-RateLimit-Limit` or `X-RateLimit-Remaining` headers present on any response
- Pages 1–5 were served from Cloudflare cache (near-instant); pages 6–10 were cache misses (origin fetched, ~200ms)

**Interpretation:** Futbin aggressively caches player listing pages at the Cloudflare edge. Rate limiting, if it exists, is either:
- Not applied to cached responses (the cache absorbs most load)
- Applied at higher volumes than tested here
- Applied differently per IP reputation score (Cloudflare's bot score)

**Recommendation:** Test at higher sustained volumes (50–200 req/min) from a non-browser context (raw HTTP client) to find the actual rate limit threshold. In-browser requests benefit from session cookies and a legitimate browser fingerprint.

---

## 3. robots.txt Analysis

**URL:** https://www.futbin.com/robots.txt
**Status:** 200 OK, file present and well-structured

### Key Findings

**Privileged crawlers (no restrictions):**
- `Googlebot`, `Googlebot-Image`, `AdsBot-Google`, `Mediapartners-Google` — unrestricted
- `AmazonAdBot` — unrestricted

**General crawlers (Disallow rules):**

| Rule | Scope |
|------|-------|
| `Disallow: /*?*` | All URLs with query strings (blocks paginated/filtered pages) |
| `Disallow: /*?` | All URLs ending with bare `?` |
| `Disallow: /players/*?*` | Player pages with filters/pagination |
| `Disallow: /*/players/*?*` | Version-prefixed player pages with query params |
| `Disallow: /eyeblaster` | Legacy ad directory |
| `Disallow: /addineyeV2.html` | Legacy ad file |
| `Disallow: /*comment/*` | All comment sections |

**Sitemaps declared:**
- `https://www.futbin.com/sitemap_index.xml` — 46 sitemaps covering FC 22–26, player databases (3-part pagination per year), squads, SBCs, evolutions, news
- `https://www.futbin.com/news/sitemap-news.xml` — News-specific sitemap

**Strategic implication:** The robots.txt **explicitly blocks the most useful URLs for a CLI** — specifically `/players?*` (all filtered/paginated player listings). The robots.txt is not technically enforced (it is advisory), but it signals the site owner's intent and may inform Cloudflare's WAF rules. A compliant CLI should respect these; a non-compliant one must expect the risk of blocks.

---

## 4. Additional Bot Detection Layers

Beyond Cloudflare, the site deploys a **multi-layer surveillance stack**:

### 4.1 StatCounter — Active Bot Detection (CRITICAL)
StatCounter (project `9767571`) is embedded and **explicitly flagged this session as a bot**:

```
sc_bot=1&sc_bot_type=headless_chrome_webdriver
```

StatCounter detected the headless Chrome instance via `navigator.webdriver = true`. This telemetry is sent to StatCounter's servers and could be used by Futbin to correlate automated sessions. This is not a blocking mechanism directly, but it feeds intelligence to the site operator.

**The `navigator.webdriver = true` flag is the root cause.** Any scraper using Playwright or Puppeteer without patching this property will be flagged by StatCounter and similar analytics systems.

### 4.2 FullStory Session Recording
- Endpoint: `rs.eu1.fullstory.com/rec/page` (HTTP 202)
- Every user session is fully recorded (mouse movements, clicks, scroll, DOM mutations)
- Automated sessions will produce unnatural interaction patterns visible in FullStory replays

### 4.3 Facebook Pixel + Multi-Platform Tracking
- Facebook tracking pixel active (`_fbp` cookie set)
- Twitter/X pixel active (`_twpid` cookie set)
- HubSpot forms tracking (`hubspotutk` cookie)
- Google Analytics GA4 (`G-46JQHZ1KXP`) with login state tracking (`ep.logged_in=not_logged_in`)
- Optable audience targeting SDK (with JWT passport tokens)
- Cookiebot consent management (UUID: `30afc6db-6adf-42aa-ad81-e096cec4956a`)

### 4.4 Authentication State Tracking
Google Analytics explicitly tracks login state per session. The `ep.logged_in=not_logged_in` parameter means the analytics pipeline distinguishes authenticated vs. unauthenticated users. Certain features (price alerts, squad saving) require login.

### 4.5 Cloudflare Workers Edge Rewriting
HTML is rewritten at the edge by a Cloudflare Worker (`futbin2` version). The worker:
- Injects obfuscated data attributes into the `<html>` element
- Controls which ads API URLs are injected
- Operates a `pavbo.futbin.com` subdomain as the internal worker-to-origin communication channel

---

## 5. Data Architecture for CLI Development

### 5.1 URL Patterns (confirmed working)

| Resource | URL Pattern | Method | Notes |
|----------|-------------|--------|-------|
| Player listing | `/26/players?page=N` | GET | HTML, Cloudflare cached |
| Player detail | `/26/player/{id}/{slug}` | GET | HTML, DYNAMIC (not cached) |
| Chemistry links | `/26/player/chemistry-link-fragment?playerCardId={id}&linkType=perfect&page=N` | GET | HTMX fragment, HTML |
| Comments | `/26/comments/threads?pageType=1&pageId={id}` | GET | HTMX fragment, HTML |
| Price history | `/26/player/{id}/price-history` | GET | Full HTML page |

### 5.2 Data Model (from live player table)

Player row fields extracted from `table.players-table tbody tr`:
- Player name, rating, position (primary + alternates)
- Price (PS4/Xbox/PC), price change %
- FUTBIN Rating, preferred foot, skills, weak foot
- PAC, SHO, PAS, DRI, DEF, PHY (6 stats)
- Popularity, IGS (in-game score), height/body type

### 5.3 Internal API Architecture
- **No dedicated JSON/REST API found** — all data is server-rendered HTML
- **HTMX** is the primary dynamic content framework (fragment-based partial page updates)
- **No exposed API keys** or CSRF tokens in page source
- **Session-based cookies** only (no Bearer tokens)
- No GraphQL endpoint detected

---

## 6. Protection Strategy Assessment

### Current Protection Level: MODERATE

| Protection Layer | Present | Blocking Risk |
|-----------------|---------|---------------|
| Cloudflare CDN | Yes | Low (caching helps, not blocks) |
| Cloudflare Challenge Platform | Yes | Medium (JS challenge, passes in browser) |
| Cloudflare Bot Management | Yes (RUM + telemetry) | Medium–High at scale |
| `navigator.webdriver` detection | Yes (StatCounter) | Low (informational only) |
| FullStory behavioral analysis | Yes | Low–Medium (operator alert) |
| Rate limiting (explicit) | Not observed | Unknown at scale |
| CAPTCHA | No | N/A |
| Login wall for data | No (public) | N/A |
| `robots.txt` enforcement at WAF | Likely | Medium |

### Risk Summary
The site **currently serves data** to an unpatched headless browser without blocking, but:
1. It knows the session is automated (StatCounter)
2. Cloudflare is collecting behavioral telemetry
3. Sustained high-volume scraping will likely trigger Cloudflare's bot score threshold and result in a 403 or JS challenge that the headless browser cannot pass without stealth patching

---

## 7. Strategy if Site is Heavily Protected

If Cloudflare escalates to hard challenges or CAPTCHAs, the recommended approach is:

### Tier 1: Stealth Browser Automation (Preferred)
- Use `playwright-stealth` or `puppeteer-extra-plugin-stealth` to patch `navigator.webdriver`, spoof canvas fingerprint, normalize plugin/language arrays
- Launch Chrome with a persistent profile to inherit cookies across sessions
- Use Playwright's `chromium` with `--disable-blink-features=AutomationControlled` flag
- Add realistic inter-request delays: 2–5 seconds between pages, jitter with `random.uniform(1.5, 4.0)`

### Tier 2: Sitemap-Driven Crawling
- Use the declared sitemaps (`sitemap_index.xml` → 46 sub-sitemaps) to get all canonical player URLs
- These are static, Cloudflare-cached URLs — much lower bot-score risk than paginated `/players?page=N` URLs
- Respect `robots.txt` crawl semantics where possible

### Tier 3: HTMX Fragment Endpoints
- The chemistry-link and comments fragment endpoints (`/26/player/chemistry-link-fragment?playerCardId=X`) are lighter, more cacheable, and less monitored than full page loads
- Player detail pages use `data-id="{playerId}"` attributes — enumerate by player ID rather than slug

### Tier 4: Cache Exploitation
- Pages 1–5 of `/26/players` were `CF-Cache-Status: HIT` — Cloudflare is caching these aggressively
- High-traffic cached pages are served without touching the origin; bot scoring may be softer for cached responses
- Schedule scraping during off-peak hours (European night time, 01:00–06:00 UTC) when cache hit rates are lower but traffic monitoring is reduced

### Tier 5: If All Automated Access is Blocked
- Implement a CAPTCHA-solving service integration (2captcha, CapSolver) as fallback
- Alternatively, explore whether Futbin has an official API or data partnership program
- Check EA Sports' official API (`api.ea.com`) which may provide player data directly

---

## 8. Recon Summary

| Question | Finding |
|----------|---------|
| Is Cloudflare present? | Yes — CDN + Challenge Platform + Workers + RUM |
| Is there an active CAPTCHA? | No |
| Does it block headless browsers? | Not currently, but detects them |
| Are there rate limits? | Not observed at low volume; unknown at scale |
| Does robots.txt block player data URLs? | Yes — `Disallow: /*?*` blocks all query-string URLs |
| Is there a JSON API? | No — HTML-only, HTMX fragments |
| Is login required for player data? | No — public access |
| Primary detection vectors | `navigator.webdriver=true`, FullStory behavioral, CF RUM telemetry |
| Recommended approach | Stealth browser with persistent profile + sitemap-based enumeration |

---

*Report generated via live browser reconnaissance on 2026-03-16. All findings are based on observed network traffic, JavaScript evaluation, and HTTP response analysis during a single session.*
