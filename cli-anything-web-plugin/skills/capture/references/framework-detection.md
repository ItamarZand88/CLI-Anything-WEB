# Framework Detection Reference

Eval commands for identifying SSR frameworks, SPA roots, and client-side state.
Every command uses `npx @playwright/cli@latest -s=<app> eval`.

---

> **WARNING: `eval` Serialization Failures**
>
> `eval` can fail with **"Passed function is not well-serializable!"** on ternary
> operators, comma expressions, and complex logic. This is a known playwright-cli
> limitation. When ANY eval command below fails, wrap it in `run-code`:
>
> ```bash
> # Instead of:
> npx @playwright/cli@latest -s=<app> eval "typeof X !== 'undefined' ? 'yes' : 'no'"
>
> # Use:
> npx @playwright/cli@latest -s=<app> run-code "async page => {
>   return await page.evaluate(() => typeof X !== 'undefined' ? 'yes' : 'no');
> }"
> ```
>
> **Recommended:** Use the all-in-one Site Fingerprint command (below) instead of
> running individual eval commands — it's faster and more reliable.

---

## All-in-One Site Fingerprint (RECOMMENDED)

Instead of running 5+ individual eval commands that may fail, use the
`site-fingerprint.js` script. **Do NOT paste the JS inline** — arrow functions,
optional chaining, and `//` comments break in playwright-cli's single-line parser.
This has been tested and verified.

```bash
# TESTED COMMAND — strips comments, joins lines, runs as single expression
npx @playwright/cli@latest -s=<app> run-code "$(grep -v '^\s*//' ${CLAUDE_PLUGIN_ROOT}/scripts/site-fingerprint.js | tr '\n' ' ')"
```

The script lives at `scripts/site-fingerprint.js` and detects:
- **Framework**: Next.js (Pages/App), Nuxt, Remix, Gatsby, SvelteKit, Google batchexecute, Angular, React
- **Protection**: Cloudflare (cf-ray header + __cf_bm cookie), CAPTCHA, Akamai, DataDome, PerimeterX, AWS WAF, rate limit, Service Worker
- **Auth**: Login button presence, user menu presence, CSRF meta tags
- **Page info**: Title, URL, language, script sources
- **Iframes**: Count, URLs, names (for embedded apps like Google Labs)

**Output interpretation:**
- `framework.googleBatch: true` → Google batchexecute protocol, generate `rpc/` subpackage
- `framework.nextPages: true` → Next.js Pages Router, extract `__NEXT_DATA__`
- `protection.cloudflare: true` → Use `curl_cffi` with `impersonate='chrome'`
- `auth.hasLoginButton && !auth.hasUserMenu` → Login required, ask user before capture
- `auth.hasUserMenu` → Already logged in, proceed directly
- `iframeCount > 0` → App is iframe-embedded, re-run detection inside iframe frame

**If the app is iframe-embedded**, re-run detection inside the iframe:
```bash
npx @playwright/cli@latest -s=<app> run-code "async page => {
  const frame = page.frames()[1];
  if (!frame) return { error: 'no iframe found' };
  return await frame.evaluate(() => ({
    framework: {
      nextPages: !!document.getElementById('__NEXT_DATA__'),
      googleBatch: typeof WIZ_global_data !== 'undefined',
      spaRoot: document.querySelector('#app, #root')?.id || null,
      vite: !!document.querySelector('script[type=\"module\"][src*=\"/@vite\"]') || !!document.querySelector('script[type=\"module\"][src*=\"/src/\"]')
    },
    title: document.title,
    bodyPreview: document.body?.textContent?.substring(0, 300) || ''
  }));
}"
```

---

## 1. Next.js Pages Router
**CLI generation strategy:** Extract `__NEXT_DATA__` props on initial load. For subsequent pages, intercept `/_next/data/<buildId>/` requests — they return the same data as JSON without full page loads.

---

## 2. Next.js App Router
**CLI generation strategy:** Trace client-side navigations to discover the flight data endpoints. These return RSC payloads that can be parsed for the data you need.

---

## 3. Nuxt 2 / Nuxt 3
**CLI generation strategy:** Extract `window.__NUXT__` on initial load for embedded data. Trace navigations to find the underlying API that Nuxt's server routes call.

---

## 4. Remix
**CLI generation strategy:** Remix loaders return data on navigation as JSON when the `_data` search param is present. Capture loader URLs from the trace.

---

## 5. SvelteKit
**CLI generation strategy:** SvelteKit exposes `/__data.json` endpoints for each route. These return structured JSON and are the primary capture target.

---

## 6. Gatsby
**CLI generation strategy:** Gatsby pre-renders pages at build time. Look for `page-data.json` files at `/page-data/<path>/page-data.json` which contain the GraphQL query results.

---

## 7. Google batchexecute
**CLI generation strategy:** These apps use `/_/<ServiceName>/data/batchexecute` POST endpoints with a specific wire format. Generate an `rpc/` subpackage that encodes/decodes batchexecute payloads. See the trace for request IDs (rpcids).

---

## 8. Generic SPA Root
**CLI generation strategy:** Check for `#app` (Vue), `#root` (React), `#__next` (Next.js), `#__nuxt` (Nuxt), `#__sveltekit` (SvelteKit). If none found, likely server-rendered or static HTML.

---

## 9. Redux / Vuex / Preloaded State
**CLI generation strategy:** Extract the state blob on initial load for seed data. Trace navigations to find the API that populates subsequent state updates.

---

## Force SPA Navigation Trick

When the initial page load shows **no API calls** in the trace (all data
embedded via SSR), force client-side navigations to reveal hidden API endpoints:

```bash
# Start tracing before navigating
npx @playwright/cli@latest -s=<app> tracing-start

# Click internal links to trigger client-side data fetches
npx @playwright/cli@latest -s=<app> click <internal-link-1>
npx @playwright/cli@latest -s=<app> click <internal-link-2>
npx @playwright/cli@latest -s=<app> click <internal-link-3>

# Stop tracing
npx @playwright/cli@latest -s=<app> tracing-stop

# Parse the trace for newly discovered endpoints
python ${CLAUDE_PLUGIN_ROOT}/scripts/parse-trace.py .playwright-cli/traces/ --output recon-traffic.json
```

**Why this works:** SSR frameworks embed data on the first load but fetch from
APIs on subsequent client-side navigations. The initial page shows zero API
calls, but clicking links exposes the real data endpoints (e.g.,
`/_next/data/<buildId>/products.json`, `/api/v1/items`).

Always run this trick when the initial trace comes back empty.
