# Framework Detection Reference

Eval commands for identifying SSR frameworks, SPA roots, and client-side state.
Every command uses `npx @playwright/cli@latest -s=<app> eval`.

---

## 1. Next.js Pages Router

```bash
npx @playwright/cli@latest -s=<app> eval "document.getElementById('__NEXT_DATA__')?.textContent?.substring(0, 200)"
```

| Return value | Meaning |
|---|---|
| JSON string (truncated) | Next.js Pages Router with embedded SSR data |
| `null` | Not Pages Router (may still be App Router) |

**CLI generation strategy:** Extract `__NEXT_DATA__` props on initial load. For
subsequent pages, intercept `/_next/data/<buildId>/` requests — they return the
same data as JSON without full page loads.

---

## 2. Next.js App Router

App Router does not embed a single `__NEXT_DATA__` blob. Instead look for:

```bash
# Check for RSC streaming markers in page source
npx @playwright/cli@latest -s=<app> eval "document.documentElement.outerHTML.includes('self.__next_f.push') ? 'next-app-router' : 'not-app-router'"
```

Also verify by checking the trace (Step 1.3) for `_next/data/` fetch requests
during client-side navigation.

**CLI generation strategy:** Trace client-side navigations to discover the
flight data endpoints. These return RSC payloads that can be parsed for the
data you need.

---

## 3. Nuxt 2 / Nuxt 3

```bash
npx @playwright/cli@latest -s=<app> eval "typeof window.__NUXT__ !== 'undefined' ? JSON.stringify(Object.keys(window.__NUXT__)) : 'not-nuxt'"
```

| Return value | Meaning |
|---|---|
| `["state","serverRendered",...]` | Nuxt 2 (Vuex-based state) |
| `["data","state","once",...]` | Nuxt 3 (Pinia / payload-based) |
| `"not-nuxt"` | Not a Nuxt app |

**CLI generation strategy:** Extract `window.__NUXT__` on initial load for
embedded data. Trace navigations to find the underlying API that Nuxt's
server routes call.

---

## 4. Remix

```bash
npx @playwright/cli@latest -s=<app> eval "typeof window.__remixContext !== 'undefined' ? 'remix' : 'not-remix'"
```

| Return value | Meaning |
|---|---|
| `"remix"` | Remix app — loaders provide data via `__remixContext` |
| `"not-remix"` | Not Remix |

**CLI generation strategy:** Remix loaders return data on navigation as JSON
when the `_data` search param is present. Capture loader URLs from the trace.

---

## 5. SvelteKit

```bash
npx @playwright/cli@latest -s=<app> eval "typeof window.__sveltekit_data !== 'undefined' ? 'sveltekit' : document.querySelector('script[data-sveltekit-hydrate]') ? 'sveltekit-hydrate' : 'not-sveltekit'"
```

| Return value | Meaning |
|---|---|
| `"sveltekit"` | SvelteKit with `__sveltekit_data` global |
| `"sveltekit-hydrate"` | SvelteKit using hydration script tags |
| `"not-sveltekit"` | Not SvelteKit |

**CLI generation strategy:** SvelteKit exposes `/__data.json` endpoints for
each route. These return structured JSON and are the primary capture target.

---

## 6. Gatsby

```bash
npx @playwright/cli@latest -s=<app> eval "typeof window.___gatsby !== 'undefined' ? 'gatsby' : 'not-gatsby'"
```

| Return value | Meaning |
|---|---|
| `"gatsby"` | Gatsby site — static generation with GraphQL at build time |
| `"not-gatsby"` | Not Gatsby |

**CLI generation strategy:** Gatsby pre-renders pages at build time. Look for
`page-data.json` files at `/page-data/<path>/page-data.json` which contain
the GraphQL query results.

---

## 7. Google batchexecute

```bash
npx @playwright/cli@latest -s=<app> eval "typeof WIZ_global_data !== 'undefined' ? 'google-batchexecute' : 'not-google'"
```

| Return value | Meaning |
|---|---|
| `"google-batchexecute"` | Google app using batchexecute RPC protocol |
| `"not-google"` | Not a Google batchexecute app |

**CLI generation strategy:** These apps use `/_/<ServiceName>/data/batchexecute`
POST endpoints with a specific wire format. Generate an `rpc/` subpackage that
encodes/decodes batchexecute payloads. See the trace for request IDs (rpcids).

---

## 8. Generic SPA Root

```bash
npx @playwright/cli@latest -s=<app> eval "document.querySelector('#app, #root, #__next, #__nuxt, #__sveltekit')?.id || 'no-spa-root'"
```

| Return value | Meaning |
|---|---|
| `"app"` | Generic Vue or custom SPA |
| `"root"` | React (Create React App or custom) |
| `"__next"` | Next.js (run Next.js-specific checks) |
| `"__nuxt"` | Nuxt (run Nuxt-specific checks) |
| `"__sveltekit"` | SvelteKit (run SvelteKit-specific checks) |
| `"no-spa-root"` | Likely server-rendered or static HTML |

---

## 9. Redux / Vuex / Preloaded State

```bash
npx @playwright/cli@latest -s=<app> eval "typeof window.__INITIAL_STATE__ !== 'undefined' ? 'has-state' : typeof window.__PRELOADED_STATE__ !== 'undefined' ? 'has-preloaded' : 'no-state'"
```

| Return value | Meaning |
|---|---|
| `"has-state"` | Server-injected initial state (common in Vue SSR / Vuex) |
| `"has-preloaded"` | Redux preloaded state (common in React SSR) |
| `"no-state"` | No global state blob found |

**CLI generation strategy:** Extract the state blob on initial load for seed
data. Trace navigations to find the API that populates subsequent state updates.

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
