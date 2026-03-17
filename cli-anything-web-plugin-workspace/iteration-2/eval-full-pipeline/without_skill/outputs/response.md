# NotebookLM Python CLI — Complete Implementation Plan

**Date:** 2026-03-15
**Scope:** Reverse-engineering, authentication, CLI design, code structure, testing strategy, and production readiness verification for a Python CLI that drives Google NotebookLM programmatically.

---

## Table of Contents

1. [API Reverse-Engineering Approach](#1-api-reverse-engineering-approach)
2. [Protocol Analysis — What NotebookLM Uses](#2-protocol-analysis)
3. [Authentication Strategy](#3-authentication-strategy)
4. [HTTP Client Setup](#4-http-client-setup)
5. [Complete CLI Command Tree](#5-complete-cli-command-tree)
6. [Code Structure and Parallel Build Tracks](#6-code-structure-and-parallel-build-tracks)
7. [Test Planning](#7-test-planning)
8. [Test Organization and Code Patterns](#8-test-organization-and-code-patterns)
9. [Auth End-to-End Verification](#9-auth-end-to-end-verification)
10. [Production Smoke Test](#10-production-smoke-test)

---

## 1. API Reverse-Engineering Approach

### Tool Stack

Traffic capture requires intercepting HTTPS between the browser and Google's servers. The best combination is:

- **Chrome DevTools** for initial manual discovery (zero setup, inspects live sessions)
- **mitmproxy** for automated, scriptable capture in headless environments
- **Playwright request interception** for integrating captures into test harnesses

### Phase 1 — Manual Discovery with Chrome DevTools

1. Open `https://notebooklm.google.com/` in Chrome, sign in.
2. Open DevTools → Network tab.
3. Enable **Preserve log** and **Disable cache**.
4. Filter by `batchexecute` to isolate RPC calls (other XHR noise is irrelevant).
5. Perform one isolated action (e.g., create a notebook).
6. Inspect the matching request:
   - **Headers tab**: The `rpcids` URL query parameter contains the RPC method ID (e.g., `CCqFvf` for CREATE_NOTEBOOK).
   - **Payload tab**: The form body contains the `f.req` URL-encoded parameter holding the nested array payload.
   - **Response tab**: Content starts with `)]}'\n` (anti-XSSI prefix), followed by chunked JSON.
7. Repeat for every action in scope.

The raw `f.req` value decoded looks like:

```
[[[rpc_id, "[payload_json]", null, "generic"]]]
```

Where `payload_json` is itself a compact-formatted JSON string (no spaces).

### Phase 2 — Playwright Automated Capture

For systematic capture and CI regression, instrument a Playwright browser session:

```python
# capture/record_session.py
import asyncio, json, urllib.parse
from playwright.async_api import async_playwright

RPC_BASE = "/_/LabsTailwindUi/data/batchexecute"
CHAT_STREAM = "/_/LabsTailwindUi/data/google.internal.labs.tailwind.orchestration.v1.LabsTailwindOrchestrationService/GenerateFreeFormStreamed"

async def capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="./chrome_profile",
            headless=False
        )
        page = await browser.new_page()

        async def handle_request(request):
            url = request.url
            if RPC_BASE in url or CHAT_STREAM in url:
                body = request.post_data or ""
                parsed = urllib.parse.parse_qs(body)
                raw_freq = parsed.get("f.req", [""])[0]
                print(json.dumps({
                    "url": url,
                    "rpcids": urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("rpcids", [""]),
                    "f_req": raw_freq
                }, indent=2))

        page.on("request", handle_request)
        await page.goto("https://notebooklm.google.com/")
        await asyncio.sleep(300)  # Manual interaction window
```

### Phase 3 — mitmproxy for Headless Environments

```bash
mitmproxy --mode regular --ssl-insecure \
  -s capture_notebooklm.py \
  --set confdir=~/.mitmproxy
```

```python
# capture_notebooklm.py
from mitmproxy import http
import json, urllib.parse

def request(flow: http.HTTPFlow):
    if "batchexecute" in flow.request.pretty_url:
        body = flow.request.get_text()
        qs = urllib.parse.parse_qs(body)
        freq = qs.get("f.req", [""])[0]
        print(f"[RPC CAPTURE] rpcids={flow.request.query.get('rpcids')} f.req={freq[:200]}")
```

### Decoding a Captured `f.req` Value

```python
import json, urllib.parse

def decode_freq(raw: str) -> dict:
    decoded = urllib.parse.unquote_plus(raw)
    outer = json.loads(decoded)           # [[[rpc_id, payload_str, null, "generic"]]]
    inner_str = outer[0][0][1]            # The inner JSON string
    payload = json.loads(inner_str)       # The actual parameters
    return {"rpc_id": outer[0][0][0], "payload": payload}
```

### What to Capture Per Feature

| Feature | Action to Trigger | Expected rpcids |
|---|---|---|
| List notebooks | Load home page | `wXbhsf` |
| Create notebook | Click "Create new" | `CCqFvf` |
| Get notebook | Open a notebook | `rLM1Ne` |
| Rename notebook | Rename via UI | `s0tc2d` |
| Delete notebook | Delete via UI | `WWINqb` |
| Add URL source | Paste URL in source panel | `izAoDd` |
| Add file source | Upload PDF | `o4cbdc` |
| Delete source | Remove a source | `tGMBJ` |
| Chat query | Send a message | streaming endpoint |
| Create note | Add a note | `CYK0Xb` + `cYAfTb` |
| Generate audio | Click "Generate" in Studio | `R7cb6c` (type=1) |
| List artifacts | Open Studio tab | `gArtLc` |

---

## 2. Protocol Analysis

### Confirmed Protocol: Google batchexecute RPC

NotebookLM does **not** use REST JSON or gRPC over HTTP/2 with protobuf. It uses Google's internal **batchexecute** mechanism — the same transport used by Google Maps, Google Docs, and other first-party Google web apps.

**Base endpoint:**
```
POST https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute
```

**Chat-specific streaming endpoint:**
```
POST https://notebooklm.google.com/_/LabsTailwindUi/data/google.internal.labs.tailwind.orchestration.v1.LabsTailwindOrchestrationService/GenerateFreeFormStreamed
```

### Request Format

Query parameters on the POST URL:
```
rpcids=<method_id>&source-path=/notebook/<notebook_id>&f.sid=<FdrFJe>&bl=<build_label>&hl=en&rt=c
```

Form-encoded POST body:
```
f.req=%5B%5B%5B%22CCqFvf%22%2C%22%5B%5B%5C%22My+Notebook%5C%22%5D%5D%22%2Cnull%2C%22generic%22%5D%5D%5D&
```

When decoded, `f.req` is:
```json
[[["CCqFvf", "[[\"My Notebook\"]]", null, "generic"]]]
```

**Critical encoding rules:**
1. The outer structure is `[[[rpc_id, payload_string, null, "generic"]]]`.
2. `payload_string` is a compact JSON string with no whitespace (matches Chrome's `JSON.stringify` default).
3. The entire `f.req` value is URL-encoded with `safe=''` (all special characters encoded).
4. The body is form-encoded (`Content-Type: application/x-www-form-urlencoded`).

### Response Format

Responses arrive as chunked streaming data:
```
)]}'\n
<byte_count>\n
<json_chunk>\n
<byte_count>\n
<json_chunk>\n
...
```

Each JSON chunk is one of:
- `[["wrb.fr", rpc_id, result_json, null, null, null, "generic"]]` — actual result
- `[["di", "n"]]` — ping/heartbeat
- `[["e", 4]]` — end of stream

**Decoding pipeline:**
```python
def decode_batchexecute_response(raw: str, expected_rpc_id: str):
    # 1. Strip anti-XSSI prefix
    body = raw.lstrip(")]}'\n")

    # 2. Split into chunks by alternating length/content lines
    results = []
    lines = body.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.isdigit():
            i += 1
            if i < len(lines):
                try:
                    chunk = json.loads(lines[i])
                    results.append(chunk)
                except json.JSONDecodeError:
                    pass
        i += 1

    # 3. Extract wrb.fr chunk matching our rpc_id
    for chunk in results:
        for entry in chunk:
            if isinstance(entry, list) and len(entry) >= 3:
                if entry[0] == "wrb.fr" and entry[1] == expected_rpc_id:
                    return json.loads(entry[2])  # The actual payload
    return None
```

### Known RPC Method Registry

```python
RPC_METHODS = {
    # Notebooks
    "LIST_NOTEBOOKS":       "wXbhsf",
    "CREATE_NOTEBOOK":      "CCqFvf",
    "GET_NOTEBOOK":         "rLM1Ne",
    "RENAME_NOTEBOOK":      "s0tc2d",
    "DELETE_NOTEBOOK":      "WWINqb",
    # Sources
    "ADD_SOURCE":           "izAoDd",   # URL and text
    "ADD_SOURCE_FILE":      "o4cbdc",   # Binary upload
    "DELETE_SOURCE":        "tGMBJ",
    "UPDATE_SOURCE":        "b7Wfje",
    "GET_SOURCE_GUIDE":     "tr032e",
    "REFRESH_SOURCE":       "FLmJqe",
    "CHECK_SOURCE_FRESHNESS": "yR9Yof",
    # Artifacts
    "CREATE_ARTIFACT":      "R7cb6c",
    "LIST_ARTIFACTS":       "gArtLc",
    "DELETE_ARTIFACT":      "V5N4be",
    "RENAME_ARTIFACT":      "rc3d8d",
    "EXPORT_ARTIFACT":      "Krh3pd",
    "SHARE_ARTIFACT":       "RGP97b",
    "GET_SUGGESTED_REPORTS": "ciyUvf",
    "GET_INTERACTIVE_HTML": "v9rmvd",
    "GENERATE_MIND_MAP":    "yyryJe",
    # Chat
    "GET_CONVERSATION_ID":  "hPTbtc",
    "GET_CONVERSATION_TURNS": "khqZz",
    # Notes
    "CREATE_NOTE":          "CYK0Xb",
    "UPDATE_NOTE":          "cYAfTb",
    "DELETE_NOTE":          "AH0mwd",
    "GET_NOTES_AND_MIND_MAPS": "cFji9",
    # Research
    "START_FAST_RESEARCH":  "Ljjv0c",
    "START_DEEP_RESEARCH":  "QA9ei",
    "POLL_RESEARCH":        "e3bVqc",
    "IMPORT_RESEARCH":      "LBwxtb",
    # Sharing & Settings
    "SHARE_NOTEBOOK":       "QDyure",
    "GET_SHARE_STATUS":     "JFMDGd",
    "SUMMARIZE":            "VfAZjd",
    "GET_USER_SETTINGS":    "ZwVcOc",
    "SET_USER_SETTINGS":    "hT54vc",
    "REMOVE_RECENTLY_VIEWED": "fejl7e",
}
```

### Artifact Type Codes

```python
ARTIFACT_TYPES = {
    "audio":      1,
    "report":     2,
    "video":      3,
    "quiz":       4,
    "flashcards": 4,  # same type code, different subtype
    "mindmap":    5,
    "infographic":7,
    "slides":     8,
    "datatable":  9,
}
```

### Source ID Nesting Rules

The API requires different nesting depths depending on the operation — a quirk of the internal RPC schema:

```python
def wrap_source_id(source_id: str, operation: str) -> list:
    if operation in ("UPDATE_SOURCE",):
        return [source_id]                          # single
    elif operation in ("DELETE_SOURCE",):
        return [[[source_id]]]                      # triple
    elif operation in ("GET_SOURCE_GUIDE",):
        return [[[[source_id]]]]                    # quadruple
    elif operation in ("CREATE_ARTIFACT",):
        return [[[source_id]]]                      # triple per source in a list
```

---

## 3. Authentication Strategy

### The Core Problem

NotebookLM requires a valid Google session — meaning actual Google login cookies (`SID`, `HSID`, `SSID`, `APISID`, `SAPISID`) plus two tokens extracted from the page HTML after login:

- **SNlM0e** — CSRF token, embedded in `window.WIZ_global_data` as a JavaScript object
- **FdrFJe** — session/build ID, extracted from the same object

Google's login flow is protected by:
- JavaScript-rendered login pages
- BotGuard (reCAPTCHA v3-style challenge embedded in login)
- Fingerprinting of browser headers and TLS fingerprint
- Rate limiting on credential-based automation

### Recommended Approach: Playwright Browser Login (Interactive Once)

The only reliable approach for personal/developer use without Google Workspace API access is a one-time interactive browser login, with cookie persistence.

```
notebooklm login
```

This command:
1. Launches a full Playwright browser (chromium).
2. Navigates to `https://notebooklm.google.com/`.
3. Waits for the user to complete login manually (including 2FA if set).
4. Detects successful login by waiting for the main app shell to load (e.g., element `[aria-label="Create notebook"]`).
5. Saves the browser storage state (cookies + localStorage) to `~/.notebooklm/storage_state.json`.

```python
# src/notebooklm_cli/auth/login.py

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

DEFAULT_STORAGE = Path.home() / ".notebooklm" / "storage_state.json"

async def interactive_login(storage_path: Path = DEFAULT_STORAGE, browser_type: str = "chromium"):
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser_launcher = getattr(p, browser_type)
        context = await browser_launcher.launch_persistent_context(
            user_data_dir=str(storage_path.parent / "browser_profile"),
            headless=False,
            args=["--no-sandbox"],
        )
        page = await context.new_page()
        await page.goto("https://notebooklm.google.com/")

        print("Complete login in the browser window. Press Enter when done...")
        # Wait for app shell as signal of successful login
        try:
            await page.wait_for_selector('[data-testid="new-notebook-button"]', timeout=300_000)
            print("Login detected. Saving session...")
        except Exception:
            input("Press Enter after completing login manually: ")

        await context.storage_state(path=str(storage_path))
        await context.close()
        print(f"Session saved to {storage_path}")
```

### Token Extraction After Login

After loading cookies, the CLI must extract `SNlM0e` and `FdrFJe` by fetching the NotebookLM homepage with the session cookies and regex-parsing the embedded JS:

```python
import re, httpx
from dataclasses import dataclass

@dataclass
class AuthTokens:
    cookies: dict
    csrf_token: str    # SNlM0e
    session_id: str    # FdrFJe

WIZ_PATTERN = re.compile(r'"SNlM0e":"([^"]+)"')
SESSION_PATTERN = re.compile(r'"FdrFJe":"([^"]+)"')

async def extract_tokens(cookies: dict) -> AuthTokens:
    async with httpx.AsyncClient(cookies=cookies) as client:
        resp = await client.get(
            "https://notebooklm.google.com/",
            headers={"Accept": "text/html"},
            follow_redirects=False,
        )
        if resp.status_code == 302:
            raise AuthError("Session expired. Run 'notebooklm login'.")

        html = resp.text
        csrf_match = WIZ_PATTERN.search(html)
        session_match = SESSION_PATTERN.search(html)

        if not csrf_match or not session_match:
            raise AuthError("Could not extract tokens. Run 'notebooklm login'.")

        return AuthTokens(
            cookies=cookies,
            csrf_token=csrf_match.group(1),
            session_id=session_match.group(1),
        )
```

### Cookie Loading from Storage State

```python
import json
from pathlib import Path
import httpx

ALLOWED_DOMAINS = {".google.com", "notebooklm.google.com", ".googleusercontent.com"}
REQUIRED_COOKIES = {"SID", "HSID", "SSID", "APISID", "SAPISID"}

def load_cookies(storage_path: Path) -> httpx.Cookies:
    with open(storage_path) as f:
        state = json.load(f)

    jar = httpx.Cookies()
    seen = set()

    for cookie in state.get("cookies", []):
        domain = cookie.get("domain", "")
        name = cookie.get("name", "")

        # Prefer .google.com over regional variants
        if name in seen and domain != ".google.com":
            continue

        if any(domain.endswith(d) for d in ALLOWED_DOMAINS) or domain in ALLOWED_DOMAINS:
            jar.set(name, cookie["value"], domain=domain, path=cookie.get("path", "/"))
            seen.add(name)

    missing = REQUIRED_COOKIES - set(jar.keys())
    if missing:
        raise AuthError(f"Missing required cookies: {missing}. Run 'notebooklm login'.")

    return jar
```

### Anti-Bot Protections and Mitigations

Google's anti-bot stack operates at multiple layers:

| Layer | Mechanism | Mitigation |
|---|---|---|
| Login page | BotGuard JS challenge | Use real Playwright browser for login (not headless `requests`) |
| TLS fingerprint | JA3/JA3S fingerprinting | httpx uses Python's native `ssl` (different JA3 from curl) — acceptable since we use valid cookies, not credential stuffing |
| Header analysis | Missing/unusual UA, Accept headers | Set a complete, realistic Chrome header set (see Section 4) |
| Cookie validation | Cross-check cookie domain, timestamps | Use cookies exactly as set by Google's server |
| Rate limiting | 429 responses, `UserDisplayableError` in body | Exponential backoff, respect `Retry-After` |
| CSRF | `SNlM0e` token required in body | Extract fresh from homepage each session |
| Session expiry | Cookies expire, redirects to login | Detect 302 redirects, prompt re-login |

**Key insight:** Because we authenticate with a real browser session (not programmatically signing in), we bypass BotGuard entirely. The only ongoing risk is session expiry (typically 2 weeks for persistent sessions) and IP-based rate limiting.

---

## 4. HTTP Client Setup

### Client Configuration

```python
# src/notebooklm_cli/http/client.py

import httpx
from typing import Optional
from .auth import AuthTokens

BASE_URL = "https://notebooklm.google.com"
BUILD_LABEL = "boq_labs-tailwind-frontend_20240101.00_p0"  # Update periodically

CHROME_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    "Origin": "https://notebooklm.google.com",
    "Referer": "https://notebooklm.google.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "X-Same-Domain": "1",
}

class NotebookLMHTTPClient:
    def __init__(self, tokens: AuthTokens):
        self._tokens = tokens
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            cookies=self._tokens.cookies,
            headers=CHROME_HEADERS,
            timeout=httpx.Timeout(30.0, read=120.0),  # 2-min read for generation polling
            follow_redirects=False,  # Detect auth expiry manually
            http2=True,  # Match Chrome's HTTP/2 preference
        )
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()

    async def rpc(
        self,
        method_id: str,
        payload: list,
        notebook_id: Optional[str] = None,
        *,
        retries: int = 3,
    ) -> list:
        url_params = self._build_url_params(method_id, notebook_id)
        body = self._build_body(method_id, payload)

        for attempt in range(retries):
            resp = await self._client.post(
                f"/_/LabsTailwindUi/data/batchexecute?{url_params}",
                content=body,
            )

            if resp.status_code == 302:
                raise AuthError("Session expired. Run 'notebooklm login'.")
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 60))
                await asyncio.sleep(wait * (2 ** attempt))
                continue
            resp.raise_for_status()

            return decode_batchexecute_response(resp.text, method_id)

        raise RateLimitError("Rate limit exceeded after retries.")

    def _build_url_params(self, method_id: str, notebook_id: Optional[str]) -> str:
        source_path = f"/notebook/{notebook_id}" if notebook_id else "/"
        params = {
            "rpcids": method_id,
            "source-path": source_path,
            "f.sid": self._tokens.session_id,
            "bl": BUILD_LABEL,
            "hl": "en",
            "rt": "c",
        }
        return urllib.parse.urlencode(params)

    def _build_body(self, method_id: str, payload: list) -> str:
        payload_str = json.dumps(payload, separators=(",", ":"))
        freq = json.dumps([[[method_id, payload_str, None, "generic"]]], separators=(",", ":"))
        encoded_freq = urllib.parse.quote(freq, safe="")
        csrf = f"at={urllib.parse.quote(self._tokens.csrf_token, safe='')}&" if self._tokens.csrf_token else ""
        return f"f.req={encoded_freq}&{csrf}"
```

### CSRF Token Refresh

The `SNlM0e` token is session-scoped but can be refreshed by re-fetching the homepage. The client should refresh automatically on `AuthError`:

```python
async def refresh_tokens(self):
    resp = await self._client.get("/", headers={"Accept": "text/html"}, follow_redirects=False)
    if resp.status_code == 302:
        raise AuthError("Cannot refresh — session expired.")
    self._tokens = await extract_tokens_from_html(resp.text, self._tokens.cookies)
    # Update client headers with new session_id
```

---

## 5. Complete CLI Command Tree

The CLI uses **Click** with a group hierarchy. All commands are async (via `asyncio.run` wrappers).

```
notebooklm
├── login                          # Playwright browser login
│   └── --browser [chromium|msedge|firefox]
├── logout                         # Clear stored session
├── auth
│   └── check                      # Validate stored session
│       └── --test                 # Make a real API call to verify
│
├── notebook
│   ├── list                       # List all notebooks
│   │   ├── --json                 # Output as JSON
│   │   └── --limit N
│   ├── create <title>             # Create notebook
│   │   └── --emoji CHAR
│   ├── get <notebook-id>          # Get notebook details
│   │   └── --json
│   ├── rename <notebook-id> <new-title>
│   ├── delete <notebook-id>
│   │   └── --yes                  # Skip confirmation
│   └── summarize <notebook-id>
│
├── source
│   ├── list <notebook-id>
│   │   └── --json
│   ├── add <notebook-id> <path-or-url>
│   │   ├── --type [url|file|text|youtube|drive]
│   │   ├── --wait                 # Poll until processing complete
│   │   └── --timeout SECONDS
│   ├── add-text <notebook-id>     # Read from stdin or --text
│   │   └── --text "content"
│   ├── delete <notebook-id> <source-id>
│   │   └── --yes
│   ├── refresh <notebook-id> <source-id>
│   └── guide <notebook-id> <source-id>   # Get AI-generated guide for source
│
├── chat
│   ├── ask <notebook-id> <question>
│   │   ├── --json
│   │   └── --stream               # Stream tokens to stdout
│   ├── history <notebook-id>
│   │   └── --json
│   └── clear <notebook-id>
│
├── note
│   ├── list <notebook-id>
│   │   └── --json
│   ├── create <notebook-id> <title>
│   │   └── --content "text"
│   ├── update <note-id> <notebook-id>
│   │   ├── --title "new title"
│   │   └── --content "new content"
│   └── delete <note-id> <notebook-id>
│       └── --yes
│
├── generate
│   ├── audio <notebook-id>
│   │   ├── --format [default|deep-dive|briefing|qa]
│   │   ├── --length [short|medium|long]
│   │   ├── --language LANG_CODE
│   │   ├── --sources SOURCE_ID...  # Limit to specific sources
│   │   ├── --instructions TEXT
│   │   └── --wait
│   ├── video <notebook-id>
│   │   ├── --format [default|explainer|deep-dive]
│   │   ├── --style [chalkboard|whiteboard|...]
│   │   └── --wait
│   ├── quiz <notebook-id>
│   │   ├── --difficulty [easy|medium|hard]
│   │   ├── --count N
│   │   └── --wait
│   ├── flashcards <notebook-id>
│   │   └── --wait
│   ├── slides <notebook-id>
│   │   ├── --format [pptx|pdf]
│   │   └── --wait
│   ├── report <notebook-id>
│   │   ├── --template TEMPLATE_TYPE
│   │   └── --wait
│   ├── mindmap <notebook-id>
│   │   └── --wait
│   ├── infographic <notebook-id>
│   │   ├── --orientation [portrait|landscape|square]
│   │   └── --wait
│   └── datatable <notebook-id>
│       └── --wait
│
├── artifact
│   ├── list <notebook-id>
│   │   └── --json
│   ├── get <notebook-id> <artifact-id>
│   ├── delete <notebook-id> <artifact-id>
│   │   └── --yes
│   ├── rename <notebook-id> <artifact-id> <new-name>
│   └── download <notebook-id> <artifact-id> <output-path>
│       └── --format [mp3|mp4|pdf|pptx|json|csv|md|html]
│
├── share
│   ├── notebook <notebook-id>
│   │   ├── enable
│   │   │   └── --level [viewer|editor]
│   │   ├── disable
│   │   └── status
│   └── artifact <notebook-id> <artifact-id>
│       ├── enable
│       └── disable
│
└── research
    ├── fast <notebook-id> <query>
    │   └── --import               # Auto-import results as source
    └── deep <notebook-id> <query>
        ├── --import
        └── --wait
```

### Output Conventions

- All commands default to human-readable, colorized terminal output via **Rich**.
- `--json` flag on any read command emits newline-delimited JSON to stdout (machine-readable).
- `--quiet` / `-q` suppresses all output except errors.
- Exit codes: 0 = success, 1 = user error, 2 = API error, 3 = auth error.

---

## 6. Code Structure and Parallel Build Tracks

### Directory Layout

```
notebooklm-cli/
├── src/
│   └── notebooklm_cli/
│       ├── __init__.py
│       ├── py.typed
│       │
│       ├── auth/                    # Track A
│       │   ├── __init__.py
│       │   ├── login.py             # Playwright interactive login
│       │   ├── tokens.py            # AuthTokens dataclass + extraction
│       │   ├── cookies.py           # Cookie loading from storage state
│       │   └── storage.py           # Storage state file management
│       │
│       ├── http/                    # Track B (depends on auth/)
│       │   ├── __init__.py
│       │   ├── client.py            # NotebookLMHTTPClient (httpx wrapper)
│       │   ├── rpc/
│       │   │   ├── __init__.py
│       │   │   ├── encoder.py       # encode_rpc_request, build_request_body, build_url_params
│       │   │   ├── decoder.py       # decode_batchexecute_response, parse_chunks
│       │   │   └── methods.py       # RPC_METHODS registry, ARTIFACT_TYPES
│       │   └── streaming.py         # Server-sent events / chunked stream reader for chat
│       │
│       ├── api/                     # Track C (depends on http/)
│       │   ├── __init__.py
│       │   ├── notebooks.py         # NotebooksAPI
│       │   ├── sources.py           # SourcesAPI
│       │   ├── chat.py              # ChatAPI
│       │   ├── notes.py             # NotesAPI
│       │   ├── artifacts.py         # ArtifactsAPI
│       │   ├── research.py          # ResearchAPI
│       │   ├── sharing.py           # SharingAPI
│       │   └── settings.py          # SettingsAPI
│       │
│       ├── models/                  # Track A (independent)
│       │   ├── __init__.py
│       │   ├── notebook.py          # Notebook, NotebookDescription, NotebookMetadata
│       │   ├── source.py            # Source, SourceType, SourceStatus, SourceFulltext
│       │   ├── artifact.py          # Artifact, ArtifactType, GenerationStatus
│       │   ├── note.py              # Note
│       │   ├── chat.py              # ConversationTurn, ChatReference, AskResult
│       │   └── enums.py             # All configuration enums
│       │
│       ├── cli/                     # Track D (depends on api/)
│       │   ├── __init__.py
│       │   ├── main.py              # Click root group + asyncio bridge
│       │   ├── commands/
│       │   │   ├── auth.py          # login, logout, auth check
│       │   │   ├── notebooks.py     # notebook subcommands
│       │   │   ├── sources.py       # source subcommands
│       │   │   ├── chat.py          # chat subcommands
│       │   │   ├── notes.py         # note subcommands
│       │   │   ├── generate.py      # generate subcommands
│       │   │   ├── artifacts.py     # artifact subcommands
│       │   │   ├── share.py         # share subcommands
│       │   │   └── research.py      # research subcommands
│       │   └── output/
│       │       ├── formatters.py    # Rich table/panel formatters
│       │       └── json_output.py   # JSON serialization helpers
│       │
│       └── exceptions.py            # Full exception hierarchy
│
├── tests/
│   ├── conftest.py                  # Global fixtures + pytest config
│   ├── unit/
│   │   ├── test_rpc_encoder.py
│   │   ├── test_rpc_decoder.py
│   │   ├── test_cookie_loading.py
│   │   ├── test_token_extraction.py
│   │   ├── test_models.py
│   │   └── test_cli_output_formatters.py
│   ├── integration/
│   │   ├── conftest.py              # pytest-httpx mock setup
│   │   ├── test_notebooks_api.py
│   │   ├── test_sources_api.py
│   │   ├── test_chat_api.py
│   │   ├── test_notes_api.py
│   │   ├── test_artifacts_api.py
│   │   └── test_cli_commands.py     # Click test runner
│   └── e2e/
│       ├── conftest.py              # Requires NOTEBOOKLM_AUTH_JSON env
│       ├── test_auth.py
│       ├── test_notebooks_e2e.py
│       ├── test_sources_e2e.py
│       ├── test_chat_e2e.py
│       └── test_smoke.py            # Production smoke test
│
├── scripts/
│   ├── capture_traffic.py           # Playwright-based traffic capture
│   ├── decode_freq.py               # f.req decoder utility
│   └── update_build_label.py        # Scrapes current bl= value from notebooklm.google.com
│
├── pyproject.toml
├── .env.example
└── README.md
```

### Parallel Build Tracks

The codebase has a clear dependency graph that allows four parallel tracks:

```
Track A (no dependencies):
  models/          — pure dataclasses and enums, no I/O
  auth/tokens.py   — regex parsing only
  auth/cookies.py  — pure cookie manipulation
  auth/storage.py  — file I/O only
  exceptions.py    — pure exception hierarchy

Track B (depends on Track A: auth/* + exceptions):
  http/rpc/encoder.py   — pure encoding functions
  http/rpc/decoder.py   — pure decoding functions
  http/rpc/methods.py   — registry constants
  http/client.py        — httpx client (depends on auth tokens + rpc/)
  http/streaming.py     — stream reader

Track C (depends on Track B: http/*):
  api/notebooks.py
  api/sources.py
  api/chat.py
  api/notes.py
  api/artifacts.py
  api/research.py
  api/sharing.py
  api/settings.py

Track D (depends on Track C: api/* + models/*):
  cli/commands/*    — Click commands
  cli/output/*      — Formatters

Track E (login, depends on auth/ but uses Playwright, optional dependency):
  auth/login.py     — Playwright browser login
```

Tracks A through E map cleanly to sprint parallelism. Track A + B can ship in sprint 1, C in sprint 2, D in sprint 3.

---

## 7. Test Planning

### Test Pyramid Structure

```
                    /\
                   /  \       E2E (requires live auth)
                  / e2e\      ~15 tests
                 /------\
                /        \    Integration (pytest-httpx mocks)
               / integr.  \   ~60 tests
              /            \
             /--------------\
            /                \   Unit tests (pure logic)
           /      unit        \  ~80 tests
          /____________________\
```

### Unit Tests (~80 tests)

Location: `tests/unit/`

These test pure functions with no I/O:

**`test_rpc_encoder.py`** — covers `encode_rpc_request`, `build_request_body`, `build_url_params`:
- Correct triple-nested array structure output
- Compact JSON (no spaces in payload_str)
- URL encoding of all special characters in f.req
- CSRF token included in body when provided
- Source path `/notebook/<id>` vs `/` for root-level calls
- `rt=c` always present in URL params

**`test_rpc_decoder.py`** — covers `decode_batchexecute_response`, `parse_chunks`:
- Strips `)]}'\n` prefix correctly
- Parses alternating length/content chunk format
- Extracts correct `wrb.fr` entry by rpc_id
- Returns `None` on null result (method returned no data)
- Raises `RateLimitError` on `UserDisplayableError` in body
- Raises `DecodingError` when >10% of chunks are malformed
- Handles `di` and `e` chunks (ping/end-of-stream) without error
- Multi-chunk responses where result spans multiple entries

**`test_cookie_loading.py`**:
- Loads cookies from a fixture storage_state.json
- `.google.com` wins over regional variant for same cookie name
- Raises `AuthError` when any of the 5 required cookies is missing
- Ignores cookies from non-whitelisted domains
- Returns correct `httpx.Cookies` type

**`test_token_extraction.py`**:
- Extracts `SNlM0e` and `FdrFJe` from a fixture HTML page
- Raises `AuthError` when patterns are absent
- Raises `AuthError` on 302 redirect response
- Handles HTML with extra surrounding JS noise

**`test_models.py`**:
- Notebook dataclass field access
- ArtifactType enum values
- GenerationStatus comparison
- SourceStatus enum serialization

**`test_cli_output_formatters.py`**:
- Rich table output structure for notebook list
- JSON output is valid JSON with expected keys
- Human-readable output contains notebook title

### Integration Tests (~60 tests)

Location: `tests/integration/`

Uses **pytest-httpx** to intercept `httpx.AsyncClient` calls and return fixture responses. No real network calls.

**Fixtures in `tests/integration/conftest.py`**:

```python
import pytest
from pytest_httpx import HTTPXMock
from notebooklm_cli.auth.tokens import AuthTokens

MOCK_TOKENS = AuthTokens(
    cookies={"SID": "test-sid", "HSID": "test-hsid", ...},
    csrf_token="test-csrf-123",
    session_id="test-session-456",
)

def build_batchexecute_response(rpc_id: str, data: list) -> str:
    """Build a properly formatted batchexecute response fixture."""
    payload_json = json.dumps(data)
    chunk = json.dumps([["wrb.fr", rpc_id, payload_json, None, None, None, "generic"]])
    chunk_bytes = chunk.encode()
    return f")]}'\n{len(chunk_bytes)}\n{chunk}\n"

@pytest.fixture
def mock_notebook_list_response():
    return build_batchexecute_response("wXbhsf", [
        [["notebook-id-1", "My First Notebook", None, None, "📚", 1700000000, 1700000000]],
        [["notebook-id-2", "Research Notes", None, None, "🔬", 1700000100, 1700000100]],
    ])
```

**`test_notebooks_api.py`** (~15 tests):
- `list()` returns a list of `Notebook` objects with correct fields
- `create("Title")` sends `CCqFvf` with correct payload and returns Notebook
- `get(id)` sends `rLM1Ne` with correct notebook_id in source-path
- `rename(id, "New Title")` sends `s0tc2d`
- `delete(id)` sends `WWINqb`
- `delete(id)` raises `NotebookNotFoundError` on null response
- Auth refresh triggered automatically on first `AuthError`

**`test_sources_api.py`** (~12 tests):
- `add_url(nb_id, url)` sends `izAoDd` with correct URL in payload
- `add_file(nb_id, path)` sends `o4cbdc` with base64-encoded content
- `add_text(nb_id, content)` sends `izAoDd` with text type flag
- `delete(nb_id, source_id)` uses triple-wrapped source_id
- `wait=True` polls source status until `SourceStatus.READY`
- `wait=True` raises `SourceTimeoutError` if not ready within timeout

**`test_chat_api.py`** (~8 tests):
- `ask(nb_id, "question")` hits streaming endpoint, not batchexecute
- Response contains `answer` and `conversation_id`
- Follow-up question includes conversation_id in payload
- Stream parsing correctly extracts token chunks
- `ChatError` raised on error chunk in stream

**`test_notes_api.py`** (~8 tests):
- `create(nb_id, title, content)` issues `CYK0Xb` then immediately `cYAfTb`
- `update(note_id, nb_id, title=None, content="new")` only sets changed fields
- `delete(note_id, nb_id)` uses soft-delete (status=2)
- `list(nb_id)` returns list of `Note` objects

**`test_artifacts_api.py`** (~10 tests):
- `generate_audio(nb_id)` sends `R7cb6c` with type=1
- `generate_audio(nb_id, format=AudioFormat.DEEP_DIVE)` sends correct subtype
- `list(nb_id)` parses `gArtLc` response into `Artifact` objects
- `download(nb_id, artifact_id, path)` follows redirect and writes file
- `wait_for_completion(nb_id, artifact_id)` polls until status=2

**`test_cli_commands.py`** (~15 tests using Click's `CliRunner`):
- `notebooklm notebook list` produces table output
- `notebooklm notebook list --json` produces valid JSON
- `notebooklm notebook create "Test"` prints notebook ID
- `notebooklm source add <nb-id> "https://example.com"` calls API
- `notebooklm chat ask <nb-id> "What is this?"` prints answer
- Error exits with code 2 on API error
- Auth error exits with code 3 and prints login hint

### E2E Tests (~15 tests)

Location: `tests/e2e/`

Require live credentials. Only run when `NOTEBOOKLM_AUTH_JSON` environment variable points to a valid storage state file.

**Guard decorator:**
```python
import os, pytest

requires_auth = pytest.mark.skipif(
    not os.environ.get("NOTEBOOKLM_AUTH_JSON"),
    reason="NOTEBOOKLM_AUTH_JSON not set"
)
```

**`test_auth.py`**:
- Storage state loads without error
- Token extraction from live homepage succeeds
- `SNlM0e` and `FdrFJe` are non-empty strings

**`test_notebooks_e2e.py`** (uses cleanup fixture):
- Create notebook → appears in list → get by ID → rename → delete
- Deleted notebook no longer in list

**`test_sources_e2e.py`**:
- Add URL source → wait=True completes without error → delete
- Add text source → source appears in list

**`test_chat_e2e.py`**:
- Ask a question against a notebook with a source → get non-empty answer

**`test_smoke.py`** — see Section 10.

---

## 8. Test Organization and Code Patterns

### pytest Configuration (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
timeout = 60
markers = [
    "e2e: requires live credentials (NOTEBOOKLM_AUTH_JSON)",
    "vcr: uses cassette recordings",
    "readonly: does not modify remote state",
    "slow: takes more than 10 seconds",
]
testpaths = ["tests"]

[tool.coverage.run]
branch = true
source = ["src/notebooklm_cli"]
omit = ["*/auth/login.py"]  # Playwright login not unit-testable

[tool.coverage.report]
fail_under = 90
```

### Base Test Class Pattern

```python
# tests/integration/conftest.py

import pytest
import asyncio
from notebooklm_cli.http.client import NotebookLMHTTPClient
from notebooklm_cli.auth.tokens import AuthTokens

MOCK_TOKENS = AuthTokens(
    cookies={"SID": "sid", "HSID": "hsid", "SSID": "ssid", "APISID": "apisid", "SAPISID": "sapisid"},
    csrf_token="csrf-token",
    session_id="session-id",
)

@pytest.fixture
def mock_client(httpx_mock):
    """Return a NotebookLMHTTPClient backed by pytest-httpx mock."""
    return NotebookLMHTTPClient(MOCK_TOKENS)
```

### RPC Mock Helper Pattern

```python
def mock_rpc(httpx_mock, rpc_id: str, response_data: list, *, status_code: int = 200):
    """Register a mock batchexecute response for a given RPC method."""
    httpx_mock.add_response(
        method="POST",
        url=re.compile(rf".*batchexecute.*rpcids={rpc_id}.*"),
        text=build_batchexecute_response(rpc_id, response_data),
        status_code=status_code,
    )
```

### Async Test Pattern

```python
@pytest.mark.asyncio
async def test_list_notebooks(mock_client, httpx_mock, mock_notebook_list_response):
    httpx_mock.add_response(
        method="POST",
        url=re.compile(r".*batchexecute.*rpcids=wXbhsf.*"),
        text=mock_notebook_list_response,
    )

    async with mock_client as client:
        api = NotebooksAPI(client)
        notebooks = await api.list()

    assert len(notebooks) == 2
    assert notebooks[0].title == "My First Notebook"
    assert notebooks[1].id == "notebook-id-2"
```

### Click CLI Test Pattern

```python
from click.testing import CliRunner
from notebooklm_cli.cli.main import cli

def test_notebook_list_json_output(mock_client, httpx_mock, mock_notebook_list_response):
    httpx_mock.add_response(...)

    runner = CliRunner()
    result = runner.invoke(cli, ["notebook", "list", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["title"] == "My First Notebook"
```

### VCR Cassette Pattern (for capturing/replaying real responses)

```python
import pytest
import vcr

@pytest.mark.vcr
@pytest.mark.e2e
async def test_list_notebooks_vcr():
    """Recorded against real API; replay without live credentials."""
    async with await NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()
    assert len(notebooks) >= 0
```

Cassettes stored in `tests/cassettes/` — committed to repo after initial capture.

### Fixture File Structure

```
tests/
├── fixtures/
│   ├── storage_state.json          # Mock Playwright storage state
│   ├── homepage.html               # Mock NotebookLM homepage with WIZ_global_data
│   ├── responses/
│   │   ├── list_notebooks.txt      # Raw batchexecute response
│   │   ├── create_notebook.txt
│   │   ├── add_source.txt
│   │   └── generate_audio.txt
│   └── uploads/
│       └── sample.pdf              # Small PDF for file upload tests
```

---

## 9. Auth End-to-End Verification

### Pre-Ship Auth Verification Checklist

Run these steps in order to confirm auth works fully before shipping:

**Step 1 — Cookie File Integrity**

```bash
python -c "
from notebooklm_cli.auth.cookies import load_cookies
from pathlib import Path
cookies = load_cookies(Path('~/.notebooklm/storage_state.json').expanduser())
required = {'SID', 'HSID', 'SSID', 'APISID', 'SAPISID'}
found = set(cookies.keys())
print('PASS: all required cookies present' if required <= found else f'FAIL: missing {required - found}')
"
```

**Step 2 — Token Extraction**

```bash
python -c "
import asyncio
from notebooklm_cli.auth.tokens import extract_tokens
from notebooklm_cli.auth.cookies import load_cookies
from pathlib import Path

async def check():
    cookies = load_cookies(Path('~/.notebooklm/storage_state.json').expanduser())
    tokens = await extract_tokens(dict(cookies))
    assert tokens.csrf_token, 'FAIL: SNlM0e empty'
    assert tokens.session_id, 'FAIL: FdrFJe empty'
    print(f'PASS: csrf={tokens.csrf_token[:20]}... session={tokens.session_id[:10]}...')

asyncio.run(check())
"
```

**Step 3 — Homepage Fetch (Session Valid)**

The homepage must return HTTP 200, not 302. A 302 means the session has expired.

```bash
python -c "
import asyncio, httpx
from notebooklm_cli.auth.cookies import load_cookies
from pathlib import Path

async def check():
    cookies = load_cookies(Path('~/.notebooklm/storage_state.json').expanduser())
    async with httpx.AsyncClient(cookies=cookies, follow_redirects=False) as client:
        resp = await client.get('https://notebooklm.google.com/')
    if resp.status_code == 200:
        print('PASS: session valid (HTTP 200)')
    elif resp.status_code == 302:
        print(f'FAIL: session expired (redirected to {resp.headers.get(\"location\")})')
    else:
        print(f'WARN: unexpected status {resp.status_code}')

asyncio.run(check())
"
```

**Step 4 — First Real RPC Call (LIST_NOTEBOOKS)**

```bash
notebooklm auth check --test
# Internally calls LIST_NOTEBOOKS and confirms a valid (possibly empty) response
```

Or directly:

```bash
python -c "
import asyncio
from notebooklm_cli.client import NotebookLMClient

async def check():
    async with await NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()
    print(f'PASS: listed {len(notebooks)} notebooks')

asyncio.run(check())
"
```

**Step 5 — CSRF Token Rotation Test**

Simulate token expiry to verify the auto-refresh path:

```python
# tests/e2e/test_auth.py

@pytest.mark.e2e
async def test_csrf_auto_refresh(tmp_storage):
    """Ensure the client recovers when SNlM0e is stale."""
    async with await NotebookLMClient.from_storage(tmp_storage) as client:
        # Corrupt the token
        client._core._tokens.csrf_token = "INVALID_CSRF_TOKEN"

        # This should trigger a refresh and succeed
        notebooks = await client.notebooks.list()
        assert isinstance(notebooks, list)

        # Verify token was refreshed
        assert client._core._tokens.csrf_token != "INVALID_CSRF_TOKEN"
```

**Step 6 — Session Expiry Error Message**

Manually verify the error message is user-friendly by simulating expired session:

```bash
NOTEBOOKLM_AUTH_JSON=/dev/null notebooklm notebook list
# Expected: "Error: Missing required cookies: {'SID', ...}. Run 'notebooklm login'."
# Expected exit code: 3
```

**Step 7 — Microsoft Edge SSO Path (Enterprise Users)**

If the target audience includes corporate users with Microsoft 365:

```bash
notebooklm login --browser msedge
# Must open Edge browser (not Chromium) and allow MSEdge's SSO to populate Google cookies
```

Verify storage state contains Google cookies from MSEdge session.

### Auth Verification in CI

For CI pipelines that run e2e tests, store the storage state as an encrypted secret:

```yaml
# .github/workflows/e2e.yml
env:
  NOTEBOOKLM_AUTH_JSON: ${{ secrets.NOTEBOOKLM_STORAGE_STATE }}
```

The CI job writes this to `~/.notebooklm/storage_state.json` before running e2e tests. Rotate the secret when sessions expire (typically every 2 weeks if the account isn't actively used).

---

## 10. Production Smoke Test

The final smoke test (`tests/e2e/test_smoke.py`) exercises the complete happy path end-to-end. It should pass before every release tag.

```python
# tests/e2e/test_smoke.py
"""
Full end-to-end smoke test covering the complete user journey.
Requires: NOTEBOOKLM_AUTH_JSON set to a valid storage state.

Run: pytest tests/e2e/test_smoke.py -v -m e2e --timeout=300
"""

import asyncio
import os
import time
import pytest
from pathlib import Path

from notebooklm_cli.client import NotebookLMClient
from notebooklm_cli.models.artifact import ArtifactType, GenerationStatus
from notebooklm_cli.models.source import SourceStatus

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

SMOKE_NOTEBOOK_TITLE = f"CLI Smoke Test {int(time.time())}"
SMOKE_SOURCE_URL = "https://en.wikipedia.org/wiki/Python_(programming_language)"
SMOKE_QUESTION = "What is Python used for?"

@pytest.fixture(scope="module")
async def smoke_client():
    """Module-scoped client for all smoke tests."""
    async with await NotebookLMClient.from_storage() as client:
        yield client

@pytest.fixture(scope="module")
async def smoke_notebook(smoke_client):
    """Create a notebook for the smoke test, delete it after."""
    notebook = await smoke_client.notebooks.create(SMOKE_NOTEBOOK_TITLE)
    yield notebook
    # Cleanup: always delete, even on test failure
    try:
        await smoke_client.notebooks.delete(notebook.id)
    except Exception:
        pass


class TestSmoke:

    async def test_01_auth_valid(self, smoke_client):
        """Auth tokens are present and homepage is reachable."""
        assert smoke_client._core._tokens.csrf_token
        assert smoke_client._core._tokens.session_id
        notebooks = await smoke_client.notebooks.list()
        assert isinstance(notebooks, list), "LIST_NOTEBOOKS returned non-list"

    async def test_02_notebook_created(self, smoke_notebook):
        """Notebook creation returns a valid ID."""
        assert smoke_notebook.id, "Notebook ID is empty"
        assert smoke_notebook.title == SMOKE_NOTEBOOK_TITLE

    async def test_03_notebook_in_list(self, smoke_client, smoke_notebook):
        """Newly created notebook appears in the list."""
        notebooks = await smoke_client.notebooks.list()
        ids = [nb.id for nb in notebooks]
        assert smoke_notebook.id in ids, "New notebook not in list"

    async def test_04_source_added(self, smoke_client, smoke_notebook):
        """URL source is added and reaches READY state within 60 seconds."""
        source = await smoke_client.sources.add_url(
            smoke_notebook.id,
            SMOKE_SOURCE_URL,
            wait=True,
            timeout=60,
        )
        assert source.id, "Source ID is empty"
        assert source.status == SourceStatus.READY, f"Source stuck in {source.status}"

    async def test_05_chat_works(self, smoke_client, smoke_notebook):
        """Chat returns a non-empty answer grounded in sources."""
        result = await smoke_client.chat.ask(smoke_notebook.id, SMOKE_QUESTION)
        assert result.answer, "Chat answer is empty"
        assert result.conversation_id, "No conversation ID returned"

    async def test_06_note_lifecycle(self, smoke_client, smoke_notebook):
        """Notes can be created, updated, listed, and deleted."""
        note = await smoke_client.notes.create(
            smoke_notebook.id, "Smoke Test Note", content="Initial content"
        )
        assert note.id, "Note ID is empty"

        await smoke_client.notes.update(note.id, smoke_notebook.id, content="Updated content")

        notes = await smoke_client.notes.list(smoke_notebook.id)
        note_ids = [n.id for n in notes]
        assert note.id in note_ids, "Note not found in list after creation"

        await smoke_client.notes.delete(note.id, smoke_notebook.id)

        notes_after = await smoke_client.notes.list(smoke_notebook.id)
        assert note.id not in [n.id for n in notes_after], "Note still present after deletion"

    async def test_07_audio_generation_initiated(self, smoke_client, smoke_notebook):
        """Audio overview generation can be initiated (does not wait for completion)."""
        status = await smoke_client.artifacts.generate_audio(smoke_notebook.id)
        assert status.task_id or status.artifact_id, "No task/artifact ID returned from generate"
        # Note: full audio generation takes 2-5 minutes; smoke test only verifies job accepted

    async def test_08_artifact_listed(self, smoke_client, smoke_notebook):
        """Artifact list is accessible (may be empty or have in-progress items)."""
        artifacts = await smoke_client.artifacts.list(smoke_notebook.id)
        assert isinstance(artifacts, list), "Artifact list is not a list"

    async def test_09_notebook_renamed(self, smoke_client, smoke_notebook):
        """Notebook can be renamed."""
        new_title = f"{SMOKE_NOTEBOOK_TITLE} (renamed)"
        await smoke_client.notebooks.rename(smoke_notebook.id, new_title)
        nb = await smoke_client.notebooks.get(smoke_notebook.id)
        assert nb.title == new_title, f"Rename did not apply: got '{nb.title}'"

    async def test_10_cli_entrypoint_works(self):
        """The installed CLI binary responds to --help."""
        import subprocess
        result = subprocess.run(
            ["notebooklm", "--help"], capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0
        assert "Usage:" in result.stdout

    async def test_11_cli_json_output_parseable(self):
        """CLI --json output for notebook list is valid JSON."""
        import subprocess, json
        result = subprocess.run(
            ["notebooklm", "notebook", "list", "--json"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"CLI exited {result.returncode}: {result.stderr}"
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    async def test_12_error_handling(self, smoke_client):
        """Querying a non-existent notebook raises NotebookNotFoundError, not a crash."""
        from notebooklm_cli.exceptions import NotebookNotFoundError
        with pytest.raises(NotebookNotFoundError):
            await smoke_client.notebooks.get("nonexistent-notebook-id-000")
```

### Running the Smoke Test

```bash
# Full smoke test with verbose output and 5-minute timeout
NOTEBOOKLM_AUTH_JSON=~/.notebooklm/storage_state.json \
  pytest tests/e2e/test_smoke.py \
  -v \
  -m e2e \
  --timeout=300 \
  --tb=short

# Expected output:
# tests/e2e/test_smoke.py::TestSmoke::test_01_auth_valid PASSED
# tests/e2e/test_smoke.py::TestSmoke::test_02_notebook_created PASSED
# ...
# tests/e2e/test_smoke.py::TestSmoke::test_12_error_handling PASSED
# 12 passed in 45.3s
```

### Declaring Production-Ready

The CLI is production-ready when all of the following are true:

1. `pytest tests/unit/ -v` — 0 failures, coverage >= 90%
2. `pytest tests/integration/ -v` — 0 failures
3. `pytest tests/e2e/test_smoke.py -v -m e2e` — all 12 tests pass against live API
4. `notebooklm --help` renders without error
5. `notebooklm auth check --test` returns exit code 0
6. The `build_label` (`bl=` parameter) in `http/client.py` matches the current value served by `https://notebooklm.google.com/` (run `scripts/update_build_label.py` to verify)
7. `mypy src/` — 0 type errors
8. `ruff check src/ tests/` — 0 lint errors
9. Manual test of `notebooklm source add <nb-id> <pdf-path>` with a real PDF file
10. Manual test of `notebooklm generate audio <nb-id> --wait` through full completion

---

## Appendix: Key Implementation Notes

### Build Label Staleness

The `bl=` query parameter (build label, e.g., `boq_labs-tailwind-frontend_20240101.00_p0`) is served by the NotebookLM page and changes with deployments. While Google typically ignores a stale value, a mismatch can cause 400 errors. The `update_build_label.py` script should run in CI before releases:

```python
# scripts/update_build_label.py
import re, httpx, asyncio

async def get_build_label():
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://notebooklm.google.com/")
        match = re.search(r'"bl":"([^"]+)"', resp.text)
        if match:
            print(f"Current build label: {match.group(1)}")
```

### Rate Limiting Strategy

Google's batchexecute endpoint rate-limits by session. Safe usage patterns:
- Never send more than 1 request per second from a single session
- Back off exponentially starting at 5 seconds on `429` or `UserDisplayableError`
- For batch operations (e.g., adding many sources), add `asyncio.sleep(1)` between calls
- Use `--wait` for source processing rather than tight polling loops

### RPC Method ID Stability

The alphanumeric method IDs (e.g., `CCqFvf`) are compiler-generated obfuscated identifiers from Google's internal Closure Compiler build system. They are **not stable across deployments** — they can change when Google pushes a new build. The `scripts/update_build_label.py` approach should be extended to also re-verify method IDs by capturing a fresh batchexecute request for each operation after each build change. A fallback mechanism could store alternative method IDs and try them in sequence on `UnknownRPCMethodError`.

### Note Creation Quirk

Due to a known API quirk, creating a note requires two sequential RPC calls:

```python
async def create_note(self, notebook_id: str, title: str, content: str) -> Note:
    # Step 1: CREATE_NOTE — returns note_id but ignores title/content
    result = await self._client.rpc("CYK0Xb", [[notebook_id, None]], notebook_id=notebook_id)
    note_id = result[0][0]

    # Step 2: UPDATE_NOTE — sets actual title and content
    await self._client.rpc(
        "cYAfTb",
        [[notebook_id, note_id, title, content]],
        notebook_id=notebook_id,
    )

    return Note(id=note_id, title=title, content=content, notebook_id=notebook_id)
```

### Chat Streaming

The chat endpoint is not batchexecute — it's a gRPC-Web streaming endpoint. The response is a series of newline-delimited JSON objects, each containing a partial token delta or a final grounding reference list:

```python
# http/streaming.py

async def stream_chat_response(client: httpx.AsyncClient, payload: dict):
    async with client.stream(
        "POST",
        "/_/LabsTailwindUi/data/google.internal.labs.tailwind.orchestration.v1.LabsTailwindOrchestrationService/GenerateFreeFormStreamed",
        json=payload,
    ) as response:
        buffer = ""
        async for chunk in response.aiter_text():
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line.strip():
                    yield parse_chat_chunk(line)
```
