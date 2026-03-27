---
name: gap-analyzer
version: 0.1.0
description: >
  Compare implemented CLI commands against <APP>.md API map to find missing
  endpoints, incomplete CRUD, dead client methods, and priority gaps.
  TRIGGER when: "gap analysis", "what's missing", "coverage report",
  "what endpoints are not implemented", or as a sub-step of the refine workflow.
  DO NOT trigger for: "refine" alone (use the /cli-anything-web:refine command).
---

# CLI Gap Analyzer

Produce a structured gap report comparing a CLI's documented API surface
against its implemented commands. Used during `/refine` workflows and
standalone coverage analysis.

---

## Inputs

You need the path to an existing CLI's agent-harness directory:
- `{APP_PATH}/agent-harness/` — the CLI root
- `{app}` — the app name (e.g., `reddit`, `hackernews`)

## Step 1: Parse Implemented Surface

Read all source files to build the set of implemented functionality:

### 1a. Extract Click commands

Read all files in `{APP_PATH}/agent-harness/cli_web/{app}/commands/`:
- For each file, find `@click.command()` and `@<group>.command()` decorators
- Extract: command group name, subcommand name, arguments, options
- Build list: `[(group, subcommand, [args], [options])]`

### 1b. Extract client methods

Read `{APP_PATH}/agent-harness/cli_web/{app}/core/client.py`:
- Find all public methods (not starting with `_`)
- For each method, note: name, HTTP method used (GET/POST/etc), URL pattern
- Build list: `[(method_name, http_verb, url_pattern)]`

### 1c. Map commands to client methods

For each Click command, trace which client method it calls:
- Read the command function body
- Find `client.method_name()` calls
- Build mapping: `{command: client_method}`

## Step 2: Parse Documented Surface

Read `{APP_PATH}/agent-harness/{APP_UPPER}.md` (the API map):
- Find the endpoint inventory section
- Extract each documented endpoint: resource group, HTTP method, URL, params, description
- Build list: `[(resource, http_verb, url, params, description)]`

## Step 3: Diff

Compare implemented vs documented:

### Missing Commands
Endpoints in `<APP>.md` that have no corresponding Click command:
```
For each documented endpoint:
  Find matching client method (by URL pattern or method name)
  Find matching Click command (that calls this client method)
  If no command found → MISSING
```

### Undocumented Commands
Click commands that call client methods not documented in `<APP>.md`:
```
For each Click command:
  Find the client method it calls
  Find the endpoint in <APP>.md for this method
  If no endpoint found → UNDOCUMENTED (possible hallucination)
```

### Dead Client Methods
Client methods that no Click command calls:
```
For each public client method:
  Search all commands/*.py for calls to this method
  If no command calls it → DEAD
```

### Incomplete CRUD
For each resource group, check CRUD coverage:
```
For each resource in <APP>.md:
  Check which CRUD ops the API supports (list, get, create, update, delete)
  Check which are implemented as commands
  If any supported op is missing → INCOMPLETE
```

## Step 4: Priority Scoring (Optional)

If `{APP_PATH}/traffic-capture/raw-traffic.json` exists:
- Count how many times each endpoint URL appears in captured requests
- Assign priority: HIGH (5+ hits), MED (2-4 hits), LOW (1 hit)
- Note: traffic captures are incomplete — endpoints not exercised during
  capture may be ranked LOW even if they are important to users

If raw-traffic.json doesn't exist, skip priority scoring and list all
gaps alphabetically.

## Step 5: Output Report

Present the gap report in this format:

```
Gap Report: cli-web-{app}
━━━━━━━━━━━━━━━━━━━━━━━━━
Coverage: X/Y endpoints (Z%)

Missing (HIGH priority):
  {HTTP_METHOD} {url} — {description} ({N} hits in traffic)
  ...

Missing (MED priority):
  {HTTP_METHOD} {url} — {description} ({N} hits)
  ...

Missing (LOW priority):
  {HTTP_METHOD} {url} — {description} ({N} hits)
  ...

Incomplete CRUD:
  {resource}: has {ops} ✓, missing {ops} ✗
  ...

Dead client methods:
  client.{method_name}() — not called by any command
  ...

Undocumented commands:
  {group} {subcommand} — calls client.{method}() but endpoint not in <APP>.md
  ...
```

If all endpoints are covered:
```
Gap Report: cli-web-{app}
━━━━━━━━━━━━━━━━━━━━━━━━━
Coverage: Y/Y endpoints (100%)
No gaps found. All documented endpoints are implemented.
```
