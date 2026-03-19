# Auth Strategies Reference

## Contents
- Cookie-Based Sessions
- Bearer / JWT Tokens
- API Key
- OAuth 2.0 / Browser-Based Login
- Browser-Delegated Auth (Anti-Bot Protected)
- Environment Variable Auth (CI/CD)
- Context Commands (Stateful Apps)
- Packaging Rules
- Simplified API Key Auth
- Config File Location

## Cookie-Based Sessions

### Detection:
- `Set-Cookie` in login response
- Subsequent requests include `Cookie` header
- Session cookies often named: `sid`, `session_id`, `connect.sid`

### Implementation:
```python
# auth.py
class CookieAuth:
    def __init__(self, config_dir):
        self.cookie_jar_path = config_dir / "cookies.json"

    def login(self, email, password, login_url):
        resp = httpx.post(login_url, json={"email": email, "password": password})
        self.save_cookies(resp.cookies)

    def inject(self, request):
        request.headers["Cookie"] = self.load_cookies()
```

### CLI commands:
```
auth login --email <e> --password <p>
auth login              # opens browser for manual login, captures cookies
auth status
auth logout
```

## Bearer / JWT Tokens

### Detection:
- `Authorization: Bearer <token>` header on API calls
- Login endpoint returns `{"access_token": "...", "refresh_token": "..."}`
- Token is base64-encoded JSON (JWT)

### Implementation:
```python
class BearerAuth:
    def __init__(self, config_dir):
        self.token_path = config_dir / "token.json"

    def login(self, email, password, auth_url):
        resp = httpx.post(auth_url, json={"email": email, "password": password})
        data = resp.json()
        self.save_token(data["access_token"], data.get("refresh_token"))

    def refresh(self):
        token = self.load_token()
        if self.is_expired(token["access_token"]):
            resp = httpx.post(self.refresh_url, json={"refresh_token": token["refresh_token"]})
            self.save_token(resp.json()["access_token"], token["refresh_token"])

    def inject(self, request):
        token = self.load_token()
        request.headers["Authorization"] = f"Bearer {token['access_token']}"
```

## API Key

### Detection:
- Custom header: `X-API-Key`, `Api-Key`, `Authorization: ApiKey <key>`
- Query parameter: `?api_key=<key>`

### Implementation:
```python
class ApiKeyAuth:
    def __init__(self, config_dir):
        self.key_path = config_dir / "api_key.txt"

    def set_key(self, key):
        self.key_path.write_text(key)

    def inject(self, request):
        request.headers["X-API-Key"] = self.key_path.read_text().strip()
```

### CLI commands:
```
auth set-key <key>
auth status
```

## OAuth 2.0 / Browser-Based Login

### Detection:
- Redirect to `/oauth/authorize` with `client_id`, `redirect_uri`
- Token exchange at `/oauth/token`
- Complex multi-step flow

### Implementation:
- Open browser for OAuth flow
- Start local HTTP server to receive callback
- Exchange code for tokens
- Store and refresh tokens

### CLI commands:
```
auth login          # opens browser, starts local server
auth login --token <t>  # manual token entry
auth refresh
auth status
```

## Browser-Delegated Auth (Anti-Bot Protected)

### Detection:
- HTTP login requests get redirected to CAPTCHA or JavaScript challenges
- Session tokens (CSRF, session IDs) are embedded in page JavaScript, not HTTP headers
- Tokens exist in `<script>` blocks or JS global objects (e.g., `WIZ_global_data`)
- Common with: Google apps, Microsoft 365, Salesforce Lightning

### Why standard login fails:
Google, Microsoft, and other major platforms detect automated HTTP clients and block
them — even with valid credentials. The browser is the only reliable login surface.

### Two-phase pattern:

