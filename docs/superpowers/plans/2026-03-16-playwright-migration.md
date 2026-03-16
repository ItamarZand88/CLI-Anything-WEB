# Playwright Migration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace chrome-devtools-mcp with playwright-cli as the primary browser automation and traffic capture engine, keeping MCP as emergency fallback.

**Architecture:** All browser interaction moves from MCP tool calls to `npx @playwright/cli@latest` via Bash. Traffic capture uses `tracing-start`/`tracing-stop` with a new `parse-trace.py` script. Auth in generated CLIs uses `state-save` via subprocess. `.mcp.json` kept as fallback only.

**Tech Stack:** `@playwright/cli` (npm), Python stdlib (parse-trace.py), Bash

**Spec:** `docs/superpowers/specs/2026-03-16-playwright-migration-design.md`

**Branch:** `playwright-migration`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `scripts/parse-trace.py` | **CREATE** | Parse playwright trace files → raw-traffic.json |
| `HARNESS.md` | Major edit | Prerequisites, Phase 1, Two Chromes, Auth |
| `commands/cli-anything-web.md` | Major edit | playwright-cli primary, MCP fallback |
| `commands/record.md` | Major edit | Same |
| `commands/refine.md` | Minor edit | Phase 1 reference |
| `commands/test.md` | Minor edit | Auth verification |
| `commands/validate.md` | Minor edit | playwright-cli check |
| `skills/*/SKILL.md` (3 files) | Minor edit | Mention playwright-cli |
| `references/auth-strategies.md` | Edit | state-save pattern |
| `scripts/setup.sh` | Edit | Check npx |
| `README.md` | Edit | Simplified Quick Start |
| `QUICKSTART.md` | Edit | playwright-cli flow |
| `verify-plugin.sh` | Edit | Add playwright-cli check |

---

## Chunk 1: Foundation (parse-trace.py + HARNESS.md)

### Task 1: Create scripts/parse-trace.py

**Files:**
- Create: `cli-anything-web-plugin/scripts/parse-trace.py`

- [ ] **Step 1: Write parse-trace.py**

