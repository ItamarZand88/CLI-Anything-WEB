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

## Cookie & Storage Commands (Debug Only)

For debugging auth issues:
```bash
playwright-cli -s=<app> cookie-list              # Show all cookies
playwright-cli -s=<app> cookie-get <name>         # Get specific cookie
playwright-cli -s=<app> localstorage-list          # Show localStorage keys
```
Rarely needed — `state-save` captures everything for auth.

## Key Points
- Always use `--persistent` for capture sessions
- Save auth state BEFORE tracing (`state-save`)
- Never commit auth state files to git
