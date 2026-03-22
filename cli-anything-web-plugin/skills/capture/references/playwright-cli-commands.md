> **Note:** Commands below use `playwright-cli` as shorthand for `npx @playwright/cli@latest`.
> Always run via npx: `npx @playwright/cli@latest -s=<app> <command>`

# Playwright-CLI Command Quick Reference

Complete syntax reference for every playwright-cli command used during capture.

---

## CRITICAL: Execution Rules

### NEVER use `run_in_background` for playwright-cli commands

All playwright-cli commands during capture MUST run in the foreground. Background
execution causes task ID tracking failures — the command completes before the agent
can read the output.

### Timeout Recommendations

| Command | Recommended timeout | Notes |
|---------|-------------------|-------|
| `open` | 30s | May timeout on heavy SPAs — non-fatal |
| `snapshot` | 15s | Fast, returns accessibility tree |
| `click <ref>` | 20s | May trigger navigation |
| `type "text"` | 15s | Types character by character |
| `fill <ref> "text"` | 15s | Sets value directly (faster than type) |
| `eval "expr"` | 10s | Quick DOM queries only |
| `run-code "..."` | 15-60s | 15s for simple, 60s for waits/generation |
| `tracing-start` | 10s | Starts recording |
| `tracing-stop` | 15s | Saves trace files |
| `state-save` | 15s | Saves cookies/storage |
| `screenshot` | 10s | Captures viewport |
| `goto <url>` | 20s | Full page navigation |

### ESM Context — No `require()`

`run-code` executes in an ESM context. `require()` is NOT available.
Use `await import()` instead:

```bash
# WRONG — will fail with "ReferenceError: require is not defined"
run-code "async page => { const fs = require('fs'); ... }"

# RIGHT — use dynamic import
run-code "async page => { const fs = await import('fs'); ... }"
```

---

## Session Management

### open — Start browser session

```bash
playwright-cli -s=<app> open <url> --headed --persistent
```

Opens a persistent Chrome browser. The `--headed` flag shows the browser window.
The `--persistent` flag keeps the session alive between commands.