**Phase A — Session capture via playwright-cli (primary):**
```python
# During development (Phase 1 recording)
# playwright-cli saves auth state automatically:
# npx @playwright/cli@latest -s=<app> state-save <app>-auth.json

# In generated CLI's auth login command:
import subprocess

# CRITICAL: Use Popen, NOT subprocess.run().
# subprocess.run() with playwright-cli "open --headed --persistent" BLOCKS
# until the browser is closed — the user can never reach input() to confirm
# they've logged in while the browser is still open. Popen runs the browser
# in the background so input() works.
proc = subprocess.Popen(["npx", "@playwright/cli@latest", "-s=auth",
                         "open", app_url, "--headed", "--persistent"])
input("Log in, then press ENTER...")
subprocess.run(["npx", "@playwright/cli@latest", "-s=auth",
                "state-save", str(auth_path)], capture_output=True, text=True, check=True)
subprocess.run(["npx", "@playwright/cli@latest", "-s=auth",
                "close"], capture_output=True)

# Parse storage state → extract cookies for httpx
# CRITICAL: state-save produces a LIST of cookie objects, not a flat dict.
# Each cookie has {name, value, domain, ...} and the SAME cookie name may
# appear multiple times for different domains.
state = json.loads(auth_path.read_text())
cookies = _extract_cookies_with_priority(state.get("cookies", []))
```

**Cookie domain priority (CRITICAL for Google apps):**

Playwright `state-save` captures cookies from ALL visited domains. For Google
apps, the same cookie names (`SID`, `__Secure-1PSID`, `HSID`, etc.) appear on
multiple domains: `.google.com`, `.google.co.il`, `.youtube.com`, etc.

**The naive approach is WRONG for international users:**
```python
# ✗ BROKEN — last value wins. If user is in Israel, .google.co.il overwrites
# .google.com and the CLI can't authenticate (gets redirected to login page).
cookies = {c["name"]: c["value"] for c in state.get("cookies", [])}
```

**The correct approach — prioritize `.google.com` over regional domains:**
```python
# ✓ CORRECT — .google.com cookies ALWAYS win over regional duplicates.
# Proven working with Israeli users (.google.co.il), and applicable to all 60+
# regional Google domains (.google.de, .google.co.jp, .google.com.br, etc.)
def _extract_cookies(raw_cookies: list) -> dict:
    result = {}
    result_domains = {}
    for c in raw_cookies:
        domain = c.get("domain", "")
        name = c.get("name", "")
        if not _is_allowed_domain(domain) or not name:
            continue
        # Don't overwrite a .google.com cookie with a regional duplicate
        if name not in result or domain == ".google.com":
            result[name] = c.get("value", "")
            result_domains[name] = domain
    return result
```

**Why this matters:** When httpx sends cookies to `notebooklm.google.com`, the
service only trusts cookies from `.google.com`. The regional `.google.co.il`
value for `__Secure-1PSID` is a different session token — valid on `google.co.il`
but rejected by `notebooklm.google.com`. The request gets 302'd to the Google
login page and `fetch_tokens()` fails with "Session expired."

**How to handle dual formats in `load_cookies()`:**

