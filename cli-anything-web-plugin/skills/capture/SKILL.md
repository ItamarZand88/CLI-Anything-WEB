---
name: capture
description: >
  Capture HTTP traffic from web apps using playwright-cli. Includes site fingerprinting
  (framework detection, protection checks, iframe detection, auth detection, API discovery)
  and full traffic recording with tracing and optional HAR output.
  TRIGGER when: "record traffic from", "capture API calls from", "start Phase 1 for",
  "analyze traffic from URL", "assess site", "site fingerprint", "start capture for",
  "open browser for", or any URL is given as the first step of CLI generation.
  DO NOT trigger for: Phase 2 implementation, test writing, or quality validation.
version: 0.3.0
---

# Traffic Capture (Phase 1)

Assess the site, then capture comprehensive HTTP traffic. This skill combines
site assessment with full traffic recording in a single browser session.

---

## CRITICAL EXECUTION RULES

> **NEVER use `run_in_background: true` for ANY playwright-cli command.**
> All playwright-cli commands must run in the foreground with appropriate timeouts.
> Background execution causes task ID tracking failures — the command completes
> before you can read the output. See `references/playwright-cli-commands.md`
> for the timeout table.

> **NEVER use `eval` for complex expressions.** `eval` fails silently on ternaries,
> comma operators, and multi-branch logic with "not well-serializable" errors.
> Use `run-code` instead. See `references/framework-detection.md` for details.

> **ESM context — no `require()`.** `run-code` uses ESM. Use `await import('fs')`
> instead of `require('fs')`. See `references/playwright-cli-commands.md`.

---

## Prerequisites (Hard Gate)

Do NOT start unless:
- [ ] playwright-cli is available (`npx @playwright/cli@latest --version`)
- [ ] Target URL is known

If playwright-cli fails, fall back to chrome-devtools-mcp (see HARNESS.md Tool Hierarchy).

### Public API Shortcut

If the target site has a **documented public REST/JSON API** (e.g., Hacker News Firebase API, Dev.to API, Reddit API, Wikipedia API), browser capture is optional:

1. Probe the API endpoints directly with `httpx` or `curl`
2. Save responses as `<app>/traffic-capture/raw-traffic.json`
3. Skip to Phase 2 (methodology)

This applies when:
- API docs exist (OpenAPI/Swagger, developer docs page, `/api/` prefix)
- The API is publicly accessible without browser-specific auth
- Endpoints return JSON (not HTML)

If unsure whether a public API exists, proceed with browser capture as normal.

### Resume from Checkpoint

Before starting, check if a previous capture session exists:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/capture-checkpoint.py restore <app>
```

If a checkpoint exists, read the `guidance` field and **resume from the last
completed step** instead of starting over. This prevents duplicate work when
sessions are interrupted.

---

## Step 1: Setup

```bash
# Create output directory
mkdir -p <app>/traffic-capture

# Clear any stale sessions
npx @playwright/cli@latest kill-all 2>/dev/null || true

npx @playwright/cli@latest -s=<app> open <url> --headed --persistent
# Note: heavy SPAs (Next.js, React) may show "TimeoutError: page._snapshotForAI" on open.
# This is non-fatal — verify with: npx @playwright/cli@latest list
#
# IMPORTANT — "Browser opened with pid..." in command output means the daemon
# RE-ATTACHED to the existing browser, NOT that a new session was created.
# Do NOT re-navigate or restart when you see this. The session is still open.
```

**Do NOT ask the user to log in yet** — Step 2 will determine if auth is needed.

---

## Step 2: Site Fingerprint (Single Command)

Run the all-in-one site fingerprint command instead of individual eval calls.
This is faster, more reliable, and detects framework + protection + iframes +
auth requirements in one shot.

**Use the script file** — multi-line JS with arrow functions and optional chaining
fails in playwright-cli's single-line command parser. The script file approach
has been tested and works reliably:

```bash
npx @playwright/cli@latest -s=<app> run-code "$(grep -v '^\s*//' ${CLAUDE_PLUGIN_ROOT}/scripts/site-fingerprint.js | tr '\n' ' ')"
```

> **IMPORTANT:** The `site-fingerprint.js` script must be loaded via the command
> above. Do NOT copy-paste the JS inline — it will fail with SyntaxError.
> The `grep -v` strips comments and `tr` joins lines for single-line execution.
```

### Interpret fingerprint results

**Framework:**
- `googleBatch: true` → Google batchexecute RPC protocol. Generate `rpc/` subpackage.
- `nextPages: true` → Next.js Pages Router. Extract `__NEXT_DATA__` + trace `/_next/data/` fetches.
- `nextApp: true` → Next.js App Router. Trace client navigations for RSC payloads.
- `nuxt: true` → Nuxt. Extract `__NUXT__` + trace API calls.
- No framework flags → likely SSR HTML or custom SPA. Check for REST API in probe.

