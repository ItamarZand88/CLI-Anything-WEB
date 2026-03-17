# API Discovery Reference

How to find and prioritize APIs during site assessment. APIs produce clean
structured data and are always preferred over HTML scraping for CLI generation.

---

## Why APIs Over Scraping

| Aspect | API | HTML Scraping |
|---|---|---|
| Speed | Fast (JSON only) | Slow (full page render) |
| Reliability | Stable structure | Breaks when HTML changes |
| Data quality | Clean, structured JSON | Messy, requires parsing |
| Bandwidth | Low (data only) | High (images, CSS, JS) |
| CLI maintenance | Low (stable contracts) | High (fragile selectors) |
| CLI suitability | Excellent | Poor — last resort |

**Bottom line:** A CLI built on an API endpoint is 10-100x faster and far more
maintainable than one built on HTML scraping.

---

## API Priority Chain

Check for APIs in this order. Stop at the first match that covers your data needs.

```
Priority  Pattern                                   Notes
────────  ────────────────────────────────────────  ──────────────────────────────
1.        REST API (/api/v1/, /api/v2/)             Direct JSON, fastest path
2.        GraphQL (/graphql)                        Single endpoint, structured queries
3.        Next.js data (/_next/data/BUILD_ID/)      SSR JSON blobs per route
4.        WordPress API (/wp-json/wp/v2/)           If WordPress detected
5.        Shopify API (/products.json)              If Shopify detected
6.        Google batchexecute (/_/Service/data/)    Google apps only
7.        Internal APIs (/_api/, /internal/)        Undocumented, may change
8.        HTML scraping                             LAST RESORT — may not be CLI-suitable
```

---

## Common API URL Patterns

### REST APIs

```
GET  /api/v1/products
GET  /api/v1/products/{id}
GET  /api/v2/search?q={query}&page={n}
POST /api/v1/auth/login
```

Found in the trace as XHR/Fetch requests returning `Content-Type: application/json`.

### GraphQL

```
POST /graphql
POST /api/graphql
POST /gql
```

Request body contains `{ "query": "...", "variables": {...} }`. Response is
always `{ "data": {...} }`.

### Next.js Data Routes

```
GET /_next/data/{buildId}/products.json
GET /_next/data/{buildId}/products/{slug}.json
```

The `buildId` changes on each deployment. Capture it from the trace or from
`__NEXT_DATA__.buildId` in the page source.

### WordPress REST API

```
GET /wp-json/wp/v2/posts?per_page=100&page=1
GET /wp-json/wp/v2/pages
GET /wp-json/wp/v2/categories
GET /wp-json/wc/v3/products  (WooCommerce)
```

### Shopify

```
GET /products.json
GET /collections.json
GET /products/{handle}.json
GET /collections/{handle}/products.json
```

### Google batchexecute

```
POST /_/ServiceName/data/batchexecute
```

Uses a specific wire format with `f.req` form field containing nested arrays.
See the trace for `rpcids` values that identify specific RPC methods.

### Internal / Undocumented

```
GET /_api/items
GET /internal/data
GET /__api/v1/feed
```

These are not officially documented but show up in traces. They may change
without notice — note this risk in the capture findings.

---

## Finding APIs in the Trace

After running Step 1.3 (Network Traffic Analysis) and parsing the trace:

1. **Filter for JSON responses** — any request returning `application/json`
   is likely an API
2. **Look at URL paths** — match against the patterns above
3. **Check request methods** — GET for reads, POST for mutations/GraphQL
4. **Note query parameters** — these reveal pagination, filtering, and sorting
5. **Check response structure** — arrays of objects usually mean list endpoints

---

## Force SPA Navigation Trick

When the initial page load embeds all data via SSR and the trace shows zero
API calls:

```bash
npx @playwright/cli@latest -s=<app> tracing-start
npx @playwright/cli@latest -s=<app> click <internal-link-1>
npx @playwright/cli@latest -s=<app> click <internal-link-2>
npx @playwright/cli@latest -s=<app> click <internal-link-3>
npx @playwright/cli@latest -s=<app> tracing-stop
python scripts/parse-trace.py .playwright-cli/traces/ --output recon-traffic.json
```

Client-side navigations bypass SSR and fetch data from APIs directly. This
reveals endpoints that are invisible on the first load. See
[framework-detection.md](framework-detection.md) for the full explanation.

---

## Identifying Pagination

Look for these patterns in traced API requests:

| Pattern | Example | Type |
|---|---|---|
| Page number | `?page=2&per_page=20` | Offset-based |
| Offset | `?offset=20&limit=20` | Offset-based |
| Cursor | `?cursor=eyJpZCI6MTAwfQ==` | Cursor-based |
| After/Before | `?after=abc123&first=20` | GraphQL relay-style |
| Token | `?pageToken=NEXT_TOKEN` | Token-based |

**How to detect:**
- Make two page navigations and compare the API request parameters
- Check if the response includes `hasMore`, `nextPage`, `cursor`, or `total` fields
- Cursor-based pagination is harder to parallelize but more reliable

---

## Detecting Auth Requirements

Check captured request headers in the trace for:

| Header | Auth Type |
|---|---|
| `Authorization: Bearer <token>` | JWT / OAuth token |
| `Authorization: Basic <base64>` | Basic auth |
| `Cookie: session=<value>` | Session cookie |
| `X-API-Key: <key>` | API key |
| `X-CSRF-Token: <token>` | CSRF protection (needs browser session) |

**If auth is required:**
- The generated CLI needs a login/auth command
- Store tokens/cookies securely (keyring or config file)
- Handle token refresh for OAuth flows
- Note the auth type in capture findings.md

**If no auth headers are present:**
- The API is publicly accessible — simplest case
- Still respect rate limits

---

## API Discovery Checklist

After completing site assessment, you should know:

- [ ] Which API pattern the site uses (REST, GraphQL, SSR data, etc.)
- [ ] The base URL and specific endpoints discovered
- [ ] Pagination mechanism and parameters
- [ ] Whether authentication is required (and what type)
- [ ] Response structure for each endpoint
- [ ] Rate limit behavior (from protection detection)
- [ ] Whether the API covers all the data the user needs
