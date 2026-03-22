# SSR Patterns Reference

## Plain HTML (No Framework) — Check for Public API First

Before applying SSR extraction patterns, check if the site has a **separate public API**.
Many traditional HTML sites (Hacker News, Reddit, Wikipedia, Dev.to) have documented
REST APIs that are much easier to use than HTML scraping:

```python
# Quick check: does /api/ return JSON?
resp = httpx.get(f"{BASE_URL}/api/", follow_redirects=True)
if resp.headers.get("content-type", "").startswith("application/json"):
    print("Public API found — skip HTML scraping, use the API directly")
```

If the site has no public API and no framework (no `__NEXT_DATA__`, no SPA root),
use httpx + BeautifulSoup4 to parse HTML tables/lists. See `traffic-patterns.md`
"Plain HTML (No Framework)" for the pattern.

**The SSR patterns below are for JavaScript framework-based SSR only** (Next.js,
Nuxt, Remix, SvelteKit). They do NOT apply to plain HTML sites.

---

## What SSR Means for CLI Generation

Server-Side Rendered (SSR) sites deliver data embedded directly in the HTML response
rather than fetching it via separate API calls. For CLI generation, this means:

- **Data lives in HTML, not in API responses** — the initial page load contains all
  the data needed to render the page, embedded as JSON blobs in script tags or global
  variables.
- **No XHR/fetch on first render** — unlike SPAs that show a loading spinner while
  fetching data, SSR sites arrive fully populated.
- **Hidden API endpoints exist** — SSR frameworks still use internal data routes for
  client-side navigation. These are the real API surface for CLI generation.

## Framework-Specific Data Extraction

### Next.js

**Global data blob:** `__NEXT_DATA__`
```javascript
// Embedded in every page as:
<script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{...}}}</script>
```

**Extract via eval:**
```bash
npx @playwright/cli@latest -s=<app> eval "JSON.stringify(window.__NEXT_DATA__)"
```

**Internal data API:** `/_next/data/<BUILD_ID>/<page>.json`
- The `BUILD_ID` changes on every deployment
- Extract it from `__NEXT_DATA__.buildId`
- These endpoints return the same data as `getServerSideProps` / `getStaticProps`
- Example: `/_next/data/abc123/dashboard.json` returns dashboard page data

### Nuxt

**Global data blob:** `window.__NUXT__`
```javascript
// Embedded as:
<script>window.__NUXT__={data:[...],fetch:{...},state:{...}}</script>
```

**Extract via eval:**
```bash
npx @playwright/cli@latest -s=<app> eval "JSON.stringify(window.__NUXT__)"
```

- `__NUXT__.data` contains page-level data from `asyncData()`
- `__NUXT__.fetch` contains component-level data from `fetch()` hooks
- `__NUXT__.state` contains Vuex/Pinia store state

### Remix

**Global data blob:** `window.__remixContext`
```javascript
// Contains loader data for all matched routes:
window.__remixContext = {
  state: {
    loaderData: {
      "routes/dashboard": { boards: [...], user: {...} },
      "routes/dashboard.$boardId": { board: {...}, items: [...] }
    }
  }
}
```

**Extract via eval:**
```bash
npx @playwright/cli@latest -s=<app> eval "JSON.stringify(window.__remixContext.state.loaderData)"
```

- Each route segment has its own loader data
- Nested routes mean nested data — parent + child loaders both fire

### SvelteKit

**Data endpoints:** `/__data.json` appended to any route

- Every SvelteKit page has a corresponding `/__data.json` endpoint
- Example: `/dashboard` → `/dashboard/__data.json`
- These return the `load()` function data as JSON
- No global variable needed — just fetch the data endpoint directly

```bash
# Check if SvelteKit data endpoints exist:
npx @playwright/cli@latest -s=<app> eval "fetch(location.pathname + '/__data.json').then(r => r.json()).then(d => JSON.stringify(d))"
```

## Force SPA Navigation Trick

SSR sites often don't make API calls on the first page load (data is already in HTML).
But when you navigate client-side (click links after the initial load), the framework
fetches data via its internal API routes. This reveals the hidden API surface.

