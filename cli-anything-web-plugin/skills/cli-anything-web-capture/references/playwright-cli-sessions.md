> **Note:** Commands below use `playwright-cli` as shorthand for `npx @playwright/cli@latest`.
> Always run via npx: `npx @playwright/cli@latest -s=<app> <command>`

# Playwright-CLI Sessions and Auth State

Manage named browser sessions with isolated state, and persist/restore authentication for CLI generation workflows.

## Named Sessions

Use the `-s` flag to create isolated browser contexts. Each named session has its own cookies, localStorage, sessionStorage, browser cache, history, tab state, and network state.

```bash
# Open a named session
playwright-cli -s=suno open https://suno.com --headed --persistent

# Interact within that session
playwright-cli -s=suno snapshot
playwright-cli -s=suno click e15
playwright-cli -s=suno fill e3 "my prompt"

# Close the session
playwright-cli -s=suno close
```

### Session Isolation

Sessions are fully isolated from each other:

| Property | Isolated per session? |
|----------|----------------------|
| Cookies | Yes |
| localStorage / sessionStorage | Yes |
| IndexedDB | Yes |
| Browser cache | Yes |
| Browsing history | Yes |
| Open tabs | Yes |

This means `-s=suno` and `-s=futbin` can visit the same site with completely different auth states.

### Session Management Commands

```bash
# List all active sessions
playwright-cli list

# Close a specific session
playwright-cli -s=suno close

# Close all sessions
playwright-cli close-all

# Kill zombie/stale daemon processes
playwright-cli kill-all

# Delete session profile data from disk
playwright-cli -s=suno delete-data
```

## Why Sessions Matter for Our Pipeline

| Pipeline step | Session name | Purpose |
|---------------|-------------|---------|
| Phase 1 Step 2 (Site assessment) | `-s=<app>` | Quick probe — same session as full capture |
| Phase 1 Step 3 (Full capture) | `-s=<app>` | Main session with persistent auth |
| Subsequent runs | `-s=<app>` | Reuse auth via `state-load` |

- **Phase 1** uses a single `-s=<app>` session (e.g., `-s=suno`) for everything: site assessment (Step 2), full capture (Step 3), and auth persistence.
- Auth state persists via `state-save` so future sessions can skip login.

## State Save / Load (Auth Persistence)

### Save After Login

```bash
# User logs in manually via headed browser...
playwright-cli -s=suno open https://suno.com --headed --persistent
# ... user completes login flow ...

# Save the authenticated state
playwright-cli -s=suno state-save suno/traffic-capture/suno-auth.json
```

### Restore on Next Run

```bash
# Skip login by restoring saved state
playwright-cli -s=suno state-load suno/traffic-capture/suno-auth.json
playwright-cli -s=suno open https://suno.com
# Already authenticated!
```

### Storage State JSON Format

This is what `auth.py` in generated CLIs parses to extract cookies and tokens:

```json
{
  "cookies": [
    {
      "name": "session_id",
      "value": "abc123",
      "domain": ".suno.com",
      "path": "/",
      "expires": 1234567890,
      "httpOnly": true,
      "secure": true,
      "sameSite": "None"
    }
  ],
  "origins": [
    {
      "origin": "https://suno.com",
      "localStorage": [
        {"name": "theme", "value": "dark"},
        {"name": "clerk-token", "value": "eyJ..."}
      ]
    }
  ]
}
```

Key fields for CLI generation:
- `cookies` -- extracted and sent via `httpx` in the generated CLI's `auth.py`
- `origins[].localStorage` -- where JWTs often live (e.g., Clerk tokens, Firebase tokens)

## Cookie Management Commands

Useful for debugging auth issues during traffic capture:

```bash
# List all cookies
playwright-cli -s=<app> cookie-list

# Filter by domain
playwright-cli -s=<app> cookie-list --domain=suno.com

# Get a specific cookie value
playwright-cli -s=<app> cookie-get session_id

# Set a cookie manually
playwright-cli -s=<app> cookie-set session_id abc123 --domain=suno.com --path=/ --httpOnly --secure

# Delete a cookie
playwright-cli -s=<app> cookie-delete session_id

# Clear all cookies
playwright-cli -s=<app> cookie-clear
```

## localStorage / sessionStorage Commands

Useful for JWT extraction during traffic capture:

```bash
# List all localStorage items
playwright-cli -s=<app> localstorage-list

# Get a specific value (e.g., JWT token)
playwright-cli -s=<app> localstorage-get clerk-token

# Set a value
playwright-cli -s=<app> localstorage-set theme dark

# List sessionStorage items
playwright-cli -s=<app> sessionstorage-list

# Get a specific sessionStorage value
playwright-cli -s=<app> sessionstorage-get form_data
```

## How Generated CLIs Use This

The storage state JSON is the bridge between traffic capture and the generated CLI:

1. During Phase 1: `state-save` captures the full auth state after login
2. During Phase 4 (Implement): `auth.py` is generated to parse the same JSON format
3. At runtime: `auth login` runs `state-save` -> parses the JSON -> extracts cookies for httpx
4. Manual fallback: `auth login --cookies-json` accepts the same format for manual paste

## Best Practices

### Save Auth Before Tracing

Save auth state **before** starting the trace recording. If the session expires mid-trace, you can restore and retry without re-doing the login flow.

```bash
playwright-cli -s=suno state-save suno/traffic-capture/suno-auth.json
playwright-cli -s=suno tracing-start
# ... recording flow ...
playwright-cli -s=suno tracing-stop
```

### Use `--persistent` for Auth Sessions

Always use `--persistent` with `open` for sessions where you need auth to survive between commands:

```bash
playwright-cli -s=suno open https://suno.com --headed --persistent
```

### Never Commit Auth State Files

Add to `.gitignore`:
```
*-auth.json
*.auth-state.json
```

Auth state files contain session tokens, cookies, and potentially JWTs. Delete them after the traffic capture phase is complete.

### Name Sessions Semantically

```bash
# Good: clear purpose
playwright-cli -s=suno open https://suno.com
playwright-cli -s=futbin open https://futbin.com

# Avoid: generic names
playwright-cli -s=s1 open https://suno.com
```