```python
#!/usr/bin/env python3
"""Parse Playwright trace files into raw-traffic.json format.

Reads .network files and resources/ from a playwright-cli trace directory
and produces a filtered JSON array of API request/response entries.

Usage:
    python parse-trace.py <traces-dir> --output raw-traffic.json
    python parse-trace.py .playwright-cli/traces/ --output suno/traffic-capture/raw-traffic.json
    python parse-trace.py .playwright-cli/traces/ --output raw.json --include-static
"""

import argparse
import json
import sys
from pathlib import Path


# Static asset extensions to filter out by default
STATIC_EXTENSIONS = (
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".map", ".webp", ".avif",
)

# Resource types to keep (API traffic)
API_RESOURCE_TYPES = ("xhr", "fetch", "websocket", "other")


def parse_network_file(network_path: Path, resources_dir: Path, filter_static: bool = True) -> list[dict]:
    """Parse a single .network trace file into request/response entries."""
    entries = []
    text = network_path.read_text(encoding="utf-8").strip()
    if not text:
        return entries

    for line in text.split("\n"):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        if data.get("type") != "resource-snapshot":
            continue

        snap = data["snapshot"]
        req = snap.get("request", {})
        resp = snap.get("response", {})
        url = req.get("url", "")

        # Filter static assets
        if filter_static:
            url_path = url.split("?")[0].split("#")[0]
            if any(url_path.endswith(ext) for ext in STATIC_EXTENSIONS):
                continue

        # Load response body from resources/
        body = None
        sha1 = resp.get("content", {}).get("_sha1")
        if sha1 and resources_dir.exists():
            body_file = resources_dir / sha1
            if body_file.exists():
                try:
                    body = json.loads(body_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    try:
                        body = body_file.read_text(encoding="utf-8")[:3000]
                    except Exception:
                        body = "[binary content]"

        # Build entry
        entries.append({
            "url": url,
            "method": req.get("method", "GET"),
            "request_headers": {
                h["name"]: h["value"]
                for h in req.get("headers", [])
            },
            "post_data": req.get("postData", {}).get("text") if isinstance(req.get("postData"), dict) else req.get("postData"),
            "status": resp.get("status", 0),
            "response_headers": {
                h["name"]: h["value"]
                for h in resp.get("headers", [])
            },
            "response_body": body,
            "mime_type": resp.get("content", {}).get("mimeType", ""),
            "time_ms": round(snap.get("time", 0), 1),
        })

    return entries


def parse_traces(traces_dir: Path, filter_static: bool = True) -> list[dict]:
    """Parse all .network files in a traces directory."""
    traces_dir = Path(traces_dir)
    resources_dir = traces_dir / "resources"

    all_entries = []
    for network_file in sorted(traces_dir.glob("*.network")):
        entries = parse_network_file(network_file, resources_dir, filter_static)
        all_entries.extend(entries)

    return all_entries


def main():
    parser = argparse.ArgumentParser(
        description="Parse Playwright trace files into raw-traffic.json"
    )
    parser.add_argument(
        "traces_dir",
        help="Path to .playwright-cli/traces/ directory",
    )
    parser.add_argument(
        "--output", "-o",
        default="raw-traffic.json",
        help="Output file path (default: raw-traffic.json)",
    )
    parser.add_argument(
        "--include-static",
        action="store_true",
        help="Include static assets (JS, CSS, images) — filtered by default",
    )
    args = parser.parse_args()

    traces_dir = Path(args.traces_dir)
    if not traces_dir.exists():
        print(f"Error: traces directory not found: {traces_dir}", file=sys.stderr)
        sys.exit(1)

    entries = parse_traces(traces_dir, filter_static=not args.include_static)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(entries, indent=2, default=str), encoding="utf-8")

    print(f"Parsed {len(entries)} API requests → {output_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify it runs**

```bash
cd cli-anything-web-plugin && python scripts/parse-trace.py --help
```
Expected: help text prints without errors.

- [ ] **Step 3: Commit**

```bash
git add cli-anything-web-plugin/scripts/parse-trace.py
git commit -m "feat: add parse-trace.py for playwright trace → raw-traffic.json"
```

---

### Task 2: Update HARNESS.md — Prerequisites + Two Chromes + Phase 1

**Files:**
- Modify: `cli-anything-web-plugin/HARNESS.md`

- [ ] **Step 1: Replace "Two Chromes" section (lines 34-61)**

Replace the entire "Two Chromes: Development vs End-User" section with:

```markdown
## Browser Automation: playwright-cli

The plugin uses `npx @playwright/cli@latest` (playwright-cli) for all browser
interaction and traffic capture. This is a CLI tool — the agent calls it via Bash,
not through MCP. Data (snapshots, screenshots, traces) goes to files on disk,
keeping context usage ~4x lower than MCP-based approaches.

### Tool Hierarchy (strict priority)

| Priority | Tool | When to use |
|----------|------|-------------|
| 1. PRIMARY | `npx @playwright/cli@latest` via Bash | Always try first |
| 2. FALLBACK | `mcp__chrome-devtools__*` MCP tools | Only if playwright-cli unavailable |
| 3. NEVER | `mcp__claude-in-chrome__*` | Blocked — cannot capture request bodies |

### Development vs End-User

| | Development (Phases 1-8) | End-User (published CLI) |
|--|--------------------------|--------------------------|
| **Browser** | playwright-cli manages its own | playwright-cli via subprocess (auth only) |
| **Traffic capture** | `tracing-start` → browse → `tracing-stop` | N/A — CLI uses httpx |
| **Auth** | `state-save` after user logs in | `auth login` → subprocess `state-save` → parse cookies |
| **Runtime HTTP** | N/A | httpx — no browser needed |
| **Dependencies** | Node.js + npx | click, httpx, Node.js + npx (auth only) |