**Protection:**
- `cloudflare: true` → Use `curl_cffi` with `impersonate='chrome'` in generated CLI.
- `awsWaf: true` → Need WAF token cookie via browser. Use curl_cffi for API calls.
- `captcha: true` → Add pause-and-prompt to auth flow.
- `serviceWorker: true` → Site has an active Service Worker that may intercept requests
  and hide them from traces. Note in assessment.md. Generated CLI's auth.py should use
  `service_workers="block"` in browser context. See `references/protection-detection.md`.

**Iframes:**
- `iframeCount > 0` → App is iframe-embedded. **Re-run detection inside the iframe:**

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

Common iframe pattern: Google Labs apps (Stitch, MusicFX, ImageFX) embed a
Vite/React SPA in an iframe. Parent has `WIZ_global_data`, iframe has the real app.
See `references/playwright-cli-advanced.md` for iframe interaction patterns.

**Note:** `snapshot` and `click <ref>` auto-resolve iframes. Only use `run-code`
for iframe interaction when built-in commands fail.

### Auth detection (BEFORE exploration)

Check the fingerprint auth fields:

| Condition | Meaning | Action |
|-----------|---------|--------|
| `hasLoginButton && !hasUserMenu` | Login required, not logged in | Ask user to log in NOW |
| `hasUserMenu` | Already logged in | Proceed to capture |
| `!hasLoginButton && !hasUserMenu` | No auth needed (public site) | Skip auth, proceed |

**If auth is needed:**
1. Tell the user: "This site requires login. Please log in in the browser window."
2. Wait for user confirmation
3. Save auth state:
```bash
npx @playwright/cli@latest -s=<app> state-save <app>/traffic-capture/<app>-auth.json
```

**If NO auth is needed:** Skip directly to Step 2b.

### 2b. Classify Site Profile

Based on fingerprint results AND what you see in the UI, classify the site:

| Profile | Auth? | Operations | Exploration Focus |
|---------|-------|-----------|-------------------|
| **Auth + CRUD** | Yes | Create, Read, Update, Delete | Full CRUD per resource |
| **Auth + Generation** | Yes | Generate, Poll, Download | Generation lifecycle + projects |
| **Auth + Read-only** | Yes | Read, Search, Export | Read operations + auth flow |
| **No-auth + CRUD** | No/Optional | Full CRUD | Skip auth, full CRUD |
| **No-auth + Read-only** | No | Read, Search | Minimal capture |

### 2c. Quick API Probe (Force SPA Navigation Trick)

Start a SHORT trace, click 3-4 internal links, stop. This reveals hidden API
endpoints that SSR hides on initial page load.

```bash
npx @playwright/cli@latest -s=<app> tracing-start
npx @playwright/cli@latest -s=<app> click <internal-link-1>
npx @playwright/cli@latest -s=<app> click <internal-link-2>
npx @playwright/cli@latest -s=<app> click <internal-link-3>
npx @playwright/cli@latest -s=<app> tracing-stop

# Quick parse to see what endpoints appeared
python ${CLAUDE_PLUGIN_ROOT}/scripts/parse-trace.py .playwright-cli/traces/ --latest --output /tmp/probe.json
```

Check the probe results — what API patterns did you find?
See `references/api-discovery.md` for the priority chain and decision tree.

### 2d. Write Assessment Summary

Create `<app>/traffic-capture/assessment.md` to consolidate all findings:

```markdown
# Site Assessment: <app>

- **URL**: <url>
- **Framework**: <detected framework or "none/custom">
- **Protocol**: <REST / GraphQL / batchexecute / HTML scraping / hybrid>
- **Protection**: <none / cloudflare / captcha / aws-waf / etc.>
- **Auth required**: <yes (type: Google SSO / cookie / JWT / API key) / no>
- **Iframes**: <yes (N frames, app in frame N at <url>) / no>
- **Site profile**: <Auth+CRUD / Auth+Generation / Auth+Read-only / No-auth+CRUD / No-auth+Read-only>
- **Capture strategy**: <API-first / SSR+API hybrid / batchexecute / HTML scraping / protected-manual>
- **Key observations**: <any quirks, localized UI, rate limits, special patterns>
```

---

## Step 3: Full Traffic Capture

Now do the comprehensive capture based on what Step 2 revealed.

```bash
# Optional: Start HAR recording alongside trace for standard-format capture
# HAR files enable mitmproxy2swagger (auto OpenAPI spec) and third-party analysis tools
npx @playwright/cli@latest -s=<app> run-code "async page => {
  await page.context().routeFromHAR('<app>/traffic-capture/capture.har', {
    update: true,
    updateContent: 'embed',
    updateMode: 'full'
  });
  return 'HAR recording started';
}"

# Start fresh trace for full capture (note the trace ID from output!)
npx @playwright/cli@latest -s=<app> tracing-start
# Output: "trace-<ID>" — record this ID

```

