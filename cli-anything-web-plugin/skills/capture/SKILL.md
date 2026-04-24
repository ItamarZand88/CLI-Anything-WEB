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
version: 0.4.0
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

**Default capture method:** playwright-cli tracing (standard workflow below).

### Optional `--mitmproxy` mode

Use this when the default `--mitmproxy` flag was passed to `/cli-anything-web`,
or when you need no body truncation, real-time noise filtering, and enhanced
metadata (timestamps, cookies, body sizes). Requires `pip install mitmproxy`
(Python 3.12+).

```bash
# Start the proxy (generates .playwright/cli.proxy.config.json automatically)
python ${CLAUDE_PLUGIN_ROOT}/scripts/mitmproxy-capture.py start-proxy --port 8080

# Open the browser routed through the proxy
npx @playwright/cli@latest -s=<app> open <url> \
  --config=.playwright/cli.proxy.config.json --headed

# ... browse normally (snapshot, click, fill, goto) ...

npx @playwright/cli@latest -s=<app> close
python ${CLAUDE_PLUGIN_ROOT}/scripts/mitmproxy-capture.py stop-proxy \
  --port 8080 -o <app>/traffic-capture/raw-traffic.json
```

The `start-proxy` command creates `.playwright/cli.proxy.config.json` as part
of startup — no manual config file needed. When the default playwright-cli path
fails entirely (e.g., Node not available), fall back to chrome-devtools-mcp via
`launch-chrome-debug.sh` — see HARNESS.md Tool Hierarchy.

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

> **If `--mitmproxy` mode:** Replace the `open` command above with:
> ```bash
> python ${CLAUDE_PLUGIN_ROOT}/scripts/mitmproxy-capture.py start-proxy --port 8080
> npx @playwright/cli@latest -s=<app> open <url> --config=.playwright/cli.proxy.config.json --headed
> ```
> This starts the proxy first, then opens the browser routed through it.
> All subsequent `snapshot`, `click`, `fill`, `goto` commands work exactly the same.

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

### Interpret fingerprint results

The fingerprint returns four groups: `framework`, `protection`, `auth`, `iframes`.
Map each `true` flag to the next action:

| Group | Action |
|---|---|
| **framework** | See `references/framework-detection.md` for the full protocol table (`googleBatch` / `nextPages` / `nextApp` / `nuxt` / `spaRoot`). |
| **protection** | See `references/protection-detection.md` — **always start at the escalation ladder at the top** (plain httpx → curl_cffi → curl_cffi + cookies → camoufox → hybrid). |
| **auth** | Table below (Auth detection section). |
| **iframes** | If `iframeCount > 0`, see `references/playwright-cli-advanced.md` for the in-iframe re-run snippet. |

Claude-facing shortcuts:
- `googleBatch: true` → generate `rpc/` subpackage (batchexecute protocol).
- `cloudflareManagedChallenge: true` → tier 4 (camoufox) is required; `curl_cffi` alone will fail.
- `awsWaf: true` → capture `aws-waf-token` cookie; use `curl_cffi` for GraphQL, cookie-only for SSR.
- `akamai: true` or `datadome: true` → 1–2 s delays between requests are mandatory.
- `serviceWorker: true` → note in assessment.md; generated CLI uses `service_workers="block"`.
- `iframeCount > 0` → re-run the fingerprint inside the iframe. Google Labs apps (Stitch / MusicFX / ImageFX) follow this pattern — parent has `WIZ_global_data`, iframe has the real app.

**Note:** `snapshot` and `click <ref>` auto-resolve iframes. Only drop down to
`run-code` for iframe interaction when built-in commands fail.

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
3. Save auth state and tighten permissions (CLAUDE.md mandates `chmod 600`):
```bash
npx @playwright/cli@latest -s=<app> state-save <app>/traffic-capture/<app>-auth.json
chmod 600 <app>/traffic-capture/<app>-auth.json
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

# Quick parse to see what endpoints appeared (saved alongside the full capture
# so it survives the session — don't output to /tmp).
python ${CLAUDE_PLUGIN_ROOT}/scripts/parse-trace.py .playwright-cli/traces/ --latest \
  --output <app>/traffic-capture/probe-traffic.json
```

This probe trace is separate from the full capture in Step 3 — Step 3 will
start a fresh trace that overwrites the `.network` file in `.playwright-cli/traces/`.
The parsed `probe-traffic.json` is kept in `traffic-capture/` so it stays available
for cross-referencing during Step 4.

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

> **If `--mitmproxy` mode:** Skip `tracing-start` and HAR recording above.
> mitmproxy is already capturing all traffic since Step 1 — just proceed
> to the exploration below. Every click, navigation, and form submission
> is automatically recorded by the proxy.

