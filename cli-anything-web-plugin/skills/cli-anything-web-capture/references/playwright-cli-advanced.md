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

Some apps embed content in iframes (e.g., embedded editors, payment forms).

```bash
# List all frames and their URLs
playwright-cli -s=<app> run-code "async page => {
  return page.frames().map(f => f.url());
}"

# Interact with iframe content
playwright-cli -s=<app> run-code "async page => {
  const frame = page.locator('iframe#editor-iframe').contentFrame();
  await frame.locator('button.save').click();
}"
```

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
playwright-cli -s=<app> eval "(() => {
  if (window.__NEXT_DATA__) return 'Next.js';
  if (window.__NUXT__) return 'Nuxt';
  if (document.querySelector('[ng-version]')) return 'Angular';
  if (document.querySelector('[data-reactroot]')) return 'React';
  return 'Unknown';
})()"
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