**The generated CLI MUST work standalone.** playwright-cli is only needed during
`auth login` — all regular commands use httpx. If the CLI requires a browser for
normal operations, it's broken.
```

- [ ] **Step 2: Replace Prerequisites section (lines 66-75)**

Replace from `### Prerequisites — Chrome Debug Profile (Development Only)` through the 3 setup steps with:

```markdown
### Prerequisites

**Primary: playwright-cli (recommended)**

playwright-cli auto-launches and manages its own browser. No manual setup needed.
Just verify Node.js and npx are available:
```bash
npx @playwright/cli@latest --version
```
If this fails, install Node.js from https://nodejs.org/

**Fallback: Chrome Debug Profile (if playwright-cli unavailable)**

If playwright-cli cannot be used, fall back to chrome-devtools-mcp:
1. Launch: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/launch-chrome-debug.sh <url>`
2. Log into the target web app (cookies persist across restarts)
3. Agent uses `mcp__chrome-devtools__*` tools instead
```

- [ ] **Step 3: Replace Phase 1 Record section**

Replace the current Phase 1 content (from `### Phase 1 — Record (Traffic Capture)` through the end of the phase) with:

```markdown
### Phase 1 — Record (Traffic Capture)

**Goal:** Capture comprehensive HTTP traffic from the target web app.

**Primary method: playwright-cli**

```bash
# 1. Open browser with named session
npx @playwright/cli@latest -s=<app> open <url> --headed --persistent

# 2. If login required — ask user to log in, wait for confirmation

# 3. Start trace recording (captures ALL network with full bodies)
npx @playwright/cli@latest -s=<app> tracing-start

# 4. Systematically explore the app:
npx @playwright/cli@latest -s=<app> snapshot          # Get element refs (YAML)
npx @playwright/cli@latest -s=<app> click e15          # Navigate
npx @playwright/cli@latest -s=<app> fill e8 "search"   # Fill forms
npx @playwright/cli@latest -s=<app> screenshot          # Visual check (file on disk)

# 5. Stop trace — saves .network + resources/ with full request/response bodies
npx @playwright/cli@latest -s=<app> tracing-stop

# 6. Save auth state for reuse
npx @playwright/cli@latest -s=<app> state-save <app>-auth.json

# 7. Parse trace → raw-traffic.json
python ${CLAUDE_PLUGIN_ROOT}/scripts/parse-trace.py \
  .playwright-cli/traces/ \
  --output <app>/traffic-capture/raw-traffic.json

# 8. Close browser
npx @playwright/cli@latest -s=<app> close
```

**Fallback method: chrome-devtools-mcp**

If playwright-cli is not available, tell the user:
"playwright-cli is not available. Falling back to chrome-devtools MCP.
Please launch debug Chrome: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/launch-chrome-debug.sh <url>`"

Then use `mcp__chrome-devtools__*` tools:
- `navigate_page` with the target URL
- `list_network_requests` to capture traffic
- `get_network_request(id)` for full request/response details
- Save to `<app>/traffic-capture/raw-traffic.json`

**Critical rules (both methods):**
- Filter OUT: static assets (.js, .css, .png, fonts, analytics, CDN)
- Filter IN: API calls (JSON responses, `/api/`, GraphQL, RPC endpoints)
- Capture auth tokens/cookies for session management design
- Record the user action that triggered each request group
```

- [ ] **Step 4: Update Phase 4 auth section**

Find the auth.py guidance in Phase 4 (the 3 login methods section). Replace the 3 methods with 2:

```markdown
- `auth.py` — handles token storage, refresh, expiry. MUST support 2 login methods:
  1. **`auth login`** (primary) — uses playwright-cli via subprocess to open browser.
     User logs in manually, `state-save` captures cookies + localStorage.
     No Playwright Python needed — just `npx @playwright/cli`.
     ```python
     # auth.py — playwright-cli login
     def login(app_url, auth_path):
         import subprocess
         session = "auth-login"
         subprocess.run(["npx", "@playwright/cli@latest", "-s=" + session,
                         "open", app_url, "--headed", "--persistent"], check=True)
         input("Log in, then press ENTER...")
         subprocess.run(["npx", "@playwright/cli@latest", "-s=" + session,
                         "state-save", str(auth_path)], check=True)
         subprocess.run(["npx", "@playwright/cli@latest", "-s=" + session,
                         "close"], check=True)
         state = json.loads(auth_path.read_text())
         cookies = {c["name"]: c["value"] for c in state.get("cookies", [])}
         save_cookies(cookies)
     ```
  2. **`auth login --cookies-json <file>`** (manual fallback) — import from JSON file.
  - Store cookies at `~/.config/cli-web-<app>/auth.json` with chmod 600
  - No more `--from-chrome` or `--from-browser` flags
  - `setup.py` should NOT include Playwright Python — only `click`, `httpx`
