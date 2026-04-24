# Protection Detection Reference

Anti-bot, WAF, and rate limit detection patterns for site assessment.
All commands use `npx @playwright/cli@latest -s=<app>`.

---

## Service Worker Detection

Service Workers can intercept network requests and make them invisible to
Playwright's tracing. **Always check for Service Workers during assessment:**

```bash
npx @playwright/cli@latest -s=<app> run-code "async page => {
  return await page.evaluate(() => {
    const sw = navigator.serviceWorker;
    return {
      supported: !!sw,
      controller: sw?.controller ? {
        scriptURL: sw.controller.scriptURL,
        state: sw.controller.state
      } : null,
      hasRegistrations: 'getRegistrations' in (sw || {})
    };
  });
}"
```

If `controller` is not null, the site has an active Service Worker that may
intercept network requests. **Impact on capture:**
- Requests intercepted by SW won't appear in traces
- Playwright recommends `service_workers: 'block'` when capturing traffic
- The site fingerprint command (in `framework-detection.md`) should be run first;
  if SW is detected, restart the browser with SW blocking

**Mitigation during capture (if playwright-cli supports context options):**
```bash
# When opening the browser, Service Workers are active by default.
# If SW is detected, note it in assessment.md.
# The generated CLI's auth.py should use service_workers="block" in context options.
```

---

## All-in-One Detection Script

> **Important:** Use `run-code` not `eval` for this check. Multi-line expressions and
> comma-separated CSS selectors break `eval`'s function serialization.

```bash
npx @playwright/cli@latest -s=<app> run-code "async page => { return await page.evaluate(() => { const body = document.body.textContent.toLowerCase(); const html = document.documentElement.outerHTML; const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src); return { cloudflare: body.includes('cloudflare') || html.includes('cf-ray') || html.includes('__cf_bm'), captcha: !!(document.querySelector('.g-recaptcha') || document.querySelector('#px-captcha') || document.querySelector('.h-captcha')), akamai: scripts.some(s => s.includes('akamai')), datadome: scripts.some(s => s.includes('datadome')), perimeterx: scripts.some(s => s.includes('perimeterx') || s.includes('/px/')), rateLimit: html.includes('429') || body.includes('too many requests'), fingerprinting: scripts.some(s => s.includes('fingerprint') || s.includes('fp-')) }; }); }"
```

Interpret the result object — any `true` value means that protection is present.

---

## Anti-Bot Escalation Ladder

When the fingerprint flags any protection, climb the ladder from simplest to
heaviest. Stop at the first tier that reaches HTTP 200 on a real endpoint.

| Tier | Tool | Works for | Proof in this repo |
|---|---|---|---|
| 1 | plain `httpx` | unprotected / permissive sites | hackernews, youtube, gh-trending |
| 2 | `curl_cffi` with `impersonate='chrome'` | Cloudflare basic, most WAFs | reddit, pexels, producthunt, unsplash |
| 3 | `curl_cffi` + browser-captured token cookie | AWS WAF, Akamai / DataDome | booking (aws-waf-token), airbnb (curl_cffi + delays) |
| 4 | `camoufox` (stealth Firefox, headless) | Cloudflare **managed challenge** | chatgpt |
| 5 | Hybrid (`camoufox` for auth + `curl_cffi` for read) | sites that challenge auth but allow read | chatgpt (auth via camoufox, chat via curl_cffi) |

Ladder rule: **never skip a tier**. Start with tier 2 when any protection is
flagged; escalate only if the tier below returns 401/403 or a challenge page.

---

## Cloudflare

### Basic Cloudflare (passes on TLS fingerprint alone)

`curl_cffi` with `impersonate='chrome'` is almost always sufficient:

```python
from curl_cffi import requests as curl_requests

resp = curl_requests.get("https://protected-site.com/", impersonate="chrome")
# Returns 200 — Cloudflare thinks it's a real browser
```

Add `curl_cffi` and `beautifulsoup4` to `setup.py` dependencies (instead of `httpx`).
This approach requires NO auth, NO cookies, NO browser session. It works because
Cloudflare primarily checks the TLS fingerprint, not the cookie jar.

### Cloudflare Managed Challenge ("Just a moment…")

Fingerprint flag: `protection.cloudflareManagedChallenge: true`.

When Cloudflare serves the interstitial page, `curl_cffi` alone fails (returns
the challenge HTML instead of the real page). Use **camoufox** — a stealth
Firefox build that passes the managed challenge headless:

```bash
pip install camoufox
python -m camoufox fetch  # downloads the stealth Firefox binary
```

Hybrid pattern (mirrors chatgpt CLI):

```python
from camoufox.sync_api import Camoufox
from curl_cffi import requests as curl_requests

# 1. Use camoufox only for auth / challenge-gated pages
with Camoufox(headless=True, humanize=True) as browser:
    page = browser.new_page()
    page.goto("https://chatgpt.com/login")
    # ... log in, then harvest cookies ...
    cookies = {c["name"]: c["value"] for c in page.context.cookies()}

# 2. Use curl_cffi for the rest — much faster
resp = curl_requests.get("https://chatgpt.com/backend-api/conversations",
                         cookies=cookies, impersonate="chrome")
```

**Detection heuristic at runtime:** if a response contains `"Just a moment..."` in
the `<title>` or `cf-chl-bypass` in the body, escalate to tier 4 for that endpoint.

### Fallback: browser cookies

If `curl_cffi` gets 403 but the body doesn't contain a managed-challenge marker,
try tier 3: capture `cf_clearance` + `__cf_bm` via `state-save` and pass to
`curl_cffi` alongside `impersonate='chrome'`. Cookies expire — users re-run
`auth login` periodically.

