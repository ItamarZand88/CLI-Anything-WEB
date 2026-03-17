# Strategy Selection Reference

Decision tree and strategy comparison for choosing the right capture approach
after site assessment is complete.

---

## Decision Tree

Use this tree to map recon findings to a capture strategy:

```
Reconnaissance Complete
├── API endpoints found in trace?
│   ├── YES (many) ──> API-first: Standard trace capture
│   │   └── Generates: standard client.py with httpx
│   ├── YES (few, mutations only) ──> Check for SSR data blobs
│   │   ├── __NEXT_DATA__/__NUXT__ found ──> SSR+API hybrid
│   │   └── No blobs ──> Force SPA trick, re-check
│   └── YES (GraphQL) ──> GraphQL capture
│       └── Generates: client.py with query templates
├── No API endpoints found?
│   ├── Google WIZ_global_data ──> batchexecute protocol
│   │   └── Generates: rpc/ subpackage
│   ├── Pure SSR, no client fetches ──> May not be CLI-suitable
│   └── APIs blocked by protection ──> Protected-manual strategy
└── Protection detected?
    ├── Cloudflare ──> Add delays, respect limits
    ├── Rate limits ──> Build backoff into client.py
    └── CAPTCHA ──> Add pause-and-prompt to auth flow
```

---

## Strategy Comparison Table

| Recon Finding | Capture Strategy | CLI Generation Impact |
|---|---|---|
| SPA + clean REST API | Standard trace | Standard client.py with httpx |
| SPA + GraphQL | Standard trace | client.py with query templates |
| SSR + __NEXT_DATA__ | Extract blobs + trace | Models from embedded data |
| SSR + __NUXT__ | Extract blobs + trace | Models from embedded data |
| SvelteKit + __data.json | Trace data routes | client.py targeting /__data.json |
| Remix + loaders | Trace loader URLs | client.py with _data param |
| Gatsby + page-data | Static JSON extraction | client.py targeting page-data.json |
| Google batchexecute | Trace + eval WIZ_data | rpc/ subpackage |
| WordPress + wp-json | Standard trace | client.py targeting /wp-json/ |
| Shopify + products.json | Standard trace | client.py targeting .json endpoints |
| Cloudflare protected | Manual browse | Note rate limits in client |
| WAF protected (Akamai, etc.) | Manual browse + cookies | Cookie persistence in auth flow |
| No API (pure SSR) | Assess viability | May not be CLI-suitable |

---

## Strategy Details

### API-First (Standard Trace)

**When:** Clean REST or internal API endpoints found in trace.

**Capture flow:**
1. Record a trace of the user workflow
2. Extract API endpoints, parameters, and response shapes
3. Generate `client.py` with httpx calls for each endpoint

**Pros:** Fast, reliable, clean data.
**Cons:** None — this is the ideal case.

### GraphQL Capture

**When:** Single `/graphql` endpoint found with structured queries.

**Capture flow:**
1. Record trace to capture query strings and variables
2. Extract unique queries and their variable shapes
3. Generate `client.py` with query templates and variable builders

**Pros:** Single endpoint, flexible queries.
**Cons:** Query complexity can be high; need to handle pagination in variables.

### SSR+API Hybrid

**When:** SSR data blob found (`__NEXT_DATA__`, `__NUXT__`) but client-side
navigations also hit APIs.

**Capture flow:**
1. Extract SSR blob for initial data models
2. Use Force SPA Navigation trick to reveal client-side API endpoints
3. Generate `client.py` that can use either SSR extraction or API calls

**Pros:** Two data sources for resilience.
**Cons:** More complex generation; buildId may change on deploy (Next.js).

### batchexecute (Google Apps)

**When:** `WIZ_global_data` detected; trace shows `batchexecute` POST requests.

**Capture flow:**
1. Trace to capture batchexecute payloads
2. Decode `f.req` wire format to identify rpcids and parameters
3. Generate `rpc/` subpackage with encode/decode functions

**Pros:** Gives full programmatic access to Google app data.
**Cons:** Wire format is complex and undocumented; may break on updates.

### Protected-Manual

**When:** WAF, CAPTCHA, or aggressive Cloudflare blocks automated access.

**Capture flow:**
1. User manually browses the site in the headed browser
2. Trace captures the requests made during manual browsing
3. Generate `client.py` with cookie/session persistence
4. Add `pause-and-prompt` auth step for CAPTCHA flows

**Pros:** Works despite protections.
**Cons:** Requires manual intervention; cookies may expire.

### Not CLI-Suitable

**When:** Pure SSR with no client-side API calls, no data blobs, and no
discoverable endpoints.

**Indicators:**
- Force SPA trick reveals zero API calls
- No `__NEXT_DATA__`, `__NUXT__`, or similar globals
- All data is rendered into HTML with no structured source

**Action:** Report to the user that the site does not expose a programmatic
data layer. Suggest alternatives (official API, data exports, etc.).

---

## Anti-Patterns

Common mistakes to avoid during strategy selection:

### Jumping to implementation without recon

**Wrong:** Start writing a scraper immediately based on assumptions.
**Right:** Run the 5-step recon flow first. Five minutes of recon saves hours
of wrong-approach debugging.

### Scraping HTML when an API exists

**Wrong:** Parse HTML with selectors when `/api/v1/products` returns clean JSON.
**Right:** Always check the API priority chain. APIs are 10-100x faster and
far more maintainable.

### Ignoring sitemaps

**Wrong:** Crawl the site link-by-link to discover URLs.
**Right:** Check `robots.txt` for `Sitemap:` references. Sitemaps give you
every URL instantly.

### Using arbitrary waits instead of proper selectors

**Wrong:** `sleep(5)` and hope the page loaded.
**Right:** Wait for specific elements or network idle. In playwright-cli,
the `open` command waits for load by default.

### No error handling for API calls

**Wrong:** Assume every request succeeds.
**Right:** Build retry logic and backoff into the generated `client.py`.
Handle 429, 403, 500, and timeout errors gracefully.

### Reverse-engineering JS instead of using the feature

**Wrong:** Grep through minified webpack bundles, parse `performance.getEntries()`,
read Next.js build manifests, or decode obfuscated JavaScript to find API endpoints.
This wastes 10-30 minutes and gives unreliable results.

**Right:** Take a screenshot, click the button, fill the form, submit — then check
the trace. If you can see the feature in the UI, you can capture its API call in
under 60 seconds by using it. The browser IS the API documentation.

---

## Quick Reference: Recon to Strategy

```
Found REST API?          --> API-first
Found GraphQL?           --> GraphQL capture
Found SSR blob + API?    --> SSR+API hybrid
Found batchexecute?      --> rpc/ subpackage
Found WordPress?         --> wp-json API-first
Found Shopify?           --> Shopify JSON API-first
Protected site?          --> Protected-manual
No APIs at all?          --> Assess viability, may not be CLI-suitable
```

Always record the chosen strategy and rationale in the capture findings.
