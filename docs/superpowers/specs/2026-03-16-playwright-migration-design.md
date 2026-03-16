# Playwright Migration Design

**Date:** 2026-03-16
**Status:** Approved
**Branch:** `playwright-migration` (experimental — revert to `master` if it doesn't work)

---

## Goal

Replace chrome-devtools-mcp as the primary browser automation and traffic capture
engine with `npx @playwright/cli@latest` (playwright-cli). Keep chrome-devtools-mcp
as an emergency fallback. No Playwright Python dependency anywhere.

---

## Why

| Problem with chrome-devtools-mcp | How playwright-cli fixes it |
|----------------------------------|----------------------------|
| Requires debug Chrome on port 9222 | playwright-cli manages its own browser |
| User must launch debug Chrome manually before each session | playwright-cli auto-launches with `open --headed --persistent` |
| MCP tools consume ~114k tokens per session | playwright-cli uses ~27k tokens (4x reduction) — data goes to disk files |
| `get_network_request` sometimes misses responses | Trace recording captures complete request/response bodies reliably |
| Agent falls back to claude-in-chrome (broken for traffic capture) | No MCP ambiguity — just Bash commands |
| Generated CLIs need `pip install playwright` (200MB Chromium) for `auth login` | `npx @playwright/cli state-save` — lightweight, no pip install |
| CDP cookie extraction has CookieMismatch issues | `state-save` produces clean Playwright storage state |

---

## Architecture

### Tool Hierarchy (strict priority)

```
1. playwright-cli (PRIMARY — try first, use for everything)
   ├── Browser control: open, snapshot, click, fill, screenshot
   ├── Traffic capture: tracing-start → browse → tracing-stop
   ├── Auth persistence: state-save / state-load
   └── Network inspection: network command

2. chrome-devtools-mcp (FALLBACK — only if playwright-cli fails)
   ├── Same capabilities but via MCP tools
   ├── Requires debug Chrome on port 9222
   └── Agent must explicitly tell user: "Falling back to MCP"

3. claude-in-chrome (NEVER — blocked, same as before)
```

### Development vs End-User

| | Development (Phases 1-8) | End-User (published CLI) |
|--|--------------------------|--------------------------|
| **Browser** | playwright-cli manages its own | playwright-cli via subprocess (only for `auth login`) |
| **Traffic capture** | `tracing-start` → `tracing-stop` → `parse-trace.py` | N/A — CLI uses httpx |
| **Auth** | `state-save` after user logs in | `auth login` → subprocess `state-save` → parse cookies |
| **Runtime HTTP** | N/A | `httpx` — no browser needed |
| **Dependencies** | `npx @playwright/cli` | `click`, `httpx`, `npx @playwright/cli` (auth only) |

---

## Phase 1 (Record) — New Flow

```bash
# 1. Open browser with named session
npx @playwright/cli@latest -s=<app> open <url> --headed --persistent

# 2. If first time: "Log in, then tell me when done." Wait for user.

# 3. Start trace recording
npx @playwright/cli@latest -s=<app> tracing-start

# 4. Agent explores the app:
npx @playwright/cli@latest -s=<app> snapshot           # → YAML with element refs
npx @playwright/cli@latest -s=<app> click e15           # Navigate
npx @playwright/cli@latest -s=<app> fill e8 "search"    # Fill forms
npx @playwright/cli@latest -s=<app> screenshot           # Visual check (file on disk)

# 5. Stop trace — saves .network + resources/ with full bodies
npx @playwright/cli@latest -s=<app> tracing-stop

# 6. Save auth state
npx @playwright/cli@latest -s=<app> state-save <app>-auth.json

# 7. Parse trace → raw-traffic.json
python ${CLAUDE_PLUGIN_ROOT}/scripts/parse-trace.py \
  .playwright-cli/traces/ \
  --output <app>/traffic-capture/raw-traffic.json

# 8. Close browser
npx @playwright/cli@latest -s=<app> close
```

### Trace File Structure (verified by research)

```
.playwright-cli/traces/
├── trace-<id>.trace      # Action log
├── trace-<id>.network    # HAR-format JSON: full request headers, response headers,
│                          # body SHA1 references → resources/
├── trace-<id>.stacks     # Stack traces
└── resources/
    ├── <sha1>.json        # Response body files (full JSON, HTML, etc.)
    └── <sha1>.jpeg        # Screenshot files
```

The `.network` file contains one JSON object per line in HAR format:
```json
{
  "type": "resource-snapshot",
  "snapshot": {
    "request": {"method": "POST", "url": "...", "headers": [...], "postData": {...}},
    "response": {"status": 200, "headers": [...], "content": {"_sha1": "abc123.json"}}
  }
}
```

The `_sha1` field points to the actual response body in `resources/`.

---

## Auth in Generated CLIs

The generated CLI's `auth login` command uses playwright-cli via subprocess:

```python
def login(app_url: str, auth_path: Path):
    """Open browser via playwright-cli, user logs in, save cookies."""
    import subprocess
    session = "auth-login"

    # Open browser
    subprocess.run(["npx", "@playwright/cli@latest", "-s=" + session,
                    "open", app_url, "--headed", "--persistent"], check=True)

    # Wait for user to log in
    input("Log in to the app in the browser, then press ENTER...")

    # Save state (cookies + localStorage)
    subprocess.run(["npx", "@playwright/cli@latest", "-s=" + session,
                    "state-save", str(auth_path)], check=True)

    # Close browser
    subprocess.run(["npx", "@playwright/cli@latest", "-s=" + session,
                    "close"], check=True)

    # Parse storage state → extract cookies for httpx
    state = json.loads(auth_path.read_text())
    cookies = {c["name"]: c["value"] for c in state.get("cookies", [])}
    save_cookies(cookies)
```

**CLI commands:**
```
cli-web-<app> auth login                # playwright-cli (primary)
cli-web-<app> auth login --cookies-json # manual import (fallback)
cli-web-<app> auth status               # show cookie validity
cli-web-<app> auth logout                # clear stored cookies
```

No more `--from-chrome` / `--from-browser` flags. Just `auth login` (playwright-cli) and `--cookies-json` (manual).

---

## New Script: `scripts/parse-trace.py`

Reads playwright trace files and produces `raw-traffic.json`:

- Input: `.playwright-cli/traces/` directory (after `tracing-stop`)
- Output: `raw-traffic.json` — array of request/response entries
- Filters: skips static assets (`.js`, `.css`, `.png`, fonts, etc.)
- Resolves `_sha1` references to load full response bodies from `resources/`
- Standalone script — no dependencies beyond Python stdlib + json

---

## Fallback: chrome-devtools-mcp

`.mcp.json` is kept but demoted:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest", "--browserUrl=http://127.0.0.1:9222"]
    }
  }
}
```

**When fallback activates:**
1. Agent tries `npx @playwright/cli@latest --version`
2. If it fails (no npm, network issue), agent says:
   "playwright-cli is not available. Falling back to chrome-devtools MCP.
   Please launch debug Chrome: `bash scripts/launch-chrome-debug.sh <url>`"
3. Agent uses `mcp__chrome-devtools__*` tools (same as current master behavior)

**Fallback scripts kept:** `scripts/launch-chrome-debug.sh`, `scripts/extract-browser-cookies.py`

---

## Command Priority Logic

In `commands/cli-anything-web.md` and `commands/record.md`:

```
Step 1: Check playwright-cli availability
  !`npx @playwright/cli@latest --version`

  IF SUCCESS → use playwright-cli for all Phase 1 operations
  IF FAIL → fall back to chrome-devtools-mcp:
    - Tell user: "playwright-cli not available, falling back to chrome-devtools MCP"
    - Launch debug Chrome: !`bash scripts/launch-chrome-debug.sh <url>`
    - If MCP not connected: tell user to /mcp → Reconnect
    - Use mcp__chrome-devtools__* tools