```

- [ ] **Step 5: Verify HARNESS.md is valid markdown**

```bash
wc -l cli-anything-web-plugin/HARNESS.md
```
Expected: file exists and has content.

- [ ] **Step 6: Commit**

```bash
git add cli-anything-web-plugin/HARNESS.md
git commit -m "docs: migrate HARNESS.md to playwright-cli primary with MCP fallback

Replace Two Chromes section with playwright-cli tool hierarchy.
Phase 1 now uses tracing-start/stop + parse-trace.py.
Auth simplified to 2 methods: playwright-cli state-save + manual JSON.
MCP kept as fallback only."
```

---

## Chunk 2: Commands (cli-anything-web.md + record.md + minor updates)

### Task 3: Update commands/cli-anything-web.md

**Files:**
- Modify: `cli-anything-web-plugin/commands/cli-anything-web.md`

- [ ] **Step 1: Update allowed-tools in frontmatter**

Change line 5 from:
```
allowed-tools: Bash(*), Read, Write, Edit, mcp__chrome-devtools__*
```
To:
```
allowed-tools: Bash(*), Read, Write, Edit, mcp__chrome-devtools__*
```
(Keep MCP in allowed-tools for fallback — but the body makes playwright-cli primary.)

- [ ] **Step 2: Replace the entire Prerequisites Check section**

Replace from `## Prerequisites Check` through `!`which npx`` with:

```markdown
## Prerequisites Check

### Step 1: Check playwright-cli availability
!`npx @playwright/cli@latest --version 2>&1 && echo "PLAYWRIGHT_OK" || echo "PLAYWRIGHT_FAIL"`

**If PLAYWRIGHT_OK** → use playwright-cli for all operations (primary path).

**If PLAYWRIGHT_FAIL** → fall back to chrome-devtools MCP:
- Tell user: "playwright-cli not available. Falling back to chrome-devtools MCP."
- Launch debug Chrome: !`bash "${CLAUDE_PLUGIN_ROOT}/scripts/launch-chrome-debug.sh" $ARGUMENTS`
- If first time, ask user to log in. Wait for confirmation.
- If MCP not connected, tell user: "Type `/mcp`, find **chrome-devtools**, click **Reconnect**."
- Use `mcp__chrome-devtools__*` tools for all operations.

### NEVER use `mcp__claude-in-chrome__*` tools — blocked, cannot capture request bodies.
```

- [ ] **Step 3: Replace Phase 1 section in the command**

Replace the current Phase 1 content with:

```markdown
### Phase 1 — Record (Traffic Capture)

**If playwright-cli available (primary):**
1. Open browser: `npx @playwright/cli@latest -s=<app> open $ARGUMENTS --headed --persistent`
2. If login needed — ask user to log in, wait for confirmation
3. Start trace: `npx @playwright/cli@latest -s=<app> tracing-start`
4. Systematically explore: use `snapshot`, `click`, `fill`, `screenshot` commands
5. Stop trace: `npx @playwright/cli@latest -s=<app> tracing-stop`
6. Save auth: `npx @playwright/cli@latest -s=<app> state-save <app>-auth.json`
7. Parse: `python ${CLAUDE_PLUGIN_ROOT}/scripts/parse-trace.py .playwright-cli/traces/ --output <app>/traffic-capture/raw-traffic.json`
8. Close: `npx @playwright/cli@latest -s=<app> close`

**If MCP fallback:**
1. Verify debug Chrome on port 9222
2. Use `mcp__chrome-devtools__*` tools: `navigate_page`, `list_network_requests`, `get_network_request`
3. Save to `<app>/traffic-capture/raw-traffic.json`
```

