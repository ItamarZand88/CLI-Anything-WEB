# Protection Detection Reference

Anti-bot, WAF, and rate limit detection patterns for site assessment.
All commands use `npx @playwright/cli@latest -s=<app>`.

---

## All-in-One Detection Script

Run this single eval to check for all common protections at once:

```bash
npx @playwright/cli@latest -s=<app> eval "(() => {
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

Interpret the result object — any `true` value means that protection is present.

---

## Cloudflare

### Detection Indicators

- **cf-ray header** in response headers (visible in trace)
- **__cf_bm cookie** set in the browser
- **Challenge page** with "Checking your browser before accessing..." text
- **Turnstile widget** (Cloudflare's own CAPTCHA replacement)

### Detailed Check

```bash
npx @playwright/cli@latest -s=<app> eval "(() => {
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

### Impact on CLI Generation

- Add realistic delays between requests (1-3 seconds)
- Respect rate limits strictly — Cloudflare escalates protections on abuse
- If challenge pages appear, the generated CLI must note that manual browser
  auth may be required for the first session
- Consider building cookie persistence into the auth flow

---

## Rate Limit Detection

### HTTP Status and Headers

Rate limits show up in the trace as 429 responses. Check headers:

```bash
# After running a trace (Step 1.3), inspect responses for rate limit signals
npx @playwright/cli@latest -s=<app> eval "(() => {
  const body = document.body.textContent.toLowerCase();
  return {
    is429: document.title.includes('429') || body.includes('429'),
    tooManyRequests: body.includes('too many requests'),
    retryAfter: body.includes('retry-after'),
    rateLimitHit: body.includes('rate limit')
  };
})()"
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

### reCAPTCHA v2 (Checkbox)

```bash
npx @playwright/cli@latest -s=<app> eval "!!document.querySelector('.g-recaptcha, iframe[src*=\"recaptcha\"]') ? 'recaptcha-v2' : 'no-recaptcha-v2'"
```

Visible checkbox challenge. Blocks automated flows entirely.

### reCAPTCHA v3 (Invisible)

```bash
npx @playwright/cli@latest -s=<app> eval "(() => {
  const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
  return scripts.some(s => s.includes('recaptcha') && s.includes('v3')) ? 'recaptcha-v3' : 'no-recaptcha-v3';
})()"
```

Invisible scoring — may silently block requests that look automated.

### hCaptcha

```bash
npx @playwright/cli@latest -s=<app> eval "!!document.querySelector('.h-captcha, iframe[src*=\"hcaptcha\"]') ? 'hcaptcha' : 'no-hcaptcha'"
```

Similar to reCAPTCHA v2 but used by Cloudflare and others.

### Cloudflare Turnstile

```bash
npx @playwright/cli@latest -s=<app> eval "!!document.querySelector('.cf-turnstile, iframe[src*=\"challenges.cloudflare.com\"]') ? 'turnstile' : 'no-turnstile'"
```

Cloudflare's managed challenge — less intrusive but still blocks bots.

### Impact on CLI Generation

- If CAPTCHA is present on login/auth pages: add a `pause-and-prompt` step
  in the auth flow where the user manually solves the CAPTCHA in the browser
- If CAPTCHA gates data pages: the site may not be CLI-suitable without
  manual intervention
- Document the CAPTCHA type in the app's `<APP>.md` so users know what to expect

---

## WAF Detection

### Akamai Bot Manager

```bash
npx @playwright/cli@latest -s=<app> eval "(() => {
  const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
  const cookies = document.cookie;
  return {
    akamaiScript: scripts.some(s => s.includes('akamai') || s.includes('akam')),
    akamaiCookie: cookies.includes('_abck') || cookies.includes('ak_bmsc'),
    sensorData: scripts.some(s => s.includes('sec_cpt'))
  };
})()"
```

### Imperva / Incapsula

```bash
npx @playwright/cli@latest -s=<app> eval "(() => {
  const cookies = document.cookie;
  const html = document.documentElement.outerHTML;
  return {
    incapCookie: cookies.includes('incap_ses') || cookies.includes('visid_incap'),
    impervaScript: html.includes('imperva') || html.includes('incapsula')
  };
})()"
```

### PerimeterX

```bash
npx @playwright/cli@latest -s=<app> eval "(() => {
  const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
  const cookies = document.cookie;
  return {
    pxScript: scripts.some(s => s.includes('perimeterx') || s.includes('/px/')),
    pxCaptcha: !!document.querySelector('#px-captcha'),
    pxCookie: cookies.includes('_px')
  };
})()"
```

### DataDome

```bash
npx @playwright/cli@latest -s=<app> eval "(() => {
  const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
  const cookies = document.cookie;
  return {
    datadomeScript: scripts.some(s => s.includes('datadome')),
    datadomeCookie: cookies.includes('datadome')
  };
})()"
```

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

## robots.txt Check

Always check robots.txt for crawl directives and sitemap references:

```bash
npx @playwright/cli@latest -s=<app> open "https://target-site.com/robots.txt"
npx @playwright/cli@latest -s=<app> snapshot
```

**What to look for:**

- `Disallow` directives — respect these in generated CLIs
- `Crawl-delay` — build this delay into the client
- `Sitemap:` references — useful for URL discovery in API discovery phase
- Specific bot blocks (`User-agent: *` vs. targeted blocks)

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