NEVER use mcp__claude-in-chrome__* — blocked, same as before
```

---

## Complete File Inventory

| File | Action | Details |
|------|--------|---------|
| `.mcp.json` | Keep | Demoted to fallback. Add comment. |
| `HARNESS.md` | Major update | Prerequisites → playwright-cli; Phase 1 → trace-based; Two Chromes → simplified; Auth → state-save |
| `commands/cli-anything-web.md` | Major update | playwright-cli primary flow; MCP fallback logic; allowed-tools keeps both |
| `commands/record.md` | Major update | Same as cli-anything-web.md |
| `commands/refine.md` | Minor update | Update Phase 1 references |
| `commands/test.md` | Minor update | Auth verification uses `auth login` (playwright-cli) |
| `commands/validate.md` | Minor update | Add `npx @playwright/cli --version` check |
| `commands/list.md` | No change | No chrome-devtools references |
| `commands/web-harness.md` | No change | Legacy file, no chrome-devtools references |
| `skills/cli-anything-web-methodology/SKILL.md` | Minor update | Mention playwright-cli |
| `skills/cli-anything-web-testing/SKILL.md` | Minor update | Update auth flow |
| `skills/cli-anything-web-standards/SKILL.md` | Minor update | Add playwright-cli prerequisite |
| `skills/cli-anything-web-methodology/references/auth-strategies.md` | Update | Add `state-save`/`state-load` as primary pattern |
| `scripts/parse-trace.py` | **NEW** | Parse trace `.network` + `resources/` → `raw-traffic.json` |
| `scripts/launch-chrome-debug.sh` | Keep | For MCP fallback |
| `scripts/extract-browser-cookies.py` | Keep | Legacy utility |
| `scripts/setup.sh` | Update | Check npx exists |
| `README.md` | Update | Simplified Quick Start |
| `QUICKSTART.md` | Update | playwright-cli flow |
| `verify-plugin.sh` | Update | Add playwright-cli check |

---

## What Does NOT Change

- 8-phase pipeline structure
- Generated CLI structure (cli_web namespace, setup.py, etc.)
- 3 skills (methodology, testing, standards)
- ReplSkin
- 50-check validation framework (minor additions only)
- Content generation download pattern
- CAPTCHA handling pattern
- Parallel subagent dispatch in Phase 4+6
- `_resolve_cli` pattern
- TEST.md two-part structure
- Google batchexecute reference
- Traffic patterns reference (existing content)

---

## Out of Scope

- Building a Suno showcase (separate branch after migration verified)
- Changes to existing generated CLIs (notebooklm, futbin)
- Playwright Python dependency anywhere
- Deleting `.mcp.json`