- [ ] **Step 4: Update Phase 8 smoke test auth**

Find the Phase 8 smoke test section. Replace `auth login` references to clarify playwright-cli:

```markdown
5. **Authenticate as an end user would:**
   ```bash
   cli-web-<app> auth login
   ```
   This uses playwright-cli via subprocess — opens a browser, user logs in,
   cookies saved. No debug Chrome, no MCP, no special setup.
```

- [ ] **Step 5: Commit**

```bash
git add cli-anything-web-plugin/commands/cli-anything-web.md
git commit -m "feat: update cli-anything-web command for playwright-cli primary"
```

---

### Task 4: Update commands/record.md

**Files:**
- Modify: `cli-anything-web-plugin/commands/record.md`

- [ ] **Step 1: Replace Prerequisites and Process sections**

Replace everything after the `@${CLAUDE_PLUGIN_ROOT}/HARNESS.md` line with:

```markdown
## Prerequisites

### Step 1: Check playwright-cli availability
!`npx @playwright/cli@latest --version 2>&1 && echo "PLAYWRIGHT_OK" || echo "PLAYWRIGHT_FAIL"`

**If PLAYWRIGHT_OK** → use playwright-cli for recording.

**If PLAYWRIGHT_FAIL** → fall back to chrome-devtools MCP:
- Tell user: "playwright-cli not available. Falling back to chrome-devtools MCP."
- Launch debug Chrome: !`bash "${CLAUDE_PLUGIN_ROOT}/scripts/launch-chrome-debug.sh" $ARGUMENTS`
- If MCP not connected: tell user to `/mcp` → Reconnect
- Use `mcp__chrome-devtools__*` tools

### NEVER use `mcp__claude-in-chrome__*` tools — blocked.

## Process

This command runs Phase 1 only — traffic recording without CLI generation.
Useful for:
- Initial exploration of an unfamiliar web app
- Adding more traffic data before refining
- Recording specific workflows

**If playwright-cli available (primary):**
1. Open browser: `npx @playwright/cli@latest -s=<app> open $ARGUMENTS --headed --persistent`
2. If login needed — ask user to log in, wait for confirmation
3. Start trace: `npx @playwright/cli@latest -s=<app> tracing-start`
4. Systematically explore: use `snapshot`, `click`, `fill`, `screenshot`
5. Stop trace: `npx @playwright/cli@latest -s=<app> tracing-stop`
6. Save auth: `npx @playwright/cli@latest -s=<app> state-save <app>-auth.json`
7. Parse: `python ${CLAUDE_PLUGIN_ROOT}/scripts/parse-trace.py .playwright-cli/traces/ --output <app>/traffic-capture/raw-traffic.json`
8. Close: `npx @playwright/cli@latest -s=<app> close`
9. Print summary: total requests captured, endpoints discovered

**If MCP fallback:**
1. Verify debug Chrome on port 9222
2. `navigate_page` with target URL
3. `list_network_requests` + `get_network_request` for traffic
4. Save to `<app>/traffic-capture/raw-traffic.json`

## Interactive Mode

Ask the user at each major section:
- "I see a boards section. Should I explore it? (create/read/update/delete)"
- "I found a settings area. Should I capture these endpoints too?"

This gives the user control over what gets recorded.
```

- [ ] **Step 2: Commit**

```bash
git add cli-anything-web-plugin/commands/record.md
git commit -m "feat: update record command for playwright-cli primary"
```

