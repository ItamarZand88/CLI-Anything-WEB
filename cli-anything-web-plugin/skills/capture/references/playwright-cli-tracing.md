> **Note:** Commands below use `playwright-cli` as shorthand for `npx @playwright/cli@latest`.
> Always run via npx: `npx @playwright/cli@latest -s=<app> <command>`

# Playwright-CLI Tracing for Traffic Capture

Capture detailed execution traces containing full HTTP request/response bodies, DOM snapshots, screenshots, and timing data. This is the primary input for CLI generation.

## Basic Usage

```bash
# Start trace recording
playwright-cli -s=<app> tracing-start

# Browse, click, interact with the app...
playwright-cli -s=<app> open https://example.com --headed --persistent
playwright-cli -s=<app> snapshot
playwright-cli -s=<app> click e15

# Stop trace recording (saves files)
playwright-cli -s=<app> tracing-stop
```

## What Traces Capture

| Category | Details |
|----------|---------|
| **Actions** | Clicks, fills, hovers, keyboard input, navigations |
| **DOM** | Full DOM snapshot before/after each action |
| **Screenshots** | Visual state at each step |
| **Network** | All HTTP requests, responses, headers, and full bodies |
| **Console** | All console.log, warn, error messages |
| **Timing** | Precise timing for each operation |

## Trace File Structure

This is the directory layout created by `tracing-stop`. Understanding this is critical for working with `parse-trace.py`.

```
.playwright-cli/traces/
├── trace-<id>.trace      # Action log (DOM snapshots, screenshots, timing)
├── trace-<id>.network    # HTTP requests/responses (HAR-format, one JSON per line)
├── trace-<id>.stacks     # Stack traces for debugging
└── resources/
    ├── <sha1>.json        # Response body files (full JSON/HTML)
    └── <sha1>.jpeg        # Screenshot captures
```

### The `.network` File Format

This is the file that `parse-trace.py` reads to extract API endpoints. Each line is a self-contained JSON object:

```json
{"type":"resource-snapshot","snapshot":{
  "request":{"method":"POST","url":"...","headers":[...],"postData":{"text":"..."}},
  "response":{"status":200,"headers":[...],"content":{"_sha1":"abc123.json","mimeType":"application/json"}},
  "time":150.5
}}
```

Key fields:
- `request.method` + `request.url` -- the API endpoint
- `request.postData.text` -- POST/PUT body (protobuf, JSON, form data)
- `response.content._sha1` -- points to `resources/<sha1>` containing the full response body
- `response.content.mimeType` -- tells you if the response is JSON, HTML, protobuf, etc.

### The `resources/` Directory

Response bodies are stored separately, referenced by SHA1 hash from the `.network` file. This is where you find the full JSON payloads that reveal the API structure.

## How It Connects to Our Pipeline

### Phase 1 Step 2 (Site Assessment — quick probe)
```bash
playwright-cli -s=<app> tracing-start
# Quick exploration: 3-4 clicks to discover API patterns
playwright-cli -s=<app> tracing-stop
# parse-trace.py --latest extracts endpoints for strategy selection
```

### Phase 1 Step 3 (Full Capture)
```bash
playwright-cli -s=<app> tracing-start
# Full user flow: login, browse, create, download
playwright-cli -s=<app> tracing-stop
# parse-trace.py extracts the complete API surface
```

### Phase 2 (Analyze)
The trace output from Phase 1 is the raw input for Phase 2. `parse-trace.py` reads the `.network` file and `resources/` directory to produce the endpoint catalog that drives CLI command design.

## Best Practices

### Always Stop Before Parsing

```bash
# WRONG: parsing while trace is still recording
playwright-cli -s=suno tracing-start
# ... interact ...
python parse-trace.py  # Incomplete data!

# RIGHT: stop first, then parse
playwright-cli -s=suno tracing-stop
python parse-trace.py --latest
```

Incomplete traces (where `tracing-stop` was never called) cannot be reliably parsed.

### Use `--latest` for the Most Recent Trace

Multiple traces accumulate in the `traces/` directory across sessions. Use `parse-trace.py --latest` to only read the most recent trace file.

### Clean Up Between Sessions

Traces consume significant disk space (full response bodies are stored):

```bash
rm -rf .playwright-cli/traces/
```

### Start Tracing Before the Interesting Part

Trace the entire flow, not just the failing or interesting step. Context from earlier requests (auth tokens, session setup) is often needed to understand later API calls.

---

## Trace Lifecycle Management

### Track active traces

Always note the trace ID returned by `tracing-start`:
```
Trace recording started
- [Action log](.playwright-cli/traces/trace-1774195355438.trace)
```
The ID is `trace-1774195355438`. Record this in the capture checkpoint.

### Trace Recovery Protocol

If `tracing-stop` fails:

1. **First failure** — retry once with 15s timeout
2. **Second failure** — the trace is lost (session likely reconnected and lost state)
3. **NEVER retry more than twice** — you'll waste time
4. **Recovery**: Run `tracing-start` again and re-do the exploration actions
5. The previous trace files may still be partially written in `.playwright-cli/traces/`
   but they won't have complete data — don't try to parse them

### Common trace errors

| Error | Cause | Fix |
|-------|-------|-----|
| "Cannot read properties of undefined (reading 'tracesDir')" | Session reconnected, lost trace state | Start new trace |
| `tracing-stop` hangs | Browser process died | `kill-all`, reopen, start fresh |
| `.network` file is empty | Trace was too short or no network activity | Re-do with more interactions |
| `.network` file missing | Trace didn't complete properly | Start new trace |

### One trace per purpose

Don't mix probe traces with capture traces. Use separate traces:
1. **Probe trace** (Step 2c): Short, 3-4 clicks, for API discovery
2. **Capture trace** (Step 3): Full exploration with all CRUD operations

Parse them separately. The capture trace is what feeds Phase 2.