**Output:** `Browser <app> opened with pid <N>`
**Note:** If a session already exists, it RE-ATTACHES (doesn't create a new one).

### close — End browser session

```bash
playwright-cli -s=<app> close
```

Closes the browser and ends the session.

### list — Show active sessions

```bash
playwright-cli list
```

Lists all active browser sessions with their PIDs.

### kill-all — Force-close all sessions

```bash
playwright-cli kill-all
```

Kills all daemon processes. Use to clean up stale sessions.

---

## Navigation

### goto — Navigate to URL

```bash
playwright-cli -s=<app> goto <url>
```

Navigates the current page to the given URL. Has a 5s snapshot timeout that may
fail on SPAs — use `run-code` with `page.goto()` if this happens.

---

## Page Inspection

### snapshot — Get accessibility tree with refs

```bash
playwright-cli -s=<app> snapshot
```

Returns the accessibility tree of the current page with reference IDs (e.g., `f1e27`)
that can be used with `click` and `fill`.

**Important:** Refs go stale after any navigation or DOM change. Always take a
**fresh snapshot** before clicking.

**Iframes:** Snapshot includes iframe content — refs inside iframes work with `click`.

### screenshot — Capture page image

```bash
playwright-cli -s=<app> screenshot
```

Captures a screenshot of the current viewport. Returns the image inline (no file
path argument — the image is displayed in the tool output).

**To save a screenshot to a file:**
```bash
playwright-cli -s=<app> run-code "async page => {
  const fs = await import('fs');
  const buf = await page.screenshot({ fullPage: true });
  fs.writeFileSync('<app>/traffic-capture/screenshot.png', buf);
  return 'saved';
}"
```

### eval — Quick DOM expression

```bash
playwright-cli -s=<app> eval "<javascript-expression>"
```

Evaluates a single JavaScript expression in the page context.

**Limitations:**
- No async/await support
- Ternary operators and complex expressions may fail with "not well-serializable"
- Cannot access iframes (runs in main frame only)
- Does NOT support multi-line or IIFE blocks

**When eval fails, use run-code instead:**
```bash
# eval fails: "Passed function is not well-serializable!"
playwright-cli -s=<app> eval "typeof X !== 'undefined' ? 'yes' : 'no'"

# run-code works:
playwright-cli -s=<app> run-code "async page => {
  return await page.evaluate(() => typeof X !== 'undefined' ? 'yes' : 'no');
}"
```

---

## Interaction

### click — Click element by ref or text

```bash
# By ref (from snapshot) — most reliable
playwright-cli -s=<app> click <ref>

# By visible text — fallback
playwright-cli -s=<app> click "Button Text"
```

Clicks an element. Refs from snapshot are most reliable. Text matching uses
exact visible text.

**For iframes:** Refs from snapshot auto-resolve to the correct frame.

### fill — Set input value directly

```bash
playwright-cli -s=<app> fill <ref> "text value"
```

Sets the value of an input/textbox directly (faster than `type`).
Clears existing content first.

### type — Type text character by character

```bash
playwright-cli -s=<app> type "text to type"
```

Types text into the currently focused element, character by character.
Triggers keyboard events for each character (useful for autocomplete).

**Important:** Must `click` the target input first to focus it.

---

## Tracing (Traffic Capture)

### tracing-start — Begin recording

```bash
playwright-cli -s=<app> tracing-start
```

Starts recording all network requests, DOM changes, and actions.
Returns the trace file path.

### tracing-stop — End recording and save

```bash
playwright-cli -s=<app> tracing-stop
```

Stops recording and saves trace files to `.playwright-cli/traces/`.

**Known issue:** If the session reconnected (browser was already open),
`tracing-stop` may fail with "Cannot read properties of undefined".
Recovery: just `tracing-start` again and re-do the actions.

**Recovery protocol:**
1. If `tracing-stop` fails once — try again with 15s timeout
2. If it fails twice — the trace is lost. Start a new trace.
3. NEVER retry more than twice — you'll waste time

---

## Auth State

### state-save — Export cookies and storage

```bash
playwright-cli -s=<app> state-save <path>
```

Saves all cookies, localStorage, and sessionStorage to a JSON file.
The format matches Playwright's `storageState` format:

```json
{
  "cookies": [...],
  "origins": [{"origin": "...", "localStorage": [...]}]
}
```

### state-load — Restore saved state

```bash
playwright-cli -s=<app> state-load <path>
```

Restores cookies and storage from a previously saved state file.

---

## Advanced: run-code

### Syntax

```bash
playwright-cli -s=<app> run-code "async page => { /* code */ }"
```

Executes arbitrary async Playwright code with full access to the `page` object.
Use for anything that built-in commands can't handle.

### Common Patterns

**Wait for network idle:**
```bash
run-code "async page => { await page.waitForLoadState('networkidle'); }"
```

**Wait for specific element:**
```bash
run-code "async page => { await page.waitForSelector('.result', { timeout: 10000 }); }"
```

**Wait for API response:**
```bash
run-code "async page => { await page.waitForResponse('**/api/data'); }"
```

**Interact with iframe:**
```bash
run-code "async page => {
  const frame = page.frames()[1];
  return await frame.evaluate(() => document.body.textContent.substring(0, 500));
}"
```

**Click inside iframe:**
```bash
run-code "async page => {
  const frame = page.locator('iframe').first().contentFrame();
  await frame.locator('button:has-text(\"Submit\")').click();
}"
```

**List all frames:**
```bash
run-code "async page => {
  return page.frames().map((f, i) => ({ index: i, url: f.url(), name: f.name() || null }));
}"
```

**Evaluate in specific frame:**
```bash
run-code "async page => {
  const frame = page.frames()[1];
  return await frame.evaluate(() => ({
    title: document.title,
    bodyLength: document.body.textContent.length
  }));
}"
```

**Handle download:**
```bash
run-code "async page => {
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.click('#download-btn')
  ]);
  await download.saveAs('./output-file');
  return download.suggestedFilename();
}"
```