---

### Task 5: Minor command updates (refine, test, validate)

**Files:**
- Modify: `cli-anything-web-plugin/commands/refine.md`
- Modify: `cli-anything-web-plugin/commands/test.md`
- Modify: `cli-anything-web-plugin/commands/validate.md`

- [ ] **Step 1: Update refine.md**

In the Process section, step 5 says "Record new traffic: Open Chrome DevTools". Change to:
"Record new traffic: Use playwright-cli (or chrome-devtools-mcp fallback) — see HARNESS.md Phase 1"

- [ ] **Step 2: Update test.md auth section**

Replace the auth verification step that mentions `--from-chrome` with:
```
cli-web-<app> auth login              # playwright-cli (recommended)
cli-web-<app> auth login --cookies-json <file>  # manual fallback
cli-web-<app> auth status
```
Remove references to "Chrome debug profile" and "port 9222".

- [ ] **Step 3: Update validate.md**

Add to the Category 1 checks (or a new prerequisite check):
```
- [ ] `npx @playwright/cli@latest --version` succeeds (playwright-cli available)
```

- [ ] **Step 4: Commit**

```bash
git add cli-anything-web-plugin/commands/refine.md cli-anything-web-plugin/commands/test.md cli-anything-web-plugin/commands/validate.md
git commit -m "docs: update refine, test, validate commands for playwright-cli"
```

---

## Chunk 3: Skills, References, Infrastructure

### Task 6: Update skills (methodology, testing, standards)

**Files:**
- Modify: `cli-anything-web-plugin/skills/cli-anything-web-methodology/SKILL.md`
- Modify: `cli-anything-web-plugin/skills/cli-anything-web-testing/SKILL.md`
- Modify: `cli-anything-web-plugin/skills/cli-anything-web-standards/SKILL.md`

- [ ] **Step 1: Update methodology SKILL.md**

In the description field or body, replace any "Chrome DevTools MCP" or "chrome-devtools-mcp" references with "playwright-cli". Add a note that playwright-cli is the primary browser automation tool.

- [ ] **Step 2: Update testing SKILL.md**

Replace auth flow references:
- `auth login --from-chrome` → `auth login` (playwright-cli)
- "Chrome debug profile" → "playwright-cli session"
- "port 9222" → remove
- "CDP via websockets" → "playwright-cli state-save"

- [ ] **Step 3: Update standards SKILL.md**

Add to Key Rules: "playwright-cli is the primary browser tool — check `npx @playwright/cli --version` in validation"

- [ ] **Step 4: Commit**

```bash
git add cli-anything-web-plugin/skills/
git commit -m "docs: update all 3 skills for playwright-cli"
```

---

### Task 7: Update auth-strategies.md

**Files:**
- Modify: `cli-anything-web-plugin/skills/cli-anything-web-methodology/references/auth-strategies.md`

- [ ] **Step 1: Add playwright-cli state-save as primary pattern**

In the "Browser-Delegated Auth" section, replace the CDP Phase A with:

```markdown
**Phase A — Session capture via playwright-cli (primary):**
```python
# During development (Phase 1 recording)
npx @playwright/cli@latest -s=<app> state-save <app>-auth.json

# In generated CLI's auth login command
import subprocess
subprocess.run(["npx", "@playwright/cli@latest", "-s=auth",
                "open", app_url, "--headed", "--persistent"], check=True)
input("Log in, then press ENTER...")
subprocess.run(["npx", "@playwright/cli@latest", "-s=auth",
                "state-save", str(auth_path)], check=True)
subprocess.run(["npx", "@playwright/cli@latest", "-s=auth",
                "close"], check=True)
