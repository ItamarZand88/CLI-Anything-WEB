---
name: capture
description: >
  Capture HTTP traffic from web apps using playwright-cli. Includes site assessment
  (framework detection, protection checks, API discovery) and full traffic recording
  with tracing. Use when recording traffic, starting Phase 1, capturing API calls,
  analyzing a web app's architecture, or detecting frameworks and protections.
version: 0.2.0
---

# Traffic Capture (Phase 1)

Assess the site, then capture comprehensive HTTP traffic. This skill combines
site assessment (formerly separate "recon") with full traffic recording in a
single browser session.

---

## Prerequisites (Hard Gate)

Do NOT start unless:
- [ ] playwright-cli is available (`npx @playwright/cli@latest --version`)
- [ ] Target URL is known

If playwright-cli fails, fall back to chrome-devtools-mcp (see HARNESS.md Tool Hierarchy).

---

## Step 1: Setup

```bash
# Create output directory
mkdir -p <app>/traffic-capture

# Open browser with named session
npx @playwright/cli@latest -s=<app> open <url> --headed --persistent

# If login required -- ask user to log in, wait for confirmation

# Save auth state BEFORE tracing
npx @playwright/cli@latest -s=<app> state-save <app>/traffic-capture/<app>-auth.json
```

---

## Step 2: Quick Site Assessment

Before full capture, run a quick assessment to guide the capture strategy.
This takes ~60 seconds and prevents wasted effort.

### 2a. Framework Detection

```bash
# Next.js Pages Router
npx @playwright/cli@latest -s=<app> eval "document.getElementById('__NEXT_DATA__')?.textContent?.substring(0, 200)"

# Next.js App Router (RSC)
npx @playwright/cli@latest -s=<app> eval "typeof self !== 'undefined' && document.querySelector('script[src*=\"_next\"]')?.src || 'no-next-app'"

# Nuxt
npx @playwright/cli@latest -s=<app> eval "typeof window.__NUXT__ !== 'undefined' ? 'nuxt' : 'not-nuxt'"

# Google batchexecute
npx @playwright/cli@latest -s=<app> eval "typeof WIZ_global_data !== 'undefined' ? 'google-batchexecute' : 'not-google'"

# Generic SPA root
npx @playwright/cli@latest -s=<app> eval "document.querySelector('#app, #root, #__next, #__nuxt')?.id || 'no-spa-root'"
```

See `references/framework-detection.md` for the complete detection command set.

### 2b. Protection Check

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
    rateLimit: html.includes('429') || body.includes('too many requests')
  };
})()"
```

Also check robots.txt:
```bash
npx @playwright/cli@latest -s=<app> goto <url>/robots.txt
npx @playwright/cli@latest -s=<app> snapshot
```

See `references/protection-detection.md` for detailed checks.

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

Check the probe results -- what API patterns did you find?
See `references/api-discovery.md` for the priority chain.
See `references/strategy-selection.md` for the decision tree.

### 2d. Log findings and choose strategy

Based on Steps 2a-2c, determine the capture strategy:
- **SPA + REST API found** -- standard full trace capture
- **SSR + __NEXT_DATA__** -- focus on client-side navigations
- **Google batchexecute** -- trace + eval WIZ_global_data for tokens
- **Cloudflare/protected** -- add delays, note rate limits
- **No API found** -- try more internal navigation, or site may not be CLI-suitable

Log findings to terminal. No separate RECON-REPORT.md needed.

---

## Step 3: Full Traffic Capture

Now do the comprehensive capture based on what Step 2 revealed.

```bash
# Start fresh trace for full capture
npx @playwright/cli@latest -s=<app> tracing-start

# === EXPLORATION CHECKLIST ===
# For EACH resource/feature visible in the UI:

# A. READ operations
npx @playwright/cli@latest -s=<app> screenshot
npx @playwright/cli@latest -s=<app> snapshot
# Navigate to list views, detail pages, dashboards

# B. WRITE operations (MOST IMPORTANT -- don't skip!)
# Screenshot -> find Create/Generate button -> click it -> fill forms -> submit

# C. Other: settings, profile, export, delete
```

**Exploration checklist by app type:**

| App Type | Must capture | Example |
|----------|-------------|---------|
| CRUD app | List, Get, Create, Update, Delete per resource | Monday: boards list, board create |
| Generation app | Create/Generate, Poll status, Download result | Suno: generate song, download MP3 |
| Search app | Search query, Results, Filters, Pagination | Futbin: player search, prices |
| Chat/Query app | Send message, Receive response, History | NotebookLM: ask, get sources |

**The trace MUST contain at least one WRITE operation before stopping.**

**Exception for read-only sites:** If the site is genuinely read-only (search engine,
dashboard, analytics viewer with no create/update/delete), the trace may contain only
GET requests. In this case, note "read-only site — no write operations" in `<APP>.md`
and proceed. The generated CLI will have read-only commands (list, get, search) but
no create/update/delete commands. This is valid.

---

## Step 4: Stop, Save, Parse

```bash
npx @playwright/cli@latest -s=<app> tracing-stop

python ${CLAUDE_PLUGIN_ROOT}/scripts/parse-trace.py \
  .playwright-cli/traces/ --latest \
  --output <app>/traffic-capture/raw-traffic.json

# Verify WRITE operations captured
python -c "
import json
data = json.load(open('<app>/traffic-capture/raw-traffic.json'))
posts = [r for r in data if r['method'] in ('POST','PUT','PATCH','DELETE')]
print(f'Total: {len(data)} requests, {len(posts)} write operations')
if not posts:
    print('WARNING: No write operations! Go use Create/Generate features.')
"
```

---

## Step 5: Close

```bash
npx @playwright/cli@latest -s=<app> close
```

---

## If an endpoint is missing -- USE THE FEATURE

Don't grep JS bundles. Start a new trace -> screenshot -> click the button -> fill
-> submit -> stop -> parse. The browser IS the API documentation.

---

## Fallback

**Fallback:** If playwright-cli is not available, see HARNESS.md Tool Hierarchy
for chrome-devtools-mcp fallback instructions.

---

## Next Step

When capture is complete and raw-traffic.json has WRITE operations, invoke
`methodology` to analyze the traffic and build the CLI.

---

## Reference Files

- [Tracing format](references/playwright-cli-tracing.md) -- trace file structure, .network format
- [Sessions & auth](references/playwright-cli-sessions.md) -- named sessions, state-save format
- [Advanced commands](references/playwright-cli-advanced.md) -- run-code, waits, downloads
- [Framework detection](references/framework-detection.md) -- SSR framework eval commands
- [Protection detection](references/protection-detection.md) -- anti-bot checks
- [API discovery](references/api-discovery.md) -- API finding priority chain
- [Strategy selection](references/strategy-selection.md) -- decision tree for capture approach
