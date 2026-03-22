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

## Cloudflare

### Impact on CLI Generation

Cloudflare blocks standard HTTP clients (`httpx`, `requests`) because their TLS
fingerprints don't match real browsers. Two strategies:

**Strategy 1: `curl_cffi` with TLS impersonation (preferred)**

Use `curl_cffi` instead of `httpx` — it impersonates Chrome's TLS fingerprint,
which passes Cloudflare without any cookies or browser session:

```python
from curl_cffi import requests as curl_requests

resp = curl_requests.get("https://protected-site.com/", impersonate="chrome")
# Returns 200 — Cloudflare thinks it's a real browser
```

Add `curl_cffi` and `beautifulsoup4` to `setup.py` dependencies (instead of `httpx`).
This approach requires NO auth, NO cookies, NO browser session. It works because
Cloudflare primarily checks the TLS fingerprint, not the cookie jar.

**Strategy 2: Browser cookies (fallback)**

If `curl_cffi` doesn't work (some sites check more than TLS), fall back to:
- Use playwright `state-save` to capture `cf_clearance` + `__cf_bm` cookies
- Pass cookies to `httpx` requests
- Cookies expire — users must re-run `auth login` periodically

**Strategy 1 is strongly preferred** — it's simpler, needs no auth, and doesn't expire.

**Protection can appear after launch.** Sites add anti-bot protection over time.
Unsplash added it in March 2026 — a CLI that worked fine with `httpx` suddenly started
getting 401 "Making sure you're not a bot!" responses. When this happens, switch from
`httpx` to `curl_cffi` with `impersonate="chrome131"`. Detection: HTTP 401/403 response
body contains "not a bot", "challenge", or "Cloudflare" text.

### General Cloudflare rules:
- Add realistic delays between requests (1-3 seconds)
- Respect rate limits strictly — Cloudflare escalates protections on abuse
- Never retry failed requests rapidly — exponential backoff only

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

## WAF Detection

### Impact on CLI Generation

WAFs significantly increase the difficulty of automated access:

| WAF | Severity | Recommended approach |
|---|---|---|
| Akamai Bot Manager | High | Manual browser auth, cookie persistence |
| Imperva / Incapsula | High | May require residential IP + cookie rotation |
| PerimeterX | High | Often triggers CAPTCHA — pause-and-prompt flow |
| DataDome | Medium-High | Fingerprint detection — add delays, rotate sessions |

For any detected WAF, note it prominently in the app's `<APP>.md` Warnings section.

---

## Summary: What Each Finding Means

| Finding | CLI Generation Impact |
|---|---|
| Cloudflare detected | Add delays, note possible challenge pages |
| Rate limits detected | Build backoff into client, default to conservative rates |
| CAPTCHA on auth | Add pause-and-prompt to login flow |
| CAPTCHA on data pages | Site may not be CLI-suitable |
| WAF detected (any) | Flag as protected, may need manual browser session |
| Fingerprinting scripts | Automated access will be harder — note in warnings |
| Clean (no protections) | Standard capture and generation, no special handling |
