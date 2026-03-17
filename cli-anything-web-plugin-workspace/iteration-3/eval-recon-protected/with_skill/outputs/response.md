# Reconnaissance Plan — futbin.com

**Target:** https://www.futbin.com
**Date:** 2026-03-16

---

## 1. Exact Playwright-CLI Commands for Protection Detection

Run these commands in sequence using a `recon` session.

### Step 1.1: Open and observe initial state

```bash
npx @playwright/cli@latest -s=recon open "https://www.futbin.com"
npx @playwright/cli@latest -s=recon snapshot
npx @playwright/cli@latest -s=recon eval "document.querySelector('#app, #root, #__next, #__nuxt, #__sveltekit')?.id || 'no-spa-root'"
```

### Step 1.2: Framework detection

```bash
# Check for Next.js (most likely candidate given futbin's stack)
npx @playwright/cli@latest -s=recon eval "document.getElementById('__NEXT_DATA__')?.textContent?.substring(0, 200)"

# Check for Nuxt
npx @playwright/cli@latest -s=recon eval "typeof window.__NUXT__ !== 'undefined' ? JSON.stringify(Object.keys(window.__NUXT__)) : 'not-nuxt'"
```

### Step 1.3: All-in-one protection detection

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

### Step 1.4: Detailed Cloudflare check

```bash
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
```

### Step 1.5: CAPTCHA type checks

```bash
# reCAPTCHA v2
npx @playwright/cli@latest -s=recon eval "!!document.querySelector('.g-recaptcha, iframe[src*=\"recaptcha\"]') ? 'recaptcha-v2' : 'no-recaptcha-v2'"

# reCAPTCHA v3 (invisible)
npx @playwright/cli@latest -s=recon eval "(() => {
  const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
  return scripts.some(s => s.includes('recaptcha') && s.includes('v3')) ? 'recaptcha-v3' : 'no-recaptcha-v3';
})()"

# hCaptcha
npx @playwright/cli@latest -s=recon eval "!!document.querySelector('.h-captcha, iframe[src*=\"hcaptcha\"]') ? 'hcaptcha' : 'no-hcaptcha'"

# Cloudflare Turnstile
npx @playwright/cli@latest -s=recon eval "!!document.querySelector('.cf-turnstile, iframe[src*=\"challenges.cloudflare.com\"]') ? 'turnstile' : 'no-turnstile'"
```

### Step 1.6: PerimeterX check (futbin is known to use PX)

```bash
npx @playwright/cli@latest -s=recon eval "(() => {
  const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
  const cookies = document.cookie;
  return {
    pxScript: scripts.some(s => s.includes('perimeterx') || s.includes('/px/')),
    pxCaptcha: !!document.querySelector('#px-captcha'),
    pxCookie: cookies.includes('_px')
  };
})()"
```

### Step 1.7: Network trace across representative pages

```bash
npx @playwright/cli@latest -s=recon tracing-start

# Navigate representative futbin pages: player search, player card, club squad
npx @playwright/cli@latest -s=recon click "a[href*='/players']"
npx @playwright/cli@latest -s=recon click "a[href*='/player/']"
npx @playwright/cli@latest -s=recon click "a[href*='/squad-builder']"

npx @playwright/cli@latest -s=recon tracing-stop

# Parse captured traffic
python scripts/parse-trace.py .playwright-cli/traces/ --output recon-traffic.json
```

---

## 2. How to Check robots.txt

```bash
npx @playwright/cli@latest -s=recon open "https://www.futbin.com/robots.txt"
npx @playwright/cli@latest -s=recon snapshot
```

**What to extract from futbin's robots.txt:**

- Any `Disallow` directives on player data endpoints (e.g., `/players`, `/player/`, `/squad-builder`) — generated CLI must respect these
- `Crawl-delay` value — if present, build this exact delay into `client.py` as the base request interval
- `Sitemap:` references — use these for URL discovery rather than crawling; futbin likely has a sitemap covering player pages
- Specific `User-agent:` blocks — check if only certain bots are blocked or all crawlers

