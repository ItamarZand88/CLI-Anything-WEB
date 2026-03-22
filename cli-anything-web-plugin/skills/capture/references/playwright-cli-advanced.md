> **Note:** Commands below use `playwright-cli` as shorthand for `npx @playwright/cli@latest`.
> Always run via npx: `npx @playwright/cli@latest -s=<app> <command>`

# Playwright-CLI Advanced: run-code, Waits, and Downloads

Advanced playwright-cli commands for scenarios not covered by basic click/fill/snapshot -- wait strategies, iframe handling, file downloads, and page information extraction.

## The `run-code` Command

Execute arbitrary async Playwright code when built-in commands are insufficient:

```bash
playwright-cli -s=<app> run-code "async page => {
  // Your Playwright code here
  // Access page.context() for browser context operations
}"
```

## `run-code` vs `eval`

| Command | Use for | Supports async? |
|---------|---------|-----------------|
| `eval` | Quick expressions, DOM queries | No |
| `run-code` | Async operations, waits, downloads, complex flows | Yes |

```bash
# eval: quick DOM query (no await needed)
playwright-cli -s=<app> eval "document.title"

# run-code: async wait operation
playwright-cli -s=<app> run-code "async page => {
  await page.waitForLoadState('networkidle');
}"
```

## Wait Strategies

Critical for dynamic SPAs where content loads asynchronously.

### Wait for Network to Settle

```bash
# No network requests for 500ms
playwright-cli -s=<app> run-code "async page => {
  await page.waitForLoadState('networkidle');
}"
```

### Wait for Specific Element

```bash
# Wait for element to appear
playwright-cli -s=<app> run-code "async page => {
  await page.waitForSelector('#content-loaded');
}"

# Wait for loading spinner to disappear
playwright-cli -s=<app> run-code "async page => {
  await page.waitForSelector('.loading', { state: 'hidden' });
}"
```

### Wait for Specific API Response

```bash
# Wait for a particular API call to complete
playwright-cli -s=<app> run-code "async page => {
  await page.waitForResponse('**/api/data');
}"
```

### Wait for Condition

```bash
# Wait for app-level readiness flag
playwright-cli -s=<app> run-code "async page => {
  await page.waitForFunction(() => window.appReady === true);
}"
```

### Wait with Timeout

```bash
# Custom timeout (default is 30s)
playwright-cli -s=<app> run-code "async page => {
  await page.waitForSelector('.result', { timeout: 10000 });
}"

# Simple delay (use sparingly)
playwright-cli -s=<app> run-code "async page => {
  await page.waitForTimeout(2000);
}"
```

## Frame / Iframe Handling

Some apps embed content in iframes (e.g., Google Labs apps like Stitch, MusicFX;
embedded editors; payment forms). **Detect iframes early** — if the real app is
inside an iframe, all framework detection must be re-run inside that frame.

### Detecting iframes

```bash
# List all frames with URLs and names
playwright-cli -s=<app> run-code "async page => {
  return page.frames().map((f, i) => ({
    index: i,
    url: f.url(),
    name: f.name() || null
  }));
}"
```

If more than 1 frame exists, the app may be iframe-embedded. Common pattern:
- Frame 0: Parent/wrapper (e.g., `stitch.withgoogle.com`) — has `WIZ_global_data`
- Frame 1: Actual app (e.g., `app-companion-*.appspot.com`) — has the real SPA

### Google Labs Iframe Pattern

Google Labs apps (Stitch, MusicFX, ImageFX, etc.) embed a Vite/React SPA inside
an iframe on a Google App Engine domain. Key characteristics:
- Parent frame has `WIZ_global_data` but NO interactive UI
- Iframe has the actual app with a different framework (Vite, React)
- `snapshot` and `click <ref>` auto-resolve iframes (safe to use)
- `eval` does NOT reach inside iframes — use `run-code` with `page.frames()[1]`

### Reading iframe content

```bash
# Get text content from iframe
playwright-cli -s=<app> run-code "async page => {
  const frame = page.frames()[1];
  if (!frame) return 'no iframe';
  return await frame.evaluate(() => document.body.textContent.substring(0, 500));
}"

# Run framework detection inside iframe
playwright-cli -s=<app> run-code "async page => {
  const frame = page.frames()[1];
  if (!frame) return { error: 'no iframe' };
  return await frame.evaluate(() => ({
    title: document.title,
    spaRoot: document.querySelector('#app, #root')?.id || null,
    vite: !!document.querySelector('script[type=\"module\"][src*=\"/@vite\"]'),
    scripts: Array.from(document.querySelectorAll('script[src]')).map(s => s.src).slice(0, 10)
  }));
}"
```

### Interacting with iframe content

```bash
# Click a button inside an iframe (by locator)
playwright-cli -s=<app> run-code "async page => {
  const frame = page.locator('iframe').first().contentFrame();
  await frame.locator('button:has-text(\"Submit\")').click();
}"

# Fill an input inside an iframe
playwright-cli -s=<app> run-code "async page => {
  const frame = page.frames()[1];
  await frame.locator('[contenteditable]').first().click();
  await frame.locator('[contenteditable]').first().fill('');
  await frame.type('[contenteditable]', 'my text');
}"
```