# Parse storage state → extract cookies for httpx
state = json.loads(auth_path.read_text())
cookies = {c["name"]: c["value"] for c in state.get("cookies", [])}
```

Keep the CDP option as "Legacy fallback" and the manual JSON import.

- [ ] **Step 2: Commit**

```bash
git add cli-anything-web-plugin/skills/cli-anything-web-methodology/references/auth-strategies.md
git commit -m "docs: add playwright-cli state-save as primary auth pattern"
```

---

### Task 8: Update infrastructure (setup.sh, verify-plugin.sh, README, QUICKSTART, .mcp.json)

**Files:**
- Modify: `cli-anything-web-plugin/.mcp.json`
- Modify: `cli-anything-web-plugin/scripts/setup.sh`
- Modify: `cli-anything-web-plugin/verify-plugin.sh`
- Modify: `cli-anything-web-plugin/README.md`
- Modify: `cli-anything-web-plugin/QUICKSTART.md`

- [ ] **Step 0: Demote .mcp.json to fallback-only**

The `.mcp.json` stays but the agent should understand it's a fallback. The JSON format
doesn't support comments, so this is communicated via the HARNESS.md and commands.
Verify the file still has the correct config:

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

No code change needed — the demotion is enforced by the command files and HARNESS.md
which now say "playwright-cli first, MCP fallback only."

- [ ] **Step 1: Update setup.sh**

Add playwright-cli check alongside existing npx check:
```bash
# Check playwright-cli
if npx @playwright/cli@latest --version > /dev/null 2>&1; then
    echo -e "  ${GREEN}playwright-cli: $(npx @playwright/cli@latest --version)${NC}"
else
    echo -e "  ${YELLOW}playwright-cli: not cached (will download on first use via npx)${NC}"
fi
```

- [ ] **Step 2: Update verify-plugin.sh**

Add a check for parse-trace.py:
```bash
check "scripts/parse-trace.py exists" "$([ -f "$SCRIPT_DIR/scripts/parse-trace.py" ] && echo true || echo false)"
```

- [ ] **Step 3: Update README.md Quick Start**

Replace the 3-step Quick Start with:
```markdown
### Step 1: Load the plugin

```bash
claude --plugin-dir /path/to/cli-anything-web-plugin
```

### Step 2: Generate a CLI

```bash
/cli-anything-web https://monday.com
```

playwright-cli auto-launches a browser. Log in when prompted. The agent captures
traffic, analyzes the API, and generates a complete CLI — all in one command.
```

- [ ] **Step 4: Update QUICKSTART.md**

Replace Step 1 (debug Chrome setup) with:
```markdown
## Step 1: Prerequisites (30 seconds)

Verify Node.js is installed (needed for playwright-cli):
```bash
npx @playwright/cli@latest --version
```
If this fails, install Node.js from https://nodejs.org/
```

Remove all "debug Chrome" references from the quickstart flow.

- [ ] **Step 5: Commit**

```bash
git add cli-anything-web-plugin/scripts/setup.sh cli-anything-web-plugin/verify-plugin.sh cli-anything-web-plugin/README.md cli-anything-web-plugin/QUICKSTART.md
git commit -m "feat: update infrastructure for playwright-cli (setup, verify, README, QUICKSTART)"
```

---

### Task 9: Final Verification

- [ ] **Step 1: Run verify-plugin.sh**

```bash
cd cli-anything-web-plugin && bash verify-plugin.sh
```
Expected: all checks pass (including new parse-trace.py check).

- [ ] **Step 2: Grep for stale chrome-devtools-as-primary references**

```bash
cd cli-anything-web-plugin && grep -rn "debug Chrome" --include="*.md" . | grep -iv "fallback\|legacy\|if playwright"
```
Expected: 0 matches (all remaining debug Chrome refs are in fallback context).

- [ ] **Step 3: Verify playwright-cli works**

```bash
npx @playwright/cli@latest --version
```
Expected: version number prints.

- [ ] **Step 4: Verify parse-trace.py runs**

```bash
python cli-anything-web-plugin/scripts/parse-trace.py --help
```
Expected: help text prints.

- [ ] **Step 5: Commit any fixes, then tag**

```bash
git log --oneline playwright-migration --not master
```
Review all commits on the branch.