**Decision rule:** If `Disallow: /players` or similar data-critical paths appear, document this as a legal/ethical constraint in the RECON-REPORT.md Warnings section and surface it to the user before proceeding.

---

## 3. Rate Limiting Signals to Look For

### In the browser (DOM-level check)

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

### In the network trace (after tracing-stop)

Inspect `recon-traffic.json` for these headers on any API response:

| Signal | What it means for CLI generation |
|---|---|
| HTTP `429 Too Many Requests` | Hard limit reached — set base delay to at least 2s |
| `Retry-After: <N>` header | Respect this exactly; build it into exponential backoff |
| `X-RateLimit-Limit` header | Maximum requests per window — cap CLI throughput below this |
| `X-RateLimit-Remaining` header | Countdown — check before each request in burst scenarios |
| `X-RateLimit-Reset` header | Timestamp-based window reset — use for sleep scheduling |
| Response body containing `"message":"rate limit exceeded"` | API-level enforcement (not just HTTP status) |

### Behavioral signals to watch during manual trace

- **Silent 200 responses with empty data arrays** after several requests — soft blocking pattern common in sports data sites
- **Redirect to a "verify you are human" page** after N rapid navigations — Cloudflare behavioral fingerprinting trigger
- **Increasing response latency** over successive requests — server-side throttling before a hard 429

### futbin-specific expectation

futbin is a high-traffic player database accessed by thousands of users simultaneously. It is highly likely to enforce per-IP rate limits on its player pricing and squad endpoints. Expect limits in the range of 20-60 requests per minute on unauthenticated endpoints, with tighter limits on endpoints that return live FIFA Ultimate Team pricing data.

---

## 4. RECON-REPORT.md

```markdown
# Reconnaissance Report — futbin

**URL:** https://www.futbin.com
**Date:** 2026-03-16

## Site Architecture

- Type: SPA (React-based, likely Next.js given URL structure and SSR patterns)
- Framework: Likely Next.js or custom React — check __NEXT_DATA__ eval result
- SSR Data: Check for __NEXT_DATA__ on player pages (populated by eval in Step 1.2)
- Routing: Client-side (URL changes on navigation without full reload)
- Content: Dynamic pricing data refreshed frequently (live EA FC market data)

## API Surface

- Protocol: REST (internal API highly likely at /api/ or similar path)
- Endpoints to verify from trace:
  - Player data: likely `/api/players`, `/api/player/{id}`
  - Pricing: likely `/api/player/{id}/prices` or inline in player response
  - Search: likely `/api/search?name=...` or `/api/players?search=...`
  - Squad builder: likely `/api/squad` or similar
- Auth required: Public endpoints likely open; squad saving requires account auth
- Note: Endpoints are speculative until trace confirms them

## Protections

- Cloudflare: LIKELY YES — futbin is a well-known high-traffic site that uses
  Cloudflare as its CDN and bot-management layer. Expect __cf_bm cookie and
  cf-ray headers. Challenge pages are possible on headless/datacenter IPs.
- CAPTCHA: POSSIBLE — Cloudflare Turnstile or hCaptcha on certain flows;
  PerimeterX CAPTCHA (#px-captcha) has been reported on futbin by the community.
- Rate limits: LIKELY YES — live pricing data makes futbin a target for
  scrapers; aggressive rate limiting expected on pricing endpoints.
- Other WAF: PerimeterX SUSPECTED — check pxScript and _px cookie in eval.
  If confirmed, severity is HIGH.
- Fingerprinting: LIKELY — scripts performing browser fingerprinting are
  common on sports data sites to detect automated access patterns.

## API Endpoint Candidates (from trace — to be confirmed)

[ Fill in after running tracing-start / tracing-stop and parsing recon-traffic.json ]

- REST endpoints found:
- GraphQL found: Yes / No
- Auth headers observed: Yes / No

## robots.txt Findings

[ Fill in after running robots.txt check ]

- Disallow directives:
- Crawl-delay:
- Sitemap references:

## Recommended Strategy

- Capture approach: Protected-manual (with API-first upgrade path)
- Rationale: Given the near-certain presence of Cloudflare and likely PerimeterX,
  automated headless access will be blocked or challenged. The correct approach is
  to have the user manually browse futbin in a headed browser while tracing is
  active. This allows the trace to capture authentic browser cookies and headers,
  which are then used to construct the generated client.py with persistent session
  support. If the network trace reveals clean REST endpoints, the strategy upgrades
  to API-first with authenticated session headers replayed.
- Warnings:
  1. PerimeterX (if confirmed): HIGH severity. Generated CLI must include a
     pause-and-prompt auth step. Cookies will expire and require periodic renewal.
  2. Cloudflare (if confirmed): Add minimum 1-3 second delays between all requests.
     Do not retry aggressively — Cloudflare escalates protection on repeated failures.
  3. Rate limits on pricing endpoints: Build exponential backoff starting at 1s,
     capped at 30s. Default to 1 request/second for pricing data.
  4. robots.txt: If /players or /player/ are in Disallow, surface this to user
     before proceeding with any CLI generation.
  5. Live pricing data: futbin prices update continuously from EA's market.
     CLIs should treat pricing responses as ephemeral and not cache aggressively.
```