**Tip:** `snapshot` + `click <ref>` works across iframes automatically — this is
the preferred approach. Only use `run-code` for iframe interaction when you need
to target elements that don't have good snapshot refs.

## Handling Localized / RTL UIs

When the browser is set to Hebrew, Arabic, Chinese, or another non-English language,
UI text will be localized. **Never hardcode translated strings** in your capture
commands — they break when the language changes.

### Interaction priority for localized UIs

1. **Click by ref** (most reliable): `click f8e77` — language-independent
2. **Click by role + test-id**: Elements with `data-testid` attributes
3. **Click by role**: `getByRole('button', { name: /generate/i })` via run-code
4. **Click by position**: `.first()`, `.last()`, `.nth(2)` via run-code

### Avoid

- `click "button text"` with translated text — breaks in other locales
- Hardcoding translated strings in notes (use English descriptions)
- Assuming LTR layout for coordinate-based clicks

### Reading localized UI text

```bash
# Get all button labels (regardless of language)
playwright-cli -s=<app> run-code "async page => {
  const frame = page.frames().length > 1 ? page.frames()[1] : page.mainFrame();
  return await frame.evaluate(() =>
    Array.from(document.querySelectorAll('button, [role=\"button\"]'))
      .map(b => ({
        text: b.textContent?.trim()?.substring(0, 50),
        testId: b.getAttribute('data-testid'),
        ariaLabel: b.getAttribute('aria-label')
      }))
      .filter(b => b.text || b.testId || b.ariaLabel)
  );
}"
```

This returns test-ids and aria-labels alongside the localized text, making it
easier to find language-independent selectors.

---

## File Download Handling

Critical for content generation apps (Suno audio, image generators, etc.).

```bash
# Wait for download to start, then get the file path
playwright-cli -s=<app> run-code "async page => {
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.click('#download-btn')
  ]);
  await download.saveAs('./downloaded-file.mp3');
  return download.suggestedFilename();
}"
```

This pattern is important during Phase 1 traffic capture -- triggering a download reveals the download URL endpoint that the generated CLI will call directly via httpx.

## Geolocation and Permissions

Some apps serve different content or APIs based on location:

```bash
# Set geolocation (e.g., New York)
playwright-cli -s=<app> run-code "async page => {
  await page.context().grantPermissions(['geolocation']);
  await page.context().setGeolocation({ latitude: 40.7128, longitude: -74.0060 });
}"

# Grant other permissions
playwright-cli -s=<app> run-code "async page => {
  await page.context().grantPermissions([
    'geolocation',
    'notifications',
    'clipboard-read'
  ]);
}"

# Clear permission overrides
playwright-cli -s=<app> run-code "async page => {
  await page.context().clearPermissions();
}"
```

## Page Information Extraction

Useful during Phase 1 (Capture) and Phase 2 (Analyze) for understanding the app structure.

### Get All Links

```bash
playwright-cli -s=<app> run-code "async page => {
  return await page.evaluate(() =>
    Array.from(document.querySelectorAll('a[href]'))
      .map(a => a.href)
      .filter(h => h.startsWith('http'))
  );
}"
```

### Get Page Metadata

```bash
playwright-cli -s=<app> run-code "async page => {
  return await page.evaluate(() =>
    JSON.stringify({
      title: document.title,
      url: location.href,
      meta: Object.fromEntries(
        Array.from(document.querySelectorAll('meta[name]'))
          .map(m => [m.name, m.content])
      )
    })
  );
}"
```

### Detect Frontend Framework

```bash
# Use run-code for multi-branch detection — eval doesn't support IIFE block bodies
npx @playwright/cli@latest -s=<app> run-code "async page => { return await page.evaluate(() => { if (window.__NEXT_DATA__) return 'Next.js Pages Router'; if (document.documentElement.outerHTML.includes('self.__next_f.push')) return 'Next.js App Router'; if (window.__NUXT__) return 'Nuxt'; if (window.__remixContext) return 'Remix'; if (document.querySelector('[ng-version]')) return 'Angular'; if (document.querySelector('[data-reactroot]')) return 'React'; return 'Unknown'; }); }"
```

## How It Connects to Our Pipeline

### Phase 1 Step 2 (Site Assessment)
- `eval` for framework detection and quick DOM queries
- `run-code` for wait-then-check patterns on slow-loading pages

### Phase 1 Step 3 (Full Capture)
- `run-code` for download handling -- triggering downloads to capture the download URL
- `run-code` for iframe interaction when the app uses embedded editors
- Wait strategies to ensure all API calls complete before `tracing-stop`

### Phase 2 (Analyze)
- `eval` for extracting page metadata, link structure, and DOM patterns
- Helps identify which parts of the page correspond to which API endpoints
