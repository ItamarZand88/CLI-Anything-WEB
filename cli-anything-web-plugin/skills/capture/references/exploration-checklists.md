# Exploration Checklists

Concrete targets for each site profile. Used during Step 3 (full capture) to
exercise enough of the API surface that `validate-capture.py` passes.

> **Pacing:** leave **1–2 seconds** between clicks/form submits on any site
> flagged with `cloudflare`, `akamai`, `datadome`, `awsWaf`, or `rateLimit`.
> Faster exploration triggers per-IP challenges within ~30 requests.

> **Minimum bar (enforced by validate-capture.py):**
> `≥ 15 entries`, `≥ 3 distinct URL paths`, protocol ≠ `unknown`, `≥ 1 WRITE op`
> (unless `--read-only`), `< 50%` error rate.

---

## Auth + CRUD

**Target:** ≥ 25 requests, ≥ 3 WRITE ops, ≥ 3 distinct resources touched.

For EACH resource (post / file / item / etc.) visible in the UI:

- [ ] **List** — navigate to the list view
- [ ] **Read detail** — open one item; load detail page
- [ ] **Paginate** — scroll or click page 2 (exercises cursor / page param)
- [ ] **Create** — fill the form, submit (capture the POST body!)
- [ ] **Update** — edit an existing item, save (PUT/PATCH)
- [ ] **Delete** — remove a test item (DELETE)

Plus once per app:

- [ ] **Search** — run ≥ 2 distinct search queries (surfaces search endpoint)
- [ ] **Settings / profile** — open settings page (user-info endpoints)
- [ ] **Export or download** if the feature exists

---

## Auth + Generation

**Target:** ≥ 20 requests, ≥ 2 WRITE ops, at least one complete generation cycle.

- [ ] **Project list** — navigate to the dashboard / project list
- [ ] **Open existing project** — view the editor / canvas
- [ ] **Generate new content** — enter prompt, click generate, **WAIT for completion** (async!)
- [ ] **Poll** — let the client poll for status; capture ≥ 3 poll cycles
- [ ] **Iterate** — modify parameters, re-generate (exercises re-run endpoint)
- [ ] **Export / download** — save the generated artifact
- [ ] **Delete** — remove a test project
- [ ] **Settings** — check model selection / preferences

**Async gotcha:** after clicking generate, wait at least 15 s before the next
action or the polling loop won't appear in the trace.

---

## Auth + Read-only

**Target:** ≥ 15 requests, all GET; ≥ 2 search queries; ≥ 3 detail pages.

- [ ] **Main feed** — navigate to primary content (dashboard / home)
- [ ] **Search** — run ≥ 2 different queries (exercises query/filter endpoint)
- [ ] **Detail pages** — open ≥ 3 different items
- [ ] **Pagination** — scroll or click page 2
- [ ] **Filters** — apply ≥ 1 non-default filter
- [ ] **Export** — if available

Run with `validate-capture.py --read-only` — the WRITE-op check is skipped.

---

## No-auth + CRUD

Same targets as **Auth + CRUD** above; just skip auth-saving steps.
Some sites (e.g., Dev.to) accept optional API-key auth — if so, capture once
without auth and once with auth to see how responses differ.

---

## No-auth + Read-only

**Target:** ≥ 15 GET requests, ≥ 3 distinct URL paths.

- [ ] **Homepage / landing** — capture initial data + hydration calls
- [ ] **Search** — try ≥ 2 queries (separate terms, not just "a", "b")
- [ ] **Detail pages** — open ≥ 3 items from different categories
- [ ] **Filters** — apply ≥ 2 filters (date range, category, sort)
- [ ] **Pagination** — go to page 2 or scroll until a new XHR fires

Run with `validate-capture.py --read-only`.

---

## Coverage heuristics — "have I browsed enough?"

General rules of thumb regardless of profile:

1. **One screen = one endpoint group minimum.** If you haven't opened a screen,
   its endpoints aren't in the trace. Open every top-level nav item.
2. **Modals fire their own endpoints.** If the app opens a modal on click,
   trigger at least one modal — its data loads lazily.
3. **Infinite-scroll triggers new requests at scroll breakpoints.** Scroll
   until you see a new XHR in DevTools (usually 2–3 viewport heights).
4. **Debounced inputs fire only after typing stops.** When testing search,
   type the query and then **wait 1–2 s**. Submitting without the pause
   misses the auto-complete endpoint entirely.
5. **Context-scoped apps need the context switch captured.** Apps like
   NotebookLM / Stitch scope all calls to the active notebook/project —
   switching notebook fires the "load workspace" endpoints you'll need.

---

## When a checklist step can't be completed

Record the reason in `assessment.md` and continue. Examples:

- **"Create" blocked by paywall** → note it; capture what you can.
- **CAPTCHA on login** → switch to pause-and-prompt flow; mark auth flow as
  `requires_manual_captcha` in assessment.md.
- **Geo-blocked feature** → note the country where capture was run; some
  endpoints may be unreachable.

Do NOT let a blocked step stop the whole capture — move on and let
`validate-capture.py` flag residual gaps.
