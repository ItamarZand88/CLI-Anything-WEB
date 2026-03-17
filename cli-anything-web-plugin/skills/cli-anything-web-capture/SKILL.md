---
name: cli-anything-web-capture
description: >
  Capture HTTP traffic from web apps using playwright-cli tracing. Handles browser
  setup, trace recording, systematic exploration (READ + WRITE operations), auth
  state persistence, and trace parsing. Use when recording traffic, starting Phase 1,
  or when the agent needs to capture API calls from a web app. Trigger phrases:
  "traffic capture", "recording", "tracing", "Phase 1", "playwright-cli", "record traffic"
version: 0.1.0
---

# CLI-Anything-Web Capture

Phase 1 of the cli-anything-web pipeline: capture comprehensive HTTP traffic
from the target web app using playwright-cli tracing (or chrome-devtools-mcp
as fallback).

---

## Prerequisites (Hard Gate)

Do NOT start unless:
- [ ] RECON-REPORT.md exists (from Phase 1a) OR site is already known
- [ ] playwright-cli is available (`npx @playwright/cli@latest --version`)

If RECON-REPORT.md is missing and the site is unfamiliar, invoke the
`web-reconnaissance` skill first.

If playwright-cli is not available, fall back to chrome-devtools MCP
(see Fallback section below).

---

## Step 1: Setup

```bash
# Create output directory
mkdir -p <app>/traffic-capture

# Open browser with named session
npx @playwright/cli@latest -s=<app> open <url> --headed --persistent

# If login required -- ask user to log in, wait for confirmation

# Save auth state BEFORE tracing (so you can restore later)
npx @playwright/cli@latest -s=<app> state-save <app>/traffic-capture/<app>-auth.json
```

---

## Step 2: Systematic Exploration (with trace)

```bash
# Start trace recording
npx @playwright/cli@latest -s=<app> tracing-start

# === EXPLORATION CHECKLIST ===
# For EACH resource/feature visible in the UI:

# A. READ operations (screenshot first to see what's there)
npx @playwright/cli@latest -s=<app> screenshot
npx @playwright/cli@latest -s=<app> snapshot
# Navigate to list views, detail pages, dashboards
# Click through pagination, filters, search

# B. WRITE operations (this is what agents skip!)
# Take a screenshot -> find the Create/Generate/New button -> click it
# Fill forms -> submit -> capture the POST/PUT request
# This is the MOST IMPORTANT part -- read-only traces are useless

# C. Other operations: settings, profile, export, delete
```

### Exploration Checklist by App Type

| App Type | Must capture | Example |
|----------|-------------|---------|
| CRUD app | List, Get, Create, Update, Delete per resource | Monday: boards list, board create, item create |
| Generation app | Create/Generate, Poll status, Download result | Suno: generate song, check status, download MP3 |
| Search app | Search query, Results, Filters, Pagination | Futbin: player search, price history |
| Chat/Query app | Send message, Receive response (streaming?), History | NotebookLM: ask question, get sources |

**For each app, the trace MUST contain at least one WRITE operation before stopping.**
If your trace only has GET requests, you haven't captured enough -- go back and
create/generate something.

---

## Step 3: Stop, Save, Parse

```bash
# Stop trace -- saves .network + resources/ with full bodies
npx @playwright/cli@latest -s=<app> tracing-stop

# Parse trace -> raw-traffic.json (only parses the LATEST trace files)
python ${CLAUDE_PLUGIN_ROOT}/scripts/parse-trace.py \
  .playwright-cli/traces/ \
  --output <app>/traffic-capture/raw-traffic.json

# Verify: check that write operations were captured
python -c "
import json
data = json.load(open('<app>/traffic-capture/raw-traffic.json'))
posts = [r for r in data if r['method'] in ('POST','PUT','PATCH','DELETE')]
print(f'Total: {len(data)} requests, {len(posts)} write operations')
if not posts:
    print('WARNING: No write operations captured! Go back and use Create/Generate features.')
"
```

---

## Step 4: Close Browser

```bash
npx @playwright/cli@latest -s=<app> close
```

---

## Use the Feature, Don't Reverse-Engineer JS

When you see a button in the UI but its endpoint isn't in the trace:
1. Start a NEW trace: `tracing-start`
2. Screenshot -> click the button -> fill the form -> submit
3. Stop: `tracing-stop` -> parse -> the endpoint is now captured

**Do NOT** grep through minified JS, read webpack chunks, or parse build manifests.
The browser IS the API documentation. 60 seconds of UI interaction beats 30 minutes
of JS analysis.

If an endpoint is missing from the trace -- USE THE FEATURE. The browser IS the
API documentation. If you can see it in the UI, you can capture it by using it.
This is faster, more reliable, and always correct -- JS analysis gives you guesses,
trace capture gives you facts.

---

## MCP Fallback (chrome-devtools)

If playwright-cli is not available, fall back to chrome-devtools MCP:

1. Launch debug Chrome: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/launch-chrome-debug.sh <url>`
2. If first time, ask user to log in. Wait for confirmation.
3. If MCP not connected: tell user "Type `/mcp`, find **chrome-devtools**, click **Reconnect**."
4. Use `mcp__chrome-devtools__*` tools: `navigate_page`, `list_network_requests`,
   `get_network_request`
5. Save to `<app>/traffic-capture/raw-traffic.json`

**NEVER use `mcp__claude-in-chrome__*` tools** -- blocked, cannot capture request bodies.

---

## WRITE Operations Verification

Before declaring capture complete, verify the trace contains WRITE operations:

```python
import json
data = json.load(open('<app>/traffic-capture/raw-traffic.json'))
posts = [r for r in data if r['method'] in ('POST', 'PUT', 'PATCH', 'DELETE')]
if not posts:
    raise SystemExit("No write operations captured. Go back and use Create/Generate features.")
print(f"Capture complete: {len(data)} requests, {len(posts)} write operations")
```

If zero WRITE operations: do NOT proceed. Go back to Step 2 and use the
Create/Generate/Submit features in the UI.

---

## Next Step

When capture is complete and raw-traffic.json has WRITE operations,
invoke the `cli-anything-web-methodology` skill to analyze the captured traffic.

Do NOT skip to implementation -- traffic must be analyzed first.

---

## References

- [Playwright CLI Tracing](references/playwright-cli-tracing.md) -- Trace file format, `.network` structure, how parse-trace.py works
- [Playwright CLI Sessions](references/playwright-cli-sessions.md) -- Named sessions, state-save/load, auth JSON format
- [Playwright CLI Advanced](references/playwright-cli-advanced.md) -- run-code, wait strategies, downloads, iframe handling