**Technique:** Open the site, then click through internal links while tracing. The
client-side navigation triggers API calls that weren't visible on the initial SSR load.

```bash
# 1. Start tracing
npx @playwright/cli@latest -s=<app> tracing-start

# 2. Click through internal links to trigger client-side data fetches
npx @playwright/cli@latest -s=<app> click <internal-link-1>
npx @playwright/cli@latest -s=<app> click <internal-link-2>

# 3. Stop tracing — captured all client-side API calls
npx @playwright/cli@latest -s=<app> tracing-stop

# 4. Parse the trace to extract discovered endpoints
python ${CLAUDE_PLUGIN_ROOT}/scripts/parse-trace.py .playwright-cli/traces/ --output recon-traffic.json
```

This trick works because:
- First page load: data is in HTML (SSR) — no network requests
- Subsequent navigation: framework fetches data via internal API (XHR/fetch)
- The trace captures these internal API calls, revealing the data routes

## SSR + API Hybrid Strategy

Most SSR sites are hybrids — they render initial data server-side but use standard
API calls for mutations. The CLI generation strategy should reflect this:

### Read operations (GET/list/search):
- **Primary source:** SSR data blobs (`__NEXT_DATA__`, `__NUXT__`, etc.)
- Use these to understand response models, data shapes, and entity relationships
- The internal data routes (`/_next/data/`, `/__data.json`) serve as read API endpoints

### Mutation operations (create/update/delete):
- **Primary source:** Standard API calls captured during user interactions
- SSR sites still use REST/GraphQL/RPC for mutations
- These appear in the network trace when users submit forms, click buttons, etc.

### Decision framework:
- **Use SSR data for response models** — the embedded JSON defines the data shape
  that the CLI should return
- **Use API calls for mutations** — create/update/delete operations go through
  standard endpoints, not SSR data routes
- **Use internal data routes for read endpoints** — `/_next/data/` and similar
  routes are stable, authenticated, and return clean JSON

## When SSR Extraction Is Viable vs Client-Side Fetches

### Use SSR extraction when:
- The site is a known SSR framework (Next.js, Nuxt, Remix, SvelteKit)
- Data is fully present in the HTML on initial load
- The internal data routes return clean JSON (not HTML fragments)
- You need to understand data models before building the CLI

### Wait for client-side fetches when:
- The site uses SSR for initial shell but loads data via separate API calls
- The SSR blob only contains minimal/skeleton data
- The site is a hybrid that uses SSR for SEO pages but SPA for app pages
- Mutations are needed — these always go through standard API endpoints
- The internal data routes are not accessible (authentication issues, CORS)

### Combined approach (recommended):
1. Extract SSR blobs first to understand data models
2. Use Force SPA Navigation to discover internal API routes
3. Capture mutation endpoints through normal user interaction
4. Build CLI with: SSR-derived models + internal data routes for reads + API for writes

---

## HTML Scraping Pitfalls

These apply to any CLI that parses HTML (SSR or plain):

### Extract ALL visible fields
When scraping a table, extract every column — not just name and price. If the browser
shows version, club, nation, and 6 stat columns, the parser must return all of them.
Empty fields in the `--json` output mean the parser is incomplete, not that the data
doesn't exist. Verify by comparing `--json` output against what the browser shows.

### SSR slug URLs
Many SSR sites require a slug in the URL (`/resource/40/item-name`, not `/resource/40`).
The bare-ID URL may 404. Strategy: search the API first to get the canonical URL/slug,
then scrape the detail page. If search doesn't return the ID, try a placeholder slug
(some sites redirect to the correct one).

### Scraped text has noise
HTML table cells often contain extra text alongside the value you want — percentage
changes, badges, status labels, currency symbols. Never parse `get_text()` directly.
Use regex or string splitting to isolate the target value before type conversion:

```python
# Bad: int(cell.get_text())  # "1,234,567 (+5.2%)" → ValueError
# Good:
raw = cell.get_text(strip=True)
value = int(re.sub(r"[^\d]", "", raw.split("(")[0]))
```