---

## 5. Strategy Recommendation Considering Protections

### Primary Recommendation: Protected-Manual with API-First Upgrade Path

**Reasoning:**

futbin sits at the intersection of two factors that demand a cautious, protection-aware approach:

1. **High-value data target.** futbin serves live FIFA/EA FC player pricing and statistics used for financial decisions in the FUT market. This makes it a prime target for scrapers, and the site operators know it. They will have invested in bot protection proportional to the scraping pressure they face.

2. **Known protection stack.** Community reports and the site's profile strongly suggest Cloudflare (CDN + bot management) and PerimeterX (behavioral fingerprinting). Both are in the HIGH severity tier from the WAF reference table.

**Execution plan:**

| Phase | Action | Tool |
|---|---|---|
| 1 | Run all eval checks above with a headed browser on a residential IP | playwright-cli recon session |
| 2 | If Cloudflare challenge page appears, solve it manually to obtain cf_clearance cookie | Manual browser action |
| 3 | Start tracing with authenticated session cookies present | tracing-start |
| 4 | Manually browse representative pages (player search, player card, pricing tab) | Manual browsing |
| 5 | Stop trace and parse for API endpoints | tracing-stop + parse-trace.py |
| 6 | If clean REST endpoints found: generate API-first client.py with session cookie replay | CLI generation |
| 7 | If APIs are blocked/absent: generate HTML-extraction client with protected-manual session | CLI generation |

**Generated client.py must include:**

- Cookie persistence (`cf_clearance`, `__cf_bm`, `_px` if PerimeterX confirmed) loaded from a user-managed cookie file
- Minimum 2-second delay between all requests (configurable, defaulting to 2s)
- Exponential backoff on 429 and 403 responses: start 1s, multiply by 2, cap at 30s
- Respect `Retry-After` header when present — do not override with fixed sleep
- User-agent string matching a real Chrome browser to reduce fingerprinting signals
- Logging of rate limit events so users know when they are approaching limits

**If PerimeterX is confirmed:**

Add a `pause-and-prompt` step at the start of every CLI session:

```
[futbin-cli] Session requires browser verification.
Open https://www.futbin.com in Chrome, complete any challenges,
then export your cookies to cookies.json and press Enter to continue.
```

**Fallback: Not CLI-suitable**

If after protected-manual trace the pricing and player endpoints return empty data or redirect to challenge pages even with valid cookies, the site should be flagged as not reliably CLI-suitable in its current configuration. In that case, recommend the official EA FC API or community-maintained datasets (FUTWIZ, cached player databases) as alternatives.
