# Web-Harness Plugin Refactor Design

**Date:** 2026-03-15
**Status:** Approved

---

## Goal

Refactor the `cli-anything-web-plugin` to match the standards, patterns, and
quality of the `cli-anything-plugin` (the reference project). The two plugins
are sister projects — web-harness extends cli-anything's methodology to web
apps. They should feel like a unified family.

---

## MCP Tool Name Corrections

chrome-devtools-mcp auto-launches Chrome on first tool call — no explicit
connect step is needed. All references to the old phantom function must be
replaced.

| Old (broken) | Correct |
|---|---|
| `start_chrome_and_connect` | *(remove — auto-connects on first call)* |
| `execute_javascript` | `evaluate_script` |
| `list_network_requests` | `list_network_requests` (already correct) |
| `get_network_request(id)` | `get_network_request` (already correct) |

**Affected files:** `WEB-HARNESS.md`, `commands/web-harness.md`, `commands/record.md`

### Why chrome-devtools-mcp (not claude-in-chrome)

claude-in-chrome provides only basic network monitoring — no request/response
body capture. chrome-devtools-mcp provides full body + header access, which is
required to map an app's API surface. Auth is handled by having the user log
in manually at the start of each recording session (supervised sessions, so
this is a 30-second step, not real friction).

---

## Command Structure Alignment

Every cli-anything command begins with a "CRITICAL: Read HARNESS.md First"
gate. Web-harness commands must adopt the same pattern with WEB-HARNESS.md.

### Changes per command file

| File | Change |
|------|--------|
| `commands/web-harness.md` | Add CRITICAL header + fix tool names |
| `commands/record.md` | Add CRITICAL header + fix tool names |
| `commands/refine.md` | Add CRITICAL header |
| `commands/test.md` | Add CRITICAL header |
| `commands/validate.md` | Add CRITICAL header |
| `commands/list.md` | **New** — `web-harness:list` command |

### New: web-harness:list

Equivalent to `cli-anything:list`. Scans for installed and generated
`cli-web-*` packages by:
- Using `importlib.metadata` to find packages starting with `cli-web-`
- Using glob to find local `**/agent-harness/cli_web/*/__init__.py`
- Merging results, outputting table or `--json`

---

## WEB-HARNESS.md Phase 1 Update

Current (broken):
```
1. Open Chrome via DevTools MCP (start_chrome_and_connect)
2. Navigate to target URL
```

New (correct):
```
1. chrome-devtools-mcp auto-launches Chrome on first tool call — no setup needed
2. Call navigate_page with the target URL
3. If login required — pause and ask user to log in manually
4. Enable network monitoring (list_network_requests)
```

Also update `execute_javascript` → `evaluate_script` throughout.

---

## Cleanup

- **Delete** the bogus `skills/web-harness-methodology/{references,scripts}/`
  directory only — this is a literal directory whose name is the unexpanded
  glob string `{references,scripts}`. The real `references/` directory
  (containing `auth-strategies.md` and `traffic-patterns.md`) must NOT be
  touched.
- **Add** `PUBLISHING.md` — same structure as cli-anything's but for
  `cli-web-*` packages and the `cli_web.*` namespace
- **Update** `QUICKSTART.md` — remove fake marketplace reference, use manual
  install instructions matching cli-anything's QUICKSTART pattern
- **Update** `scripts/setup-web-harness.sh` — add Windows bash/cygpath
  detection (matching cli-anything's setup script), fix fragile copy logic

---

## Complete File Inventory

| File | Action |
|------|--------|
| `WEB-HARNESS.md` | Update Phase 1 tool names + `evaluate_script` |
| `commands/web-harness.md` | CRITICAL header + tool name fixes |
| `commands/record.md` | CRITICAL header + tool name fixes |
| `commands/refine.md` | Add CRITICAL header |
| `commands/test.md` | Add CRITICAL header |
| `commands/validate.md` | Add CRITICAL header |
| `commands/list.md` | New file |
| `QUICKSTART.md` | Fix install instructions |
| `PUBLISHING.md` | New file |
| `scripts/setup-web-harness.sh` | Windows detection + copy fix |
| `skills/web-harness-methodology/{references,scripts}/` | Delete (bogus literal dir only) |

---

## Out of Scope

- Changes to `WEB-HARNESS.md` methodology (phases 2–7 are correct)
- Changes to `skills/web-harness-methodology/references/` content
- Changes to `.claude-plugin/plugin.json` (already has more fields than cli-anything's — keep it)
- Changes to `.mcp.json` (already correctly configured for chrome-devtools-mcp)
