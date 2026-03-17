# Recon Report: Vercel Dashboard CLI Strategy

**Target:** https://vercel.com/dashboard
**Framework:** Next.js (Vercel's own product)
**Date:** 2026-03-16

---

## 1. How to Detect It's Next.js

### Primary Signals (No Auth Required)

**HTML `<head>` markers**

The most reliable indicator is the presence of `<script id="__NEXT_DATA__" type="application/json">` in the page source. This script tag is emitted by every Next.js SSR page and contains the serialized props, page name, build ID, and runtime config. Its presence alone is definitive proof of Next.js.

Additional `<head>` signals:
- `<link rel="preload" as="script" href="/_next/static/chunks/...">` — the `/_next/static/` path prefix is Next.js-exclusive.
- `<meta name="next-head-count">` — injected automatically by the Next.js `<Head>` component.

**Network requests**

- All static assets are served under `/_next/static/` (chunks, CSS, images).
- Client-side page transitions hit `/_next/data/<buildId>/<page>.json` — this is the getServerSideProps / getStaticProps JSON endpoint that Next.js generates automatically.
- The build ID appears in every asset URL; it changes on each deploy.

**HTTP response headers**

- `x-powered-by: Next.js` — present unless explicitly removed (Vercel likely removes this, but the `/_next/` path structure remains).
- `x-nextjs-cache: HIT|MISS|STALE` — Vercel's CDN layer tags cached SSR responses with this header.

**JavaScript globals (browser console)**

```js
window.__NEXT_DATA__          // always present
window.__NEXT_P               // Next.js page registration array
window.next                   // { version, page, ... }
```

Running `Object.keys(window).filter(k => k.startsWith('__NEXT'))` in the console is the fastest single-command confirmation.

**Build ID extraction**

```bash
curl -s https://vercel.com/dashboard | grep -o '"buildId":"[^"]*"'
# Returns something like: "buildId":"abc123xyz"
```

The build ID is embedded in `__NEXT_DATA__` and in every `/_next/static/<buildId>/` asset URL.

---

## 2. How to Extract Data from Server-Side Rendering

### The `__NEXT_DATA__` JSON blob

Every SSR page embeds its full initial data in the `__NEXT_DATA__` script tag. For the Vercel dashboard this will contain the authenticated user's initial state: user profile, team context, feature flags, and the first page of project data.

**Extraction approach:**

```bash
# 1. Fetch the page with a valid session cookie
curl -s https://vercel.com/dashboard \
  -H "Cookie: token=<session_token>" \
  | python3 -c "
import sys, json, re
html = sys.stdin.read()
m = re.search(r'<script id=\"__NEXT_DATA__\"[^>]*>(.*?)</script>', html, re.DOTALL)
data = json.loads(m.group(1))
print(json.dumps(data['props']['pageProps'], indent=2))
"
```

The `data` object has this shape:
```json
{
  "props": {
    "pageProps": { /* the actual page data */ },
    "__N_SSP": true   // true = SSR, false/absent = SSG
  },
  "page": "/dashboard",
  "query": {},
  "buildId": "abc123",
  "runtimeConfig": {},
  "nextExport": false,
  "autoExport": false,
  "isFallback": false
}
```

**What `pageProps` typically contains for an authenticated dashboard:**
- Current user object (id, name, email, avatar)
- Active team/scope
- Billing plan and limits
- Initial project list (first N projects)
- Feature flags / experiments

### SSR data endpoint (`/_next/data/`)

After the initial page load, Next.js fetches subsequent page data via a dedicated JSON endpoint rather than re-fetching the full HTML. This endpoint returns only the `pageProps` without any HTML wrapper.

Pattern:
```
GET /_next/data/<buildId>/<page-path>.json[?query-params]
```

Examples for Vercel dashboard:
```
GET /_next/data/abc123/dashboard.json
GET /_next/data/abc123/[team]/[project].json?team=my-team&project=my-app
```

These endpoints:
- Require the same session cookie as the browser page
- Return pure JSON (no HTML parsing needed)
- Are much faster to poll than full page loads
- Accept the same query parameters as the page route

**Strategy:** Intercept one browser page transition (network tab or proxy), copy the `/_next/data/` URL, then replay it with `curl` using the session cookie. This is the cleanest SSR data extraction path.

### React component state (client-side)

For data that isn't in `pageProps` but is loaded client-side, the React DevTools fiber tree can be walked:

```js
// In browser console — finds the root fiber and extracts all component state
const getRootFiber = () => {
  const root = document.querySelector('#__next');
  const key = Object.keys(root).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
  return root[key];
};
```

This is useful for extracting data from components that fetch after mount (e.g., project deployment lists, analytics numbers) that don't appear in the initial `__NEXT_DATA__`.

---

## 3. How to Discover Hidden API Endpoints

### Approach A: Network tab interception during user flows

The most reliable method. Open Chrome DevTools Network tab filtered to `Fetch/XHR`, then perform each meaningful UI action:
- Log in
- Switch team context
- Open a project
- View deployments
- Trigger a deployment
- Manage environment variables
- View analytics

Each action reveals the underlying API call. For Vercel, expect to find calls to:
- `/api/v1/...` or `/api/v2/...` — REST endpoints
- `/api/graphql` — if Vercel uses GraphQL internally (their public API is REST, but dashboards sometimes use internal GraphQL)
- `/api/teams/<teamId>/projects` — team-scoped project endpoints

**Key headers to capture:** `Authorization`, `x-vercel-token`, CSRF tokens, and any request-specific headers.

### Approach B: Extract from `__NEXT_DATA__` and JS bundles

The build manifest and page manifest expose every route:

```bash
# Fetch the build manifest (lists all JS chunks per page)
curl https://vercel.com/_next/static/abc123/_buildManifest.js

# Fetch the SSR manifest
curl https://vercel.com/_next/static/abc123/_ssgManifest.js
```

Then fetch and search the JS chunks for API URLs:

```bash
# Download all page chunks and grep for /api/ paths
curl -s https://vercel.com/_next/static/chunks/pages/dashboard-<hash>.js \
  | grep -oE '"(/api/[^"]+)"' | sort -u
```

Look for patterns like:
- String literals containing `/api/`
- `fetch(` calls with template literals
- Axios/SWR config objects with `url:` properties
- `useSWR("/api/...")` hooks

### Approach C: `robots.txt`, `sitemap.xml`, and `.well-known` paths

```bash
curl https://vercel.com/robots.txt
curl https://vercel.com/sitemap.xml
curl https://vercel.com/.well-known/openid-configuration  # if OAuth is used
```

These often expose paths that aren't linked in the UI.

### Approach D: Next.js page routing inference

Every file under `pages/` in Next.js becomes a route. By analyzing the `_buildManifest.js`, all client-side routes are enumerable:

```bash
curl -s https://vercel.com/_next/static/abc123/_buildManifest.js \
  | node -e "
const s = require('fs').readFileSync('/dev/stdin','utf8');
// The manifest assigns sorted page list to self.__BUILD_MANIFEST.sortedPages
const m = s.match(/sortedPages\s*:\s*(\[.*?\])/s);
console.log(JSON.parse(m[1]).join('\n'));
"
```

This gives the complete list of Next.js pages (routes), including admin or settings pages not linked from the main navigation.

### Approach E: Source maps (if enabled)

Some production builds ship source maps or leave them accessible:

```bash
# Check if source maps exist for a known chunk
curl -I https://vercel.com/_next/static/chunks/pages/dashboard-<hash>.js.map
# HTTP 200 = source maps exposed; HTTP 404 = not available
```

If available, source maps reconstruct the original TypeScript source, making API endpoint discovery trivial.

### Approach F: OpenAPI / public API documentation cross-reference

Vercel publishes a public REST API at `https://vercel.com/docs/rest-api`. The dashboard is built by the same team, so internal endpoints often follow the same naming conventions. Cross-referencing:
- Public API: `GET /v9/projects` → internal dashboard likely uses a similar or identical path
- Check if dashboard requests go directly to `vercel.com/api/...` or to a separate backend (`api.vercel.com/...`)

---

## 4. Structured Recon Strategy

### Phase 0: Pre-auth reconnaissance (no credentials needed)

| Step | Action | Signal |
|------|--------|--------|
| 0.1 | `curl -s https://vercel.com/dashboard \| grep __NEXT_DATA__` | Confirm Next.js, extract build ID |
| 0.2 | Fetch `/_next/static/<buildId>/_buildManifest.js` | List all page routes |
| 0.3 | Check `robots.txt`, `sitemap.xml` | Discover hidden paths |
| 0.4 | `curl -I https://vercel.com/dashboard` — inspect response headers | Auth redirect behavior, CDN headers |
| 0.5 | Grep JS chunks for `/api/` string literals | Enumerate API surface without auth |

### Phase 1: Auth mechanism analysis

| Step | Action | Signal |
|------|--------|--------|
| 1.1 | Observe login flow in Network tab | Identify token type: cookie-based, Bearer token, or OAuth |
| 1.2 | Inspect `document.cookie` after login | Find session cookie name and domain scope |
| 1.3 | Check `localStorage` / `sessionStorage` | Some Next.js apps store tokens client-side |
| 1.4 | Look for CSRF tokens in `__NEXT_DATA__` | Identify if mutation requests need CSRF headers |
| 1.5 | Check `Authorization` header on first authenticated XHR | Bearer token format and refresh mechanism |

### Phase 2: SSR data extraction

| Step | Action | Signal |
|------|--------|--------|
| 2.1 | Parse `__NEXT_DATA__.props.pageProps` on `/dashboard` | Initial user + project data structure |
| 2.2 | Reproduce `/_next/data/<buildId>/dashboard.json` with curl | Validate SSR endpoint reachability |
| 2.3 | Navigate to each sub-page, capture `/_next/data/` requests | Map page → data schema |
| 2.4 | Extract all `pageProps` schemas across routes | Build data model for CLI output |

### Phase 3: API endpoint discovery

| Step | Action | Signal |
|------|--------|--------|
| 3.1 | Network tab — all XHR/Fetch during full UI walkthrough | Primary API endpoint list |
| 3.2 | Grep all downloaded JS chunks for `/api/` paths | Secondary endpoint list |
| 3.3 | Cross-reference with Vercel public REST API docs | Validate endpoint naming patterns |
| 3.4 | Attempt `/_next/data/` for every discovered page route | Confirm SSR vs CSR data loading per route |
| 3.5 | Check for GraphQL endpoint (`/api/graphql` introspection) | If GraphQL: run introspection query to get full schema |

### Phase 4: CLI implementation plan

Based on the above, the CLI architecture for Vercel dashboard:

**Authentication module**
- Store session token (cookie or Bearer) in `~/.config/vercel-cli/credentials.json`
- Implement token refresh if needed
- Support both personal account and team-scoped requests

**Data fetching strategy (priority order)**
1. `/_next/data/<buildId>/<page>.json` — for pages that use `getServerSideProps` (fast, structured JSON, no HTML parsing)
2. Direct `/api/` endpoints — for mutations and real-time data not in SSR props
3. Full page HTML + `__NEXT_DATA__` parse — fallback for pages that embed data only in SSR HTML

**Build ID management**
- The build ID changes on each Vercel deploy
- Cache the build ID locally; on `404` from a `/_next/data/` request, re-fetch the dashboard HTML to extract the new build ID

**Command surface (inferred from dashboard UI)**
```
vercel-cli projects list
vercel-cli projects get <name>
vercel-cli deployments list <project>
vercel-cli deployments inspect <id>
vercel-cli env list <project> [--environment=production|preview|development]
vercel-cli domains list
vercel-cli logs <deployment-id>
vercel-cli analytics <project>
```

---

## Key Findings Summary

1. **Next.js detection is unambiguous**: `__NEXT_DATA__` script tag and `/_next/static/` asset paths are definitive, framework-level signals that cannot be spoofed or removed without breaking the application.

2. **SSR data is the primary extraction vector**: The `/_next/data/<buildId>/<page>.json` endpoints return structured JSON with the same data the browser sees, require only a valid session cookie, and are far simpler to consume than scraping HTML.

3. **Build ID is the key dependency**: All `/_next/data/` requests embed the build ID in the URL. The CLI must detect and cache the current build ID, and re-fetch it automatically after deploys (detected by `404` responses).

4. **API discovery is layered**: Network tab interception during manual UI walkthrough gives the most complete and reliable endpoint list. JS bundle grepping fills in endpoints that are only triggered by rare UI flows. The `_buildManifest.js` gives the complete page route list for systematic `/_next/data/` enumeration.

5. **Vercel's public REST API is a valuable reference**: Since Vercel builds their own dashboard on their own platform, the internal API endpoints are likely identical to or a superset of the documented public API at `vercel.com/docs/rest-api`. Starting from the public docs and observing deviations in network traffic is an efficient strategy.