> **HAR recording is optional but recommended.** It produces a standard HAR file
> alongside the trace. This enables `mitmproxy2swagger` to auto-generate an
> OpenAPI spec: `pip install mitmproxy2swagger && mitmproxy2swagger -i capture.har -o api-spec.yaml -p <base-url>`
> The HAR file is saved when the browser context is closed (Step 5).

### Exploration by site profile

Use the profile-specific checklist from Step 2b:

**Auth + CRUD:**
```
For EACH resource visible in the UI:
- [ ] List/browse: navigate to list view
- [ ] Detail: open one item
- [ ] Create: fill form, submit (capture POST body!)
- [ ] Update: edit an item, save
- [ ] Delete: delete a test item
- [ ] Settings/profile: check app settings
- [ ] Export: if available, trigger export/download
```

**Auth + Generation:**
```
- [ ] Dashboard/projects: navigate to project list
- [ ] Open existing project: view editor/canvas
- [ ] Generate new content: type prompt, click generate, WAIT for completion
- [ ] Edit/iterate: modify generation, re-generate
- [ ] Export/download: trigger download of generated content
- [ ] Delete: delete a test project
- [ ] Settings: check model selection, preferences
```

**Auth + Read-only:**
```
- [ ] Main view: navigate to primary content
- [ ] Search/filter: use search functionality
- [ ] Detail pages: open 2-3 different items
- [ ] Pagination: go to page 2 if available
- [ ] Export: if available
```

**No-auth + CRUD:**
```
Same as Auth + CRUD, but skip auth-related captures.
```

**No-auth + Read-only:**
```
- [ ] Homepage: capture initial data
- [ ] Search: try 2-3 different queries
- [ ] Detail pages: open 2-3 items
- [ ] Filters: apply different filters
- [ ] Pagination: check next page
```

### General interaction rules

- **Click by ref (from snapshot) is most reliable:** `snapshot` → note ref → `click <ref>`
- **Refs go stale** — always take a fresh snapshot before clicking
- **For localized UIs** (Hebrew, Arabic, etc.) — use refs or data-testid, not text
- **For iframe-embedded apps** — `snapshot` + `click <ref>` auto-resolves iframes
- **Wait after generation** — if the app generates content async, wait:
  ```bash
  npx @playwright/cli@latest -s=<app> run-code "async page => {
    await page.waitForTimeout(15000);
    return 'waited';
  }"
  ```
- **The trace MUST contain at least one WRITE operation** (POST/PUT/DELETE) unless
  the site is genuinely read-only (see exception below)

**Exception for read-only sites:** If the site is genuinely read-only, the trace
may contain only GET requests. Note "read-only site" in `assessment.md` and proceed.

---

## Step 4: Stop, Save, Parse

```bash
npx @playwright/cli@latest -s=<app> tracing-stop
```

**If `tracing-stop` fails:**
1. Retry once with 15s timeout
2. If it fails again — the trace is lost. Start a new trace (Step 3).
3. **NEVER retry more than twice.** See `references/playwright-cli-tracing.md` for recovery.

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/parse-trace.py \
  .playwright-cli/traces/ --latest \
  --output <app>/traffic-capture/raw-traffic.json

# parse-trace.py now auto-runs analyze-traffic.py and produces:
#   - <app>/traffic-capture/raw-traffic.json (raw request/response data)
#   - <app>/traffic-capture/traffic-analysis.json (auto-detected protocol, auth, endpoints)
#
# The analysis output shows: protocol type, auth pattern, endpoint groups,
# GraphQL operations, batchexecute RPC IDs, and suggested CLI commands.
# Review the analysis — anything marked "unknown" needs manual investigation.

# You can also run the analyzer separately for more detail:
python ${CLAUDE_PLUGIN_ROOT}/scripts/analyze-traffic.py \
  <app>/traffic-capture/raw-traffic.json --summary
```

---

## Step 5: Close

```bash
npx @playwright/cli@latest -s=<app> close

# Mark capture complete
python ${CLAUDE_PLUGIN_ROOT}/scripts/capture-checkpoint.py update <app> --step complete
```

---

## If an endpoint is missing — USE THE FEATURE

Don't grep JS bundles. Start a new trace → screenshot → click the button → fill
→ submit → stop → parse. The browser IS the API documentation.

---

## Fallback

**Fallback:** If playwright-cli is not available, see HARNESS.md Tool Hierarchy
for chrome-devtools-mcp fallback instructions.

---

## Next Step

When capture is complete (raw-traffic.json has WRITE operations, or the site is
read-only with only GET requests), invoke `methodology` to analyze the traffic
and build the CLI.

---

## References

See `references/` for: command syntax (playwright-cli-commands.md), tracing (playwright-cli-tracing.md),
sessions (playwright-cli-sessions.md), advanced patterns (playwright-cli-advanced.md),
framework detection (framework-detection.md), protection (protection-detection.md),
API discovery (api-discovery.md).
