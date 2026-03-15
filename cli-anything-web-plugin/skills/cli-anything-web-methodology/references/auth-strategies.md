# Auth Strategies Reference

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
auth login --browser  # opens Chrome for manual login, captures cookies
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

**Phase A — Cookie extraction via CDP (one-time):**
```python
# Connect to Chrome debug profile on port 9222
# Use Storage.getCookies CDP command
cookies = extract_cookies_via_cdp(port=9222, domain=".google.com")
save_cookies(cookies)  # ~/.config/cli-web-<app>/auth.json
```

**Phase B — Token extraction via HTTP (repeatable):**
```python
# Once you have valid cookies, HTTP GET works for token extraction
resp = httpx.get(APP_URL, headers={"Cookie": cookie_header(cookies)})
csrf = re.search(r'"SNlM0e":"([^"]+)"', resp.text).group(1)
session_id = re.search(r'"FdrFJe":"([^"]+)"', resp.text).group(1)
```

Key insight: CDP is only needed for initial cookie extraction. Token refresh
uses plain HTTP with those cookies — no CDP required for subsequent refreshes.

### Token refresh (on 401):
```python
def refresh_tokens(self):
    """Re-fetch tokens from homepage. Cookies are still valid."""
    resp = httpx.get(APP_URL, headers={"Cookie": self.cookie_header})
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
auth login --from-browser   # Phase A: extract cookies via CDP
auth status                 # Show cookies + token validity
auth refresh                # Phase B: re-fetch tokens via HTTP
```

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