The auth file may contain cookies in either format depending on how it was saved:
- Dict format (CLI's own extraction): `{"cookies": {"SID": "val", ...}}`
- List format (raw playwright state): `{"cookies": [{name, value, domain, ...}, ...]}`

```python
def load_cookies() -> dict:
    data = json.loads(auth_file.read_text())
    cookies = data.get("cookies", {})
    # Handle raw playwright state-save format
    if isinstance(cookies, list):
        cookies = _extract_cookies(cookies)  # with domain priority
        if not cookies:
            raise AuthError("No Google cookies found")
    return cookies
```

**Legacy fallback (chrome-devtools-mcp):**
```python
# Option 1: autoConnect (Chrome 144+, no port needed)
cookies = extract_cookies_via_cdp(auto_connect=True, domain=".google.com")

# Option 2: Legacy debug profile (Chrome < 144)
cookies = extract_cookies_via_cdp(port=9222, domain=".google.com")

save_cookies(cookies)  # ~/.config/cli-web-<app>/auth.json
```

**Phase B — Token extraction via HTTP (repeatable):**
```python
# Once you have valid cookies, HTTP GET works for token extraction
resp = httpx.get(APP_URL, cookies=cookies, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})
csrf = re.search(r'"SNlM0e":"([^"]+)"', resp.text).group(1)
session_id = re.search(r'"FdrFJe":"([^"]+)"', resp.text).group(1)
```

Key insight: playwright-cli state-save is only needed for initial cookie extraction.
Token refresh uses plain HTTP with those cookies — no browser required for subsequent refreshes.

### Token refresh (on 401):
```python
def refresh_tokens(self):
    """Re-fetch tokens from homepage. Cookies are still valid."""
    resp = httpx.get(APP_URL, cookies=self.cookies)
    self.csrf, self.session_id = extract_tokens(resp.text)
```

### Auth file format:
```json
{
  "cookies": {"SID": "...", "HSID": "...", ...},
  "csrf_token": "AIXQIk...",
  "session_id": "394392219...",
  "extracted_at": "2026-03-15T12:00:00Z"
}
```

### CLI commands:
```
auth login              # playwright-cli state-save (primary)
auth login --cookies-json <file>  # manual import (fallback)
auth status             # show cookies + token validity
auth refresh            # re-fetch tokens via HTTP
```

### Known Pitfalls (from production bugs)

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| `subprocess.run()` with `open --persistent` | `input()` never reached; user sees "Aborted!" | Use `Popen()` so browser runs in background |
| Naive cookie flattening `{c["name"]: c["value"]}` | Auth works in US but fails in Israel, Germany, Japan, etc. | Prioritize `.google.com` over regional domains |
| `load_cookies()` expects dict but gets list | `TypeError` or empty cookies | Check `isinstance(cookies, list)` and convert |
| `state-save` from non-authenticated session | All cookies captured but none valid — redirects to login | Verify user logged in before saving state |
| Missing `User-Agent` header on token fetch | Some services reject bare HTTP clients | Always include a browser-like User-Agent |

## Environment Variable Auth (CI/CD)

For CI/CD pipelines where browser login is impossible, support an environment variable:

```python
import os, json

env_auth = os.environ.get(f"CLI_WEB_{APP_UPPER}_AUTH_JSON")
if env_auth:
    return json.loads(env_auth)
```

This allows headless environments to inject auth as a JSON string without
needing `auth login`.

## Context Commands (Stateful Apps)

For apps with persistent context (notebooks, projects, boards):

- `use <id>` — set the active context, stored in `context.json`
- `status` — show the current context (active notebook/project/board)

Store context at `~/.config/cli-web-<app>/context.json` alongside `auth.json`.

## Packaging Rules

- `setup.py` should NOT include Playwright Python as a dependency — only `click`, `httpx`,
  and other runtime deps. Playwright is a dev/user tool invoked via `npx`, not a Python import.
- No `--from-chrome` or `--from-browser` flags — playwright-cli is the only browser integration.

## Simplified API Key Auth

For sites that use API key auth (simple header like `api-key: <KEY>`),
implement a minimal auth module — no browser needed:

```python
# auth.py for API key auth
def login(api_key: str):
    save_auth({"api_key": api_key})

def inject_auth(headers: dict) -> dict:
    auth = load_auth()
    if auth and auth.get("api_key"):
        headers["api-key"] = auth["api_key"]
    return headers
```

The full playwright-cli browser login is only needed for browser-delegated
auth (Google apps, Microsoft 365, etc.).

## Config File Location

Standard: `~/.config/cli-web-<app>/auth.json`

```json
{
  "type": "bearer",
  "access_token": "...",
  "refresh_token": "...",
  "expires_at": "2026-03-15T12:00:00Z",
  "base_url": "https://api.monday.com/v2"
}
```

Permissions: `chmod 600 auth.json` — user-only read/write.