**Protection can appear after launch.** Sites add anti-bot protection over time.
Unsplash added it in March 2026 — a CLI that worked fine with `httpx` suddenly
started getting 401 "Making sure you're not a bot!" responses. When this happens,
switch from `httpx` to `curl_cffi` with `impersonate="chrome131"`. Detection:
HTTP 401/403 response body contains "not a bot", "challenge", or "Cloudflare".

### General Cloudflare rules:
- Add realistic delays between requests (1-3 seconds)
- Respect rate limits strictly — Cloudflare escalates protections on abuse
- Never retry failed requests rapidly — exponential backoff only

---

## AWS WAF (Booking.com pattern)

Fingerprint flag: `protection.awsWaf: true`.

AWS WAF returns a 202 JavaScript-challenge page to raw HTTP clients. The bypass
pattern used by the booking CLI:

1. **GraphQL endpoints** — `curl_cffi` with `impersonate='chrome'` passes the
   WAF cold, no cookies needed. Use this tier first for any JSON API.
2. **SSR HTML pages** — require an `aws-waf-token` cookie obtained via a browser
   session. After `state-save`, pass ONLY the `aws-waf-token` cookie:

   ```python
   # Critical: use ONLY aws-waf-token on SSR requests.
   # The bkng session cookie contains affiliate data that triggers
   # server-side redirects on detail pages.
   cookies = {"aws-waf-token": saved["aws-waf-token"]}
   resp = curl_requests.get(url, cookies=cookies, impersonate="chrome")
   ```

3. **Hotel detail pages** redirect when date/occupancy params are present —
   fetch without them, then parse the response for availability data.

---

## Akamai Bot Manager / DataDome (Airbnb pattern)

Fingerprint flags: `protection.akamai: true` / `protection.datadome: true`.

Akamai's Bot Manager and DataDome inspect JA3/JA4 TLS fingerprints plus header
ordering. `curl_cffi` with `impersonate='chrome'` handles both in most cases.
Additional rules observed on the airbnb CLI (~780 requests in capture):

- **Minimum 1-2s delay between requests** — back-to-back requests trigger
  per-IP challenges within ~30 requests.
- **Impersonate the latest Chrome** (`impersonate='chrome131'`) — older
  fingerprints (`chrome110`) get flagged.
- **Preserve the `_abck` / `bm_sz` / `bm_sv` cookies** from browser capture
  (Akamai) and `datadome` cookie (DataDome). Pass them on every request.
- **Rotate the User-Agent** only if you've already rotated the TLS fingerprint
  to match; mismatched UA+TLS is the strongest bot signal.

If both `curl_cffi` tiers fail, the site is tier-4/5 camoufox territory.

---

## PerimeterX

Fingerprint flag: `protection.perimeterx: true`.

PerimeterX (now HUMAN) often renders a CAPTCHA the first time. Options:

- **Auth flow:** pause-and-prompt — ask the user to solve the CAPTCHA in the
  visible browser, then resume capture.
- **Data pages:** usually also challenged; may not be CLI-suitable without a
  paid/residential IP rotation.

---

## Rate Limit Detection

### HTTP Status and Headers

Rate limits show up in the trace as 429 responses. Check headers:

```bash
# After running a trace (Step 1.3), inspect responses for rate limit signals
npx @playwright/cli@latest -s=<app> run-code "async page => { return await page.evaluate(() => { const body = document.body.textContent.toLowerCase(); return { is429: document.title.includes('429') || body.includes('429'), tooManyRequests: body.includes('too many requests'), retryAfter: body.includes('retry-after'), rateLimitHit: body.includes('rate limit') }; }); }"
```

### Common Rate Limit Headers (found in trace)

| Header | Meaning |
|---|---|
| `429 Too Many Requests` | Hard rate limit hit |
| `Retry-After: <seconds>` | Wait this long before retrying |
| `X-RateLimit-Limit` | Max requests allowed in window |
| `X-RateLimit-Remaining` | Requests left in current window |
| `X-RateLimit-Reset` | Timestamp when window resets |

### Impact on CLI Generation

- Build exponential backoff into `client.py` (start at 1s, max 30s)
- Respect `Retry-After` headers when present
- Default to conservative request rates (1 request/second)
- Log rate limit responses so users know when they hit limits

---

## CAPTCHA Types

### Impact on CLI Generation

- If CAPTCHA is present on login/auth pages: add a `pause-and-prompt` step
  in the auth flow where the user manually solves the CAPTCHA in the browser
- If CAPTCHA gates data pages: the site may not be CLI-suitable without
  manual intervention
- Document the CAPTCHA type in the app's `<APP>.md` so users know what to expect

---

## Summary: What Each Finding Means

| Fingerprint flag | Start at ladder tier | Notes |
|---|---|---|
| `cloudflare: true` | 2 (curl_cffi) | Most common — TLS impersonation alone suffices |
| `cloudflareManagedChallenge: true` | 4 (camoufox) | Headless Firefox required for interstitial |
| `awsWaf: true` | 2 for JSON APIs; 3 for SSR | SSR needs `aws-waf-token` cookie only |
| `akamai: true` | 3 (curl_cffi + delays + cookies) | 1-2s delays mandatory |
| `datadome: true` | 3 | Same pattern as Akamai |
| `perimeterx: true` | Manual CAPTCHA | Pause-and-prompt for auth; data pages often unreachable |
| `captcha: true` | Manual CAPTCHA | Add pause-and-prompt to auth flow |
| `rateLimit: true` | 2 | Build backoff into client, respect Retry-After |
| `serviceWorker: true` | N/A | Restart browser with `service_workers='block'` |
| All `false` | 1 (plain httpx) | Standard capture and generation |

For any detected protection, note it prominently in the app's `<APP>.md` Warnings section and record which ladder tier ended up working.