> **HAR recording is optional but recommended.** It produces a standard HAR file
> alongside the trace. This enables `mitmproxy2swagger` to auto-generate an
> OpenAPI spec: `pip install mitmproxy2swagger && mitmproxy2swagger -i capture.har -o api-spec.yaml -p <base-url>`
> The HAR file is saved when the browser context is closed (Step 5).

### Exploration by site profile

Use the **concrete targets** in `references/exploration-checklists.md` for the
profile identified in Step 2b. Each profile has an explicit entry count,
distinct-path count, and WRITE-op target that `validate-capture.py` (Step 4)
will enforce. Minimum bar across all profiles:

- ≥ 15 entries, ≥ 3 distinct URL paths, protocol ≠ `unknown`
- ≥ 1 WRITE op (unless the site is genuinely read-only — pass `--read-only` to the validator)
- < 50% error rate (dominant 4xx/5xx means auth or rate-limit failure)

### Pacing for protected sites

If any of `cloudflare`, `cloudflareManagedChallenge`, `akamai`, `datadome`,
`awsWaf`, or `rateLimit` fired in the fingerprint, **leave 1–2 s between
clicks / form submits**. Faster exploration triggers per-IP challenges within
~30 requests and corrupts the trace.

### General interaction rules

- **Click by ref (from snapshot) is most reliable:** `snapshot` → note ref → `click <ref>`
- **Refs go stale** — always take a fresh snapshot before clicking
- **For localized UIs** (Hebrew, Arabic, etc.) — use refs or data-testid, not text
- **For iframe-embedded apps** — `snapshot` + `click <ref>` auto-resolves iframes
- **Wait after generation** — if the app generates content async, wait for ≥ 15 s
  before the next action, otherwise the polling loop won't appear in the trace:
  ```bash
  npx @playwright/cli@latest -s=<app> run-code "async page => {
    await page.waitForTimeout(15000);
    return 'waited';
  }"
  ```
- **Debounced inputs** — after typing a search query, pause 1–2 s before the
  next action; submitting immediately misses the auto-complete endpoint.

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

# Gate — validate the capture before declaring Phase 1 complete.
# This check enforces: ≥15 entries, ≥3 distinct paths, protocol ≠ unknown,
# ≥1 WRITE op (add --read-only if the site is genuinely read-only), <50% error rate.
python ${CLAUDE_PLUGIN_ROOT}/scripts/validate-capture.py <app>
# OR for genuinely read-only sites:
# python ${CLAUDE_PLUGIN_ROOT}/scripts/validate-capture.py <app> --read-only
```

If `validate-capture.py` returns a non-zero exit code, **do not proceed to Step 5**.
Re-open the browser (Step 1), continue exploration to fill the gaps the validator
flagged, then re-run Step 4. Only mark the capture complete after the validator
passes (or warns, with your explicit sign-off on each warning).

For deeper inspection:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/analyze-traffic.py \
  <app>/traffic-capture/raw-traffic.json --summary
```

> **If `--mitmproxy` mode:** Replace the parse/analyze block above with:
> ```bash
> # Stop the proxy and save captured traffic (includes auto-analysis)
> python ${CLAUDE_PLUGIN_ROOT}/scripts/mitmproxy-capture.py stop-proxy \
>   --port 8080 -o <app>/traffic-capture/raw-traffic.json
>
> # Validate the capture (same gate applies)
> python ${CLAUDE_PLUGIN_ROOT}/scripts/validate-capture.py <app>
>
> # Then run the analyzer for the full report:
> python ${CLAUDE_PLUGIN_ROOT}/scripts/analyze-traffic.py \
>   <app>/traffic-capture/raw-traffic.json --summary
> ```
> No `tracing-stop` or `parse-trace.py` needed — mitmproxy already has the data.
> The analysis will include enhanced fields (request_sequence, session_lifecycle,
> endpoint_sizes) that are only available with mitmproxy capture.

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

**Fallback:** If playwright-cli is not available, see HARNESS.md Tool Hierarchy for chrome-devtools-mcp fallback instructions.

---

## Next Step

When capture is complete (raw-traffic.json has WRITE operations, or the site is
read-only with only GET requests), invoke `methodology` to analyze the traffic
and build the CLI.

---

## References

See `references/` for:
- `playwright-cli-commands.md` — command syntax, timeouts, ESM rules
- `playwright-cli-tracing.md` — trace file format, recovery protocol
- `playwright-cli-sessions.md` — named sessions, auth persistence
- `playwright-cli-advanced.md` — waits, iframes, localized UIs, downloads
- `framework-detection.md` — framework → protocol table
- `protection-detection.md` — anti-bot escalation ladder (curl_cffi → camoufox → hybrid)
- `api-discovery.md` — protocol priority chain, decision tree
- `exploration-checklists.md` — per-profile capture targets with concrete numbers
