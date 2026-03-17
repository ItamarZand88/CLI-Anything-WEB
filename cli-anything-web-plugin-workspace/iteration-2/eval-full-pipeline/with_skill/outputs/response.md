# cli-web-notebooklm — Complete Implementation Plan

**Target:** https://notebooklm.google.com/
**CLI package:** `cli_web.notebooklm`
**CLI command:** `cli-web-notebooklm`
**Date:** 2026-03-15

---

## Overview

Google NotebookLM is a browser-based research assistant that lets users create notebooks,
upload sources (PDFs, URLs, text), query those sources via chat, manage notes, and generate
audio overviews ("podcasts"). It uses Google's batchexecute RPC protocol — not a public
REST API. This plan covers all 8 phases of the CLI-Anything-Web pipeline.

---

## Phase 1 — Record (Traffic Capture)

### Prerequisites

Launch Chrome with the dedicated debug profile (already authenticated with a Google account):

```bash
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" \
  --remote-debugging-port=9222 \
  --user-data-dir="%USERPROFILE%\.chrome-debug-profile"
```

Navigate to `https://notebooklm.google.com/` in that window and confirm the notebook list
loads (not a login screen). The `.mcp.json` in the plugin root points chrome-devtools-mcp
at port 9222.

### Capture Sequence

Using Chrome DevTools MCP, perform the following sequence systematically. For each action,
record the full request (method, URL, headers, body) and response (status, body):

**1. Load home page — notebook list:**
- Navigate to `https://notebooklm.google.com/`
- Capture the initial `batchexecute` call that loads the notebook list
- Note the `rpcids` value (expected: `wXbhsf` based on known pattern)
- Save full response including the `)]}'\n` prefix

**2. Create a notebook:**
- Click "New notebook" in the UI
- Capture the POST to `batchexecute` that creates the notebook
- Note `rpcids` (expected: `CCqFvf`)
- Record the request body's `f.req` parameter structure
- Record the response including the new notebook ID

**3. Open a notebook:**
- Click on the created notebook
- Capture any `batchexecute` call that fetches notebook details
- Note `rpcids` (expected: `rLM1Ne`)
- Record the full notebook object schema (ID, title, source list, notes list)

**4. Add a URL source:**
- Inside the notebook, click "Add source" → "Website"
- Enter a real URL (e.g., `https://en.wikipedia.org/wiki/Python_(programming_language)`)
- Capture the POST to `batchexecute`
- Note `rpcids` (expected: `izAoDd` or similar)
- Record source schema in response

**5. Add a PDF source:**
- Click "Add source" → "PDF" and upload a file
- The upload likely uses a different endpoint (multipart form or Google Drive API)
- Capture BOTH the upload request AND the subsequent batchexecute call that registers it
- Note all relevant `rpcids` values

**6. Add a text/paste source:**
- Click "Add source" → "Copied text"
- Paste sample text, submit
- Capture the `batchexecute` call and note `rpcids`

**7. List sources in a notebook:**
- If there is a separate "load sources" call, capture it
- Otherwise note whether sources are included in the notebook detail response (GET notebook)

**8. Query/chat:**
- In the chat panel, type a question and submit
- Capture the streaming or chunked batchexecute response
- Note `rpcids` (expected: `GenerateFreeFormStreamed` or similar)
- Record the full streamed response format (multiple length-prefixed chunks)

**9. Create a note:**
- Click "Add note" or equivalent
- Capture the `batchexecute` POST
- Note `rpcids`
- Record note schema (ID, content, timestamps)

**10. Update a note:**
- Edit an existing note
- Capture the `batchexecute` PUT/POST
- Note `rpcids`

**11. Delete a note:**
- Delete a note
- Capture the `batchexecute` POST
- Note `rpcids`

**12. Delete a source:**
- Remove a source from a notebook
- Capture the `batchexecute` POST
- Note `rpcids`

**13. Generate audio overview:**
- Click "Generate audio overview" (or "Create podcast")
- Capture the `batchexecute` call that triggers generation
- Also capture the polling/status call if generation is async
- Note both `rpcids` values

**14. Delete a notebook:**
- Delete the test notebook
- Capture the `batchexecute` POST
- Note `rpcids`

**15. Rename a notebook:**
- Create another notebook, rename it
- Capture the `batchexecute` POST
- Note `rpcids`

### What to Capture for Each Request

For each batchexecute call, record:
- Full URL including all query parameters (`rpcids`, `f.sid`, `bl`, `source-path`, `_reqid`)
- Request headers (especially `x-same-domain`, `Content-Type`, `Cookie`, `Origin`, `Referer`)
- Raw request body (the `f.req=...&at=...` form data, URL-decoded)
- Full response body (including `)]}'\n` prefix and all length-prefixed chunks)
- The page URL at the time of the request (for `source-path` context)

Also capture the NotebookLM homepage HTML:
- The full `<script>` block containing `WIZ_global_data` (source of `SNlM0e` CSRF token and `FdrFJe` session ID)

### Filtering Rules

Filter OUT (do not record):
- `*.js`, `*.css`, `*.png`, `*.woff`, `*.ico` — static assets
- Google Analytics, Tag Manager, and telemetry (`/collect`, `/analytics.js`, etc.)
- CDN resources from `gstatic.com`, `fonts.googleapis.com`
- Preflight CORS requests

Filter IN (record all of these):
- Any URL containing `batchexecute`
- Any URL containing `/notebook/`
- Upload endpoints (`upload.google.com` or `/upload/`)

### Output

Save all captured traffic to:
`notebooklm/traffic-capture/raw-traffic.json`

This file is a JSON array where each entry has:
```json
{
  "action": "create_notebook",
  "request": { "method": "POST", "url": "...", "headers": {...}, "body": "..." },
  "response": { "status": 200, "headers": {...}, "body": "..." }
}
```

---

## Phase 2 — Analyze (API Discovery)

### RPC Protocol Identification

After reviewing `raw-traffic.json`, the detection signals will confirm Google batchexecute:

- URLs contain `/_/LabsNotebookUi/data/batchexecute` (the service name may vary — capture the exact service name from traffic)
- All writes use `POST` with `Content-Type: application/x-www-form-urlencoded`
- Request bodies contain `f.req=` with triple-nested JSON arrays
- URLs carry `rpcids=<method_id>` query parameters
- Responses begin with `)]}'\n` anti-XSSI prefix followed by length-prefixed JSON chunks

This is **not** REST, **not** GraphQL, **not** gRPC-Web. It is Google batchexecute. This
determines the architecture for Phase 4: a `core/rpc/` subpackage is required.

### RPC Method ID Inventory

Map each captured action to its `rpcids` value. The table below shows expected method IDs
based on known patterns (actual values must be confirmed from captured traffic — they may
differ from these estimates):

| User Action | Expected rpcids | CLI Command |
|---|---|---|
| List all notebooks | `wXbhsf` | `notebooks list` |
| Create notebook | `CCqFvf` | `notebooks create` |
| Get notebook details | `rLM1Ne` | `notebooks get` |
| Rename notebook | (capture) | `notebooks rename` |
| Delete notebook | (capture) | `notebooks delete` |
| Add URL source | `izAoDd` | `sources add-url` |
| Add PDF source | (capture, may use upload API) | `sources add-pdf` |
| Add text source | (capture) | `sources add-text` |
| List sources | (may be embedded in GET notebook) | `sources list` |
| Delete source | (capture) | `sources delete` |
| Send chat query | `GenerateFreeFormStreamed` | `chat ask` |
| Create note | (capture) | `notes create` |
| Update note | (capture) | `notes update` |
| Delete note | (capture) | `notes delete` |
| List notes | (may be embedded in GET notebook) | `notes list` |
| Generate audio overview | (capture) | `audio generate` |
| Get audio status | (capture, if async) | `audio status` |

**Important:** These must be verified against captured traffic. The `rpcids` values are
opaque identifiers that Google can change between deployments — always source them from
live traffic, never assume.

### Request Body Schema

Decode each captured `f.req` value. The triple-nested structure is:
```
[[[ rpc_id, json.dumps(params), null, "generic" ]]]
```

Document the `params` structure for each method, e.g.:
- List notebooks: `[null, 1, null, [2]]` (pagination token in position 1)
- Create notebook: `["My Title", null, []]` (title, description, source list)
- Add source URL: `[notebook_id, url, null, "website"]`
- Chat ask: `[notebook_id, "question text", chat_history]`

### Response Body Schema

After stripping the anti-XSSI prefix and parsing length-prefixed chunks, extract the
`wrb.fr` entry matching the `rpcids`. The inner value is a JSON string requiring a second
`json.loads()` call.

Document the decoded schema for each response:
- Notebook object: `{ id, title, source_ids, note_ids, created_at, updated_at }`
- Source object: `{ id, type, title, url, created_at }`
- Chat response: `{ text, citations: [{ source_id, excerpt }] }`
- Note object: `{ id, content, created_at, updated_at }`
- Audio overview: `{ id, status, audio_url, transcript }`

### Auth Pattern Analysis

NotebookLM uses **Browser-Delegated Auth** (the hardest category):

- HTTP login is blocked by CAPTCHA/JavaScript challenges — standard credential posting does not work
- Session cookies (`SID`, `HSID`, `SSID`, `APISID`, `SAPISID`, `__Secure-1PSID`, etc.) are stored in the Chrome profile
- Two additional tokens must be extracted from page HTML each session:
  - `SNlM0e` — CSRF token used as `at=` in request body
  - `FdrFJe` — Session ID used as `f.sid=` in URL parameters
- These tokens change per session and per deployment (`bl` build label also changes)

**Critical headers identified from traffic:**
- `x-same-domain: 1` — mandatory, Google rejects requests without it
- `Content-Type: application/x-www-form-urlencoded;charset=UTF-8`
- `Origin: https://notebooklm.google.com`
- `Referer: https://notebooklm.google.com/`
- `Cookie: SID=...; HSID=...; SSID=...; APISID=...; SAPISID=...; __Secure-1PSID=...` (and others)

**Note on cookie deduplication:** The Chrome profile may contain cookies for both
`.google.com` and `accounts.google.com`. When extracting, prefer `.google.com` domain
cookies to avoid `CookieMismatch` errors.

### PDF Upload Analysis

PDF upload likely uses a separate flow:
1. Upload to `upload.google.com` or a resumable upload endpoint — yields a resource ID
2. Register the resource with the notebook via a batchexecute call using that resource ID

Document the upload URL pattern, required headers (`X-Goog-Upload-*`), and the subsequent
registration call's schema.

### Data Model

```
Notebook
  id: string (opaque)
  title: string
  created_at: timestamp
  updated_at: timestamp
  sources: Source[]
  notes: Note[]

Source
  id: string
  notebook_id: string
  type: "url" | "pdf" | "text"
  title: string
  url: string | null
  created_at: timestamp

Note
  id: string
  notebook_id: string
  content: string
  created_at: timestamp
  updated_at: timestamp

AudioOverview
  id: string
  notebook_id: string
  status: "generating" | "ready" | "failed"
  audio_url: string | null
  transcript: string | null
```

### Output

Write `NOTEBOOKLM.md` — the app-specific SOP — with:
- Full API map (all batchexecute endpoints with decoded schemas)
- Complete data model
- Auth scheme (browser-delegated, cookie + token extraction)
- PDF upload flow
- Chat streaming format
- Anti-bot observations

---

## Phase 3 — Design (CLI Architecture)

### Complete CLI Command Tree

```
cli-web-notebooklm                          # REPL mode (default, no subcommand)
cli-web-notebooklm --help
cli-web-notebooklm --json <subcommand>      # --json flag available on all commands

# Auth management
cli-web-notebooklm auth login               # Playwright: open browser, user logs in
cli-web-notebooklm auth login --from-browser  # CDP: extract from debug Chrome (port 9222)
cli-web-notebooklm auth login --cookies-json <file>  # Manual: import from JSON file
cli-web-notebooklm auth status              # Show cookies, CSRF token, session ID validity
cli-web-notebooklm auth refresh             # Re-fetch CSRF + session tokens via HTTP GET

# Notebooks
cli-web-notebooklm notebooks list           # List all notebooks
cli-web-notebooklm notebooks get --id <id>  # Get notebook details (sources, notes)
cli-web-notebooklm notebooks create --title <title>
cli-web-notebooklm notebooks rename --id <id> --title <new-title>
cli-web-notebooklm notebooks delete --id <id>

# Sources
cli-web-notebooklm sources list --notebook-id <id>
cli-web-notebooklm sources add-url --notebook-id <id> --url <url>
cli-web-notebooklm sources add-pdf --notebook-id <id> --file <path>
cli-web-notebooklm sources add-text --notebook-id <id> --text <text>
cli-web-notebooklm sources add-text --notebook-id <id> --text-file <path>  # read from file
cli-web-notebooklm sources delete --notebook-id <id> --source-id <id>

# Chat
cli-web-notebooklm chat ask --notebook-id <id> --question <text>
cli-web-notebooklm chat ask --notebook-id <id> --question <text> --stream  # streaming output
cli-web-notebooklm chat history --notebook-id <id>  # if supported by API

# Notes
cli-web-notebooklm notes list --notebook-id <id>
cli-web-notebooklm notes create --notebook-id <id> --content <text>
cli-web-notebooklm notes update --notebook-id <id> --note-id <id> --content <text>
cli-web-notebooklm notes delete --notebook-id <id> --note-id <id>

# Audio overviews
cli-web-notebooklm audio generate --notebook-id <id>
cli-web-notebooklm audio status --notebook-id <id>
cli-web-notebooklm audio download --notebook-id <id> --out <path>
```

### Auth Design

Auth uses the Browser-Delegated pattern. Three login methods are required:

**Method 1: `auth login` (Playwright — default for end users)**
Opens a headless-off Chromium instance. User logs into Google manually. Playwright saves
`storage_state.json` with full cookie metadata. Requires `pip install playwright` and
`playwright install chromium`. Declared as optional dependency under `[browser]` extra.

**Method 2: `auth login --from-browser` (CDP — for dev/pipeline)**
Connects to Chrome debug profile on port 9222 via WebSockets CDP. Issues
`Storage.getCookies` for `notebooklm.google.com` domain. Deduplicates cookies: prefers
`.google.com` over `accounts.google.com` for any cookie name collision. Then immediately
performs Phase B: HTTP GET to homepage with those cookies to extract `SNlM0e` and `FdrFJe`.

**Method 3: `auth login --cookies-json <file>` (manual fallback)**
Imports cookies from a JSON file (e.g., exported via a browser extension). Validates
required cookie names are present, then runs Phase B token extraction.

**Auth storage:** `~/.config/cli-web-notebooklm/auth.json` with `chmod 600`

```json
{
  "cookies": { "SID": "...", "HSID": "...", "SSID": "...", "__Secure-1PSID": "...", "..." },
  "csrf_token": "AIXQIk...",
  "session_id": "394392219...",
  "build_label": "notebooklm.frontend.prod-2026-03-15.12_p0",
  "extracted_at": "2026-03-15T12:00:00Z"
}
```

**`auth status` output:**
```
Cookies:        12 cookies present (SID, HSID, SSID, ...)
CSRF token:     present (AIXQIk...)
Session ID:     present (394392219...)
Live validation: OK (200, got 3 notebooks)
```

**Auto-refresh on 401:**
When a batchexecute call returns 401 or 403, the client:
1. Re-fetches `https://notebooklm.google.com/` with current cookies
2. Parses new `SNlM0e` and `FdrFJe` from the HTML
3. Updates the in-memory token cache and `auth.json`
4. Retries the failed request once

### REPL Design

- Invoked when `cli-web-notebooklm` is called with no subcommand
- Uses `ReplSkin` from `utils/repl_skin.py` (copied from plugin)
- Branded banner: `NotebookLM CLI` with version
- Context-aware prompt: `notebooklm [notebook: My Research] > ` when a notebook is active
- REPL supports setting active notebook context: `use <notebook-id>` sets `session.current_notebook_id`
- Subsequent commands in REPL can omit `--notebook-id` if context is set

### Session State Design

`session.py` holds:
- `current_notebook_id: str | None`
- `undo_stack: list[dict]` — records mutating operations with enough info to reverse them
- `output_format: str` — "table" or "json"

### Output Format

Every command:
- Without `--json`: pretty-printed tables using `rich` or `tabulate`
- With `--json`: clean JSON to stdout (no extra text)
- Errors: always to stderr, never to stdout

---

## Phase 4 — Implement (Code Generation)

### Package Structure

```
notebooklm/
└── agent-harness/
    ├── NOTEBOOKLM.md
    ├── setup.py
    └── cli_web/                          # NO __init__.py (namespace package)
        └── notebooklm/
            ├── __init__.py
            ├── __main__.py
            ├── README.md
            ├── notebooklm_cli.py         # Main Click entry point
            ├── core/
            │   ├── __init__.py
            │   ├── client.py             # High-level API (delegates to rpc/)
            │   ├── auth.py               # Cookie + token management, 3 login methods
            │   ├── session.py            # State + undo/redo
            │   ├── models.py             # Typed dataclasses (Notebook, Source, Note, etc.)
            │   └── rpc/
            │       ├── __init__.py       # Public: encode_request, decode_response
            │       ├── types.py          # RPCMethod enum, URL constants
            │       ├── encoder.py        # encode_rpc_request(), build_request_body()
            │       └── decoder.py        # strip_prefix(), parse_chunks(), extract_result()
            ├── commands/
            │   ├── __init__.py
            │   ├── auth_cmds.py          # auth login/status/refresh
            │   ├── notebooks.py          # notebooks list/get/create/rename/delete
            │   ├── sources.py            # sources list/add-url/add-pdf/add-text/delete
            │   ├── chat.py               # chat ask/history
            │   ├── notes.py              # notes list/create/update/delete
            │   └── audio.py              # audio generate/status/download
            ├── utils/
            │   ├── __init__.py
            │   ├── repl_skin.py          # Copied from plugin scripts/repl_skin.py
            │   ├── output.py             # JSON/table formatting
            │   └── config.py             # Config file path management
            └── tests/
                ├── __init__.py
                ├── TEST.md
                ├── fixtures/
                │   ├── list_notebooks.json
                │   ├── get_notebook.json
                │   ├── create_notebook.json
                │   ├── add_source_url.json
                │   ├── chat_ask.json
                │   ├── create_note.json
                │   └── generate_audio.json
                ├── test_core.py
                └── test_e2e.py
```

### Module Specifications

**`core/rpc/types.py`**

```python
class RPCMethod:
    LIST_NOTEBOOKS = "wXbhsf"       # verify from captured traffic
    CREATE_NOTEBOOK = "CCqFvf"      # verify from captured traffic
    GET_NOTEBOOK = "rLM1Ne"         # verify from captured traffic
    RENAME_NOTEBOOK = "..."         # fill from captured traffic
    DELETE_NOTEBOOK = "..."         # fill from captured traffic
    ADD_SOURCE = "izAoDd"           # verify from captured traffic
    DELETE_SOURCE = "..."           # fill from captured traffic
    CHAT_ASK = "GenerateFreeFormStreamed"  # verify from captured traffic
    CREATE_NOTE = "..."             # fill from captured traffic
    UPDATE_NOTE = "..."             # fill from captured traffic
    DELETE_NOTE = "..."             # fill from captured traffic
    LIST_NOTES = "..."              # fill from captured traffic
    GENERATE_AUDIO = "..."          # fill from captured traffic
    GET_AUDIO_STATUS = "..."        # fill from captured traffic

BASE_URL = "https://notebooklm.google.com"
BATCHEXECUTE_PATH = "/_/LabsNotebookUi/data/batchexecute"  # verify exact service name
```

**`core/rpc/encoder.py`**

```python
import json
import urllib.parse

def encode_rpc_request(rpc_id: str, params: list) -> str:
    """Encode params into triple-nested f.req format."""
    inner = [rpc_id, json.dumps(params), None, "generic"]
    return json.dumps([[inner]])

def build_request_body(rpc_id: str, params: list, csrf_token: str) -> str:
    """Return URL-encoded form body: f.req=...&at=..."""
    freq = encode_rpc_request(rpc_id, params)
    return urllib.parse.urlencode({"f.req": freq, "at": csrf_token})

def build_url(path: str, rpc_id: str, session_id: str, build_label: str, reqid: int) -> str:
    """Construct the full batchexecute URL."""
    params = urllib.parse.urlencode({
        "rpcids": rpc_id,
        "source-path": path,
        "f.sid": session_id,
        "bl": build_label,
        "hl": "en",
        "_reqid": reqid,
        "rt": "c",
    })
    return f"{BASE_URL}{BATCHEXECUTE_PATH}?{params}"
```

**`core/rpc/decoder.py`**

```python
import json

def strip_prefix(text: str) -> str:
    if text.startswith(")]}'"):
        return text[4:].lstrip("\n")
    return text

def parse_chunks(text: str) -> list[str]:
    """Parse length-prefixed response into list of chunk strings."""
    chunks = []
    pos = 0
    while pos < len(text):
        while pos < len(text) and text[pos] in " \t\r\n":
            pos += 1
        if pos >= len(text):
            break
        count_start = pos
        while pos < len(text) and text[pos].isdigit():
            pos += 1
        if pos == count_start:
            break
        chunk_len = int(text[count_start:pos])
        if pos < len(text) and text[pos] == "\n":
            pos += 1
        chunks.append(text[pos:pos + chunk_len])
        pos += chunk_len
    return chunks

def extract_result(response_text: str, rpc_id: str):
    """Full decode pipeline: strip prefix → parse chunks → find wrb.fr entry."""
    text = strip_prefix(response_text)
    chunks = parse_chunks(text)
    for chunk in chunks:
        try:
            outer = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        for entry in outer:
            if isinstance(entry, list) and len(entry) >= 3:
                if entry[0] == "wrb.fr" and entry[1] == rpc_id:
                    return json.loads(entry[2])   # double decode
                if entry[0] == "er":
                    raise RPCError(f"RPC error for {rpc_id}: {entry}")
    raise RPCError(f"No result found for rpcid={rpc_id}")
```

**`core/auth.py`**

Three login methods, token extraction, storage, auto-refresh:

```python
class NotebookLMAuth:
    CONFIG_DIR = Path.home() / ".config" / "cli-web-notebooklm"
    AUTH_FILE = CONFIG_DIR / "auth.json"
    REQUIRED_COOKIES = ["SID", "HSID", "SSID"]

    def login_playwright(self):
        """Method 1: Open browser, user logs in, save storage_state."""

    def login_from_browser(self, port: int = 9222):
        """Method 2: Extract cookies via CDP from debug Chrome."""
        # Connect to ws://localhost:9222/json to get page list
        # Use Storage.getCookies for notebooklm.google.com
        # Deduplicate: prefer .google.com over accounts.google.com
        # Then run _fetch_tokens() using those cookies

    def login_cookies_json(self, path: Path):
        """Method 3: Import cookies from JSON file."""
        # Load JSON, validate required cookie names present
        # Then run _fetch_tokens()

    def _fetch_tokens(self, cookies: dict):
        """HTTP GET to homepage, extract SNlM0e and FdrFJe."""
        # If HTTP GET redirects (anti-bot), fall back to CDP JS eval:
        # window.WIZ_global_data.SNlM0e, window.WIZ_global_data.FdrFJe

    def _save(self, data: dict):
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.AUTH_FILE.write_text(json.dumps(data, indent=2))
        self.AUTH_FILE.chmod(0o600)

    def load(self) -> dict:
        if not self.AUTH_FILE.exists():
            raise AuthError("Not authenticated. Run: cli-web-notebooklm auth login")
        return json.loads(self.AUTH_FILE.read_text())

    def refresh_tokens(self):
        """Re-fetch CSRF + session tokens. Called on 401."""
        data = self.load()
        self._fetch_tokens(data["cookies"])
```

**`core/client.py`**

```python
class NotebookLMClient:
    def __init__(self, auth: NotebookLMAuth):
        self.auth = auth
        self._reqid = 100000

    def call(self, rpc_id: str, params: list, source_path: str = "/"):
        data = self.auth.load()
        url = build_url(source_path, rpc_id, data["session_id"], data["build_label"], self._reqid)
        self._reqid += 87654  # increment like browser does
        body = build_request_body(rpc_id, params, data["csrf_token"])
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "x-same-domain": "1",
            "Origin": "https://notebooklm.google.com",
            "Referer": "https://notebooklm.google.com/",
            "Cookie": _cookie_header(data["cookies"]),
        }
        resp = httpx.post(url, content=body, headers=headers)
        if resp.status_code in (401, 403):
            self.auth.refresh_tokens()
            data = self.auth.load()
            # rebuild url and body with fresh tokens, retry once
            ...
        resp.raise_for_status()
        return extract_result(resp.text, rpc_id)
```

### Parallelization Plan for Phase 4

**Step 1 (sequential, write first):** Core foundation that all commands depend on:
1. `core/rpc/types.py` — method IDs from captured traffic
2. `core/rpc/encoder.py` — request encoding
3. `core/rpc/decoder.py` — response decoding
4. `core/auth.py` — authentication (3 login methods)
5. `core/models.py` — typed dataclasses
6. `core/client.py` — HTTP layer (depends on rpc/ and auth)
7. `core/session.py` — state management
8. `utils/config.py`, `utils/output.py`, `utils/repl_skin.py` (copy from plugin)

**Step 2 (parallel subagents):** All command modules are independent of each other.
Each only imports from `core/`. Dispatch simultaneously:

| Subagent | Module | Commands to implement |
|---|---|---|
| Agent 1 | `commands/notebooks.py` | list, get, create, rename, delete |
| Agent 2 | `commands/sources.py` | list, add-url, add-pdf, add-text, delete |
| Agent 3 | `commands/chat.py` | ask (with streaming option), history |
| Agent 4 | `commands/notes.py` | list, create, update, delete |
| Agent 5 | `commands/audio.py` | generate, status, download |
| Agent 6 | `commands/auth_cmds.py` | login (3 methods), status, refresh |

Each agent receives: `NOTEBOOKLM.md` (API spec), `core/client.py` interface, `core/models.py`
schemas, and their specific batchexecute method IDs and params structures from Phase 2.

**Step 3 (sequential, write last):** Wire everything together:
1. `notebooklm_cli.py` — imports all command groups, registers them on main Click group
2. `__main__.py` — `from cli_web.notebooklm.notebooklm_cli import main; main()`
3. `setup.py` — packaging config

**Encoder details:**

The encoder must handle the triple-nested structure exactly. Special care:
- `json.dumps(params)` is called on the inner params array before embedding it as a string
- The outer structure is then JSON-serialized as a whole
- URL encoding is applied to the entire value of `f.req`
- The `at` CSRF token is never URL-encoded beyond what `urllib.parse.urlencode` applies

**Decoder details:**

- Strip `)]}'\n` prefix first (exactly 4 characters plus newline)
- Parse length-prefixed chunks: each chunk is a decimal byte count on its own line, followed by that many bytes of JSON
- For each chunk, `json.loads()` the outer array, then scan for `entry[0] == "wrb.fr"` and `entry[1] == rpc_id`
- The matching entry's `entry[2]` is a JSON string — apply a second `json.loads()` to get the actual result
- Error entries have `entry[0] == "er"` — raise `RPCError`
- Streaming chat responses may arrive as multiple chunks — accumulate text across all matching entries

**Anti-bot resilience:**

- Never hardcode `f.sid`, `bl`, `at` — always extract dynamically
- The `bl` build label must be extracted from the homepage HTML alongside CSRF/session tokens:
  `re.search(r'"cfb2h"\s*:\s*"([^"]+)"', html)` (key may vary — confirm from traffic)
- If homepage GET redirects (status 302 to accounts.google.com), switch to CDP fallback:
  evaluate `JSON.stringify(window.WIZ_global_data)` in Chrome tab and parse the result
- The `_reqid` counter starts at a random large number (like browsers do) and increments by a
  fixed amount per request — use the increment pattern observed in captured traffic

**PDF upload specifics:**

PDF upload is a two-phase operation that may differ from batchexecute:
1. Upload phase: `POST` to a Google upload endpoint with `Content-Type: multipart/form-data`
   Captures the `upload_id` or resource reference from response
2. Register phase: `POST` to `batchexecute` with the upload reference to attach it to a notebook

The `sources add-pdf` command handles both phases transparently, with a progress indicator
for large files.

**`setup.py`:**

```python
from setuptools import setup, find_namespace_packages

setup(
    name="cli-web-notebooklm",
    version="0.1.0",
    packages=find_namespace_packages(include=["cli_web.*"]),
    install_requires=["click>=8.0", "httpx>=0.24.0", "websockets>=11.0"],
    extras_require={"browser": ["playwright>=1.40.0"]},
    entry_points={"console_scripts": ["cli-web-notebooklm=cli_web.notebooklm.notebooklm_cli:main"]},
    python_requires=">=3.10",
)
```

---

## Phase 5 — Plan Tests (TEST.md Part 1)

This document would be written to `cli_web/notebooklm/tests/TEST.md` BEFORE any test code.

### Test Inventory

| File | Type | Planned Count |
|---|---|---|
| `test_core.py` | Unit tests (mocked HTTP) | ~45 tests |
| `test_e2e.py` | E2E fixture replay tests | ~15 tests |
| `test_e2e.py` | E2E live tests (real API) | ~20 tests |
| `test_e2e.py` | CLI subprocess tests | ~10 tests |
| **Total** | | **~90 tests** |

### Unit Test Plan (test_core.py)

**Module: `core/rpc/encoder.py`** (~10 tests)
- Functions: `encode_rpc_request`, `build_request_body`, `build_url`
- Cases:
  - `encode_rpc_request("wXbhsf", [None, 1, None, [2]])` produces exact expected JSON string
  - Triple nesting: verify outer is `[[...]]`, inner first element is rpc_id
  - `build_request_body` produces URL-encoded string with `f.req=` and `at=` fields
  - `build_url` includes all required query parameters: `rpcids`, `f.sid`, `bl`, `_reqid`, `rt=c`
  - `_reqid` increments between successive calls
  - Special characters in params are properly JSON-escaped

**Module: `core/rpc/decoder.py`** (~12 tests)
- Functions: `strip_prefix`, `parse_chunks`, `extract_result`
- Cases:
  - `strip_prefix` removes `)]}'\n` correctly from real captured response
  - `strip_prefix` is idempotent if prefix absent
  - `parse_chunks` correctly splits multi-chunk response (load `fixtures/list_notebooks.json`)
  - `parse_chunks` handles trailing whitespace and newlines
  - `extract_result` finds the correct `wrb.fr` entry when multiple entries in response
  - `extract_result` applies double JSON decode to `entry[2]`
  - `extract_result` raises `RPCError` on `"er"` entry
  - `extract_result` raises `RPCError` when no matching `wrb.fr` entry found
  - Empty response handling
  - Malformed JSON chunk handling

**Module: `core/auth.py`** (~12 tests)
- Functions: `_fetch_tokens`, `_save`, `load`, `refresh_tokens`, `login_cookies_json`
- Cases:
  - `_fetch_tokens` parses `SNlM0e` and `FdrFJe` from realistic HTML fixture
  - `_fetch_tokens` raises `AuthError` when tokens absent from HTML
  - `_save` writes `auth.json` with mode `0o600`
  - `load` raises `AuthError` with actionable message when file absent
  - `login_cookies_json` raises `AuthError` when required cookies (`SID`, `HSID`, `SSID`) missing
  - `refresh_tokens` calls `_fetch_tokens` and updates stored tokens
  - `refresh_tokens` handles HTTP redirect (anti-bot) by raising `AntiBot` exception
  - Cookie deduplication: `.google.com` wins over `accounts.google.com`

**Module: `core/client.py`** (~11 tests)
- Functions: `call`, retry-on-401 behavior
- Cases (all using `unittest.mock.patch` on `httpx.post`):
  - Successful call: correct headers sent including `x-same-domain: 1`
  - Successful call: URL contains correct `f.sid` and `bl`
  - Successful call: response decoded and returned as parsed dict
  - 401 response: triggers `auth.refresh_tokens()` then retries once
  - 401 on retry: raises `AuthError` (no infinite loop)
  - 500 response: raises `RPCError` with status code
  - Network error: raises `NetworkError`
  - `reqid` increments between calls

### E2E Test Plan (test_e2e.py)

**Fixture replay tests** (~15 tests):

Using saved response bodies from `tests/fixtures/`:

| Fixture | Test | Verifies |
|---|---|---|
| `list_notebooks.json` | parse notebook list | count ≥ 1, each item has `id` and `title` |
| `get_notebook.json` | parse notebook detail | has `sources` list and `notes` list |
| `create_notebook.json` | parse create response | returned `id` is non-empty string |
| `add_source_url.json` | parse source add | returned source has `type == "url"` |
| `chat_ask.json` | parse chat response | has `text` field with non-empty string |
| `create_note.json` | parse note create | returned `id` and `content` present |
| `generate_audio.json` | parse audio generate | has `status` field |

**Live tests** — require auth (~20 tests):

Before any live test, the test file includes a module-level auth check:
```python
@pytest.fixture(scope="module", autouse=True)
def require_auth():
    auth = NotebookLMAuth()
    if not auth.AUTH_FILE.exists():
        pytest.fail("Auth not configured. Run: cli-web-notebooklm auth login --from-browser")
    data = auth.load()
    if "csrf_token" not in data:
        pytest.fail("Auth incomplete. Run: cli-web-notebooklm auth refresh")
```

Live test scenarios:
1. Notebooks list — verify returns list with required fields
2. Notebooks CRUD round-trip (see Workflow Scenario 1 below)
3. Sources add-url + verify in notebook detail
4. Sources add-text + verify in notebook detail
5. Chat ask — verify non-empty answer with citations
6. Notes CRUD round-trip (see Workflow Scenario 2 below)
7. Audio generate + status poll

**CLI subprocess tests** (~10 tests):

```python
class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-web-notebooklm")
    # ... tests below
```

Tests:
1. `--help` returns exit code 0 and shows command groups
2. `auth status` returns exit code 0 when auth configured
3. `--json notebooks list` returns valid JSON array
4. `--json notebooks create --title test-<timestamp>` returns JSON with `id` field
5. `--json notebooks delete --id <id-from-above>` succeeds

### Realistic Workflow Scenarios

**Scenario 1 — Notebook CRUD round-trip**
- Simulates: researcher creating a new research notebook, verifying it exists, renaming it, then cleaning up
- Operations:
  1. `notebooks create --title "test-research-$(date +%s)"` → capture `notebook_id`
  2. `notebooks list` → verify new notebook appears with correct title
  3. `notebooks get --id <notebook_id>` → verify `id` matches, `sources` is empty list
  4. `notebooks rename --id <notebook_id> --title "test-research-renamed"` → verify 200
  5. `notebooks get --id <notebook_id>` → verify `title` now equals "test-research-renamed"
  6. `notebooks delete --id <notebook_id>` → verify 200
  7. `notebooks list` → verify notebook no longer appears
- Verified: round-trip consistency, rename persists, delete removes item

**Scenario 2 — Source and chat workflow**
- Simulates: researcher adding a URL source and then asking a question about it
- Operations:
  1. `notebooks create --title "source-test-$(date +%s)"` → capture `notebook_id`
  2. `sources add-url --notebook-id <notebook_id> --url https://en.wikipedia.org/wiki/Python_(programming_language)` → capture `source_id`
  3. `notebooks get --id <notebook_id>` → verify `sources` list contains item with `source_id`
  4. Wait up to 30 seconds for source to be indexed (poll `notebooks get` until `sources[0].status == "ready"`)
  5. `chat ask --notebook-id <notebook_id> --question "What is Python?"` → verify answer contains "Python" and has at least one citation
  6. Verify citation references `source_id`
  7. `sources delete --notebook-id <notebook_id> --source-id <source_id>` → verify 200
  8. `notebooks delete --id <notebook_id>` → cleanup
- Verified: source indexing, citation accuracy, deletion

**Scenario 3 — Notes CRUD round-trip**
- Simulates: researcher taking and managing notes within a notebook
- Operations:
  1. Use existing notebook (or create one) → `notebook_id`
  2. `notes create --notebook-id <notebook_id> --content "Initial note content"` → capture `note_id`
  3. `notes list --notebook-id <notebook_id>` → verify note appears
  4. `notes update --notebook-id <notebook_id> --note-id <note_id> --content "Updated content"` → verify 200
  5. `notes list --notebook-id <notebook_id>` → verify content updated
  6. `notes delete --notebook-id <notebook_id> --note-id <note_id>` → verify 200
  7. `notes list --notebook-id <notebook_id>` → verify note absent
- Verified: note content persists, update reflects new value, delete removes item

**Scenario 4 — Audio overview generation**
- Simulates: researcher generating an audio summary of their notebook
- Operations:
  1. Use a notebook with at least one indexed source
  2. `audio generate --notebook-id <notebook_id>` → capture `audio_id`, verify status is "generating" or "ready"
  3. If status is "generating": poll `audio status --notebook-id <notebook_id>` every 10 seconds, up to 5 minutes
  4. Once status is "ready": verify `audio_url` is a non-empty string
  5. `audio download --notebook-id <notebook_id> --out /tmp/test-audio.mp3` → verify file created, size > 0
- Verified: async generation workflow, polling, download

**Scenario 5 — Auth token refresh**
- Simulates: session expiry and automatic recovery
- Operations:
  1. Load auth data, manually corrupt the `csrf_token` in memory (not on disk)
  2. Call `client.call("wXbhsf", [...])` — expect 401
  3. Verify client auto-refreshes tokens (calls `auth.refresh_tokens()`)
  4. Verify retry succeeds and returns valid notebook list
  5. Verify `auth.json` now contains updated `csrf_token`
- Verified: auto-refresh on 401, retry succeeds, storage updated

**Scenario 6 — Bulk operations**
- Simulates: agent creating multiple notebooks in bulk then cleaning up
- Operations:
  1. Create 3 notebooks with distinct titles (timestamp-suffixed)
  2. `notebooks list` → verify count increases by 3, all 3 titles present
  3. Delete all 3 by ID
  4. `notebooks list` → verify all 3 are absent
- Verified: bulk create, list reflects changes, bulk delete

---

## Phase 6 — Test (Write Tests)

### Pre-condition: Auth Must Be Working

Before writing or running any E2E test:

```bash
# Ensure Chrome debug profile is running on port 9222, user is logged in
cli-web-notebooklm auth login --from-browser
cli-web-notebooklm auth status
# Must show: "Live validation: OK" with notebook count
```

If `auth status` shows anything other than "OK", STOP and fix auth first. Do not proceed
to writing or running E2E tests until `auth status` shows live API validation succeeds.

### Parallel Test Writing (Subagent Dispatch)

Test files are independent of each other and can be written in parallel:

| Subagent | Scope | Inputs needed |
|---|---|---|
| Agent 1 | Unit tests for `rpc/encoder.py` and `rpc/decoder.py` in `test_core.py` | encoder/decoder source, `fixtures/list_notebooks.json` |
| Agent 2 | Unit tests for `core/auth.py` and `core/client.py` in `test_core.py` | auth/client source, sample HTML fixture with WIZ_global_data |
| Agent 3 | E2E fixture replay tests in `test_e2e.py` | all `fixtures/*.json`, models.py |
| Agent 4 | E2E live tests (Scenarios 1–4) in `test_e2e.py` | full client interface, TEST.md scenarios |
| Agent 5 | E2E live tests (Scenarios 5–6) + subprocess tests in `test_e2e.py` | auth module, `_resolve_cli` pattern |

Agents 1 and 2 can start in parallel immediately after Phase 4 Step 1 (core modules written).
Agents 3–5 can start once Phase 4 Step 2 is complete (all command modules written).

After all agents return, integrate their outputs into the final `test_core.py` and `test_e2e.py`
files, ensuring no duplicate test names and consistent imports.

### `_resolve_cli` Implementation

Every subprocess test uses:

```python
def _resolve_cli(name: str) -> list[str]:
    force = os.environ.get("CLI_WEB_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-web-", "cli_web.") + "." + name.split("-")[-1] + "_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]
```

For `cli-web-notebooklm`, the fallback module path is `cli_web.notebooklm.notebooklm_cli`.

### Fixture Capture

During Phase 1 traffic capture, save each response body to `tests/fixtures/` as a raw file
(including the `)]}'\n` prefix). The fixture replay tests load these files and feed them
into `extract_result()` — this verifies the decoder handles real Google responses correctly,
without any live network calls.

Example fixture structure for `fixtures/list_notebooks.json`:
```
)]}'\n
96132\n
[["wrb.fr","wXbhsf","[[[\"notebook_id_1\",\"My Research\",...]]]\n",null,...]]
42\n
[["di",95]]
```

### Running Tests

```bash
# Unit tests only (no auth needed)
python3 -m pytest cli_web/notebooklm/tests/test_core.py -v

# E2E fixture + live tests (auth required)
python3 -m pytest cli_web/notebooklm/tests/test_e2e.py -v --tb=short

# Full suite
python3 -m pytest cli_web/notebooklm/tests/ -v --tb=short

# Subprocess tests (requires pip install -e . first)
CLI_WEB_FORCE_INSTALLED=1 python3 -m pytest cli_web/notebooklm/tests/ -v -s -k subprocess
```

### Test Failure Protocol

If tests fail:
1. Show full pytest output with tracebacks
2. Do NOT update TEST.md Part 2 — it should only record passing results
3. Analyze: auth error (fix auth first), API schema change (update decoder/models),
   encoding error (fix encoder), or logic bug
4. Fix the issue, re-run, confirm all tests pass before proceeding to Phase 7

---

## Phase 7 — Document (Update TEST.md)

### Pre-condition Verification

```bash
cli-web-notebooklm auth login --from-browser   # re-extract fresh cookies + tokens
cli-web-notebooklm auth status                  # must show "Live validation: OK"
```

If auth status fails, do not run tests. Fix auth first.

### Run Full Suite

```bash
python3 -m pytest cli_web/notebooklm/tests/ -v --tb=no 2>&1 | tee test_output.txt
```

All tests must pass. If any E2E test fails with auth errors, return to the auth fix step.
The output "auth not configured" is not a valid test result — it means auth is broken.

```bash
CLI_WEB_FORCE_INSTALLED=1 python3 -m pytest cli_web/notebooklm/tests/ -v -s -k subprocess 2>&1 | tee subprocess_output.txt
```

### Append Part 2 to TEST.md

TEST.md Part 2 is APPENDED (not overwritten) to the existing Part 1 document:

```markdown
---

## Part 2 — Test Results

### Execution Date: 2026-03-15

### Full Test Output

```
(paste pytest -v --tb=no output here)
```

### Summary

| Metric | Value |
|---|---|
| Total tests | 90 |
| Passed | 90 |
| Failed | 0 |
| Skipped | 0 |
| Pass rate | 100% |
| Execution time | ~45s |

### Gaps and Notes

- Audio download test uses a pre-existing notebook with a ready audio overview; generation time
  varies (1–5 minutes) so the async polling loop has a 5-minute timeout
- PDF upload test requires a real PDF file at `tests/fixtures/sample.pdf` (included in repo)
- Streaming chat test verifies the accumulated text output; individual chunk ordering is not tested
```

### README.md

The `README.md` inside `cli_web/notebooklm/` must include:
1. Installation: `pip install -e .` and `pip install -e ".[browser]"` for Playwright
2. Auth setup: the three login methods with step-by-step instructions
3. Quick start: 5-line example from "list notebooks" to "ask a question"
4. Full command reference: all commands with flags and example output
5. Troubleshooting: common anti-bot redirect issues, token expiry, CDP connection failures

---

## Phase 8 — Publish and Verify (End-User Smoke Test)

### Installation

```bash
cd notebooklm/agent-harness
pip install -e .
which cli-web-notebooklm   # must return a path
cli-web-notebooklm --help  # must show all command groups
```

### End-User Smoke Test (MANDATORY)

This simulates what a new user does after `pip install cli-web-notebooklm`. Every step must
succeed. If any step fails, the pipeline is NOT complete.

**Step 1: Authenticate (Playwright — primary end-user method)**

```bash
pip install "cli-web-notebooklm[browser]"
playwright install chromium
cli-web-notebooklm auth login
# Browser opens. User navigates to notebooklm.google.com and logs in with Google account.
# User presses ENTER in the terminal.
# Playwright saves storage_state.json with all cookies.
# CLI automatically extracts CSRF + session tokens via HTTP GET.
```

Expected output:
```
Opening browser for login...
[waiting for user to log in and press ENTER]
Cookies saved: 14 cookies
Session tokens extracted: csrf_token=AIXQIk..., session_id=3943...
Auth saved to /home/user/.config/cli-web-notebooklm/auth.json (mode 600)
```

**Step 2: Verify auth status**

```bash
cli-web-notebooklm auth status
```

Expected output:
```
Cookies:         14 cookies present (SID, HSID, SSID, __Secure-1PSID, ...)
CSRF token:      present (AIXQIk...)
Session ID:      present (394392219...)
Live validation: OK (200, got 5 notebooks)
```

If it shows "redirected", "expired", or "0 notebooks" — STOP. Fix auth before continuing.

**Step 3: List notebooks (verify real API data)**

```bash
cli-web-notebooklm --json notebooks list
```

Expected: valid JSON array with at least one notebook object containing `id`, `title`, and `created_at`.
If array is empty, that is acceptable (user may have no notebooks yet) — but it must not be
an error response, and the JSON must be a valid array.

**Step 4: CRUD smoke test**

```bash
# Create
cli-web-notebooklm --json notebooks create --title "smoke-test-$(date +%s)"
# Copy the returned id

# Verify it appears in list
cli-web-notebooklm --json notebooks list
# Confirm smoke-test notebook is present

# Add a source
cli-web-notebooklm --json sources add-url \
  --notebook-id <id> \
  --url "https://en.wikipedia.org/wiki/Python_(programming_language)"

# Ask a question
cli-web-notebooklm --json chat ask \
  --notebook-id <id> \
  --question "What is Python used for?"
# Verify: non-empty "text" field in response

# Create a note
cli-web-notebooklm --json notes create \
  --notebook-id <id> \
  --content "Smoke test note"

# Clean up
cli-web-notebooklm --json notebooks delete --id <id>
```

**Step 5: REPL smoke test**

```bash
cli-web-notebooklm
# Verify branded banner appears
# Type: notebooks list
# Verify output matches --json mode output
# Type: exit
```

**Declaring Done**

The pipeline is complete ONLY when ALL of the following are true:
- `pip install -e .` succeeds without errors
- `which cli-web-notebooklm` returns a path
- `auth login` works (Playwright or CDP)
- `auth status` shows "Live validation: OK"
- `notebooks list` returns real data from the live API
- CRUD smoke test (create → verify → delete) completes without error
- `pytest` passes all 90 tests

---

## Cross-Cutting Concerns

### How Auth Works (3 Login Methods)

**Method 1: Playwright (recommended for end users)**

The end user should never need to understand batchexecute internals. `auth login` opens a
real browser (Chromium), the user navigates normally, Google sees a real browser with
real user interaction — no CAPTCHA, no challenge. Playwright captures the full cookie state
after login. The CLI then immediately performs an HTTP GET to the homepage using those cookies
to extract the CSRF token and session ID.

This requires the `[browser]` optional dependency. If Playwright is not installed, the CLI
prints: "Playwright not installed. Run: pip install cli-web-notebooklm[browser]"

**Method 2: CDP extraction (`--from-browser`)**

For developers running the pipeline who already have Chrome debug profile running. Connects
via WebSockets to `ws://localhost:9222/json`, enumerates tabs, targets the notebooklm.google.com
tab (or any Google tab), issues `Storage.getCookies` CDP command for the `.google.com` domain.

Cookie deduplication is critical here: the Chrome profile stores cookies for multiple subdomains.
For any cookie name that appears under both `.google.com` and `accounts.google.com`, use the
`.google.com` version — it has broader scope and avoids CookieMismatch rejections from the server.

After extracting cookies, immediately performs the HTTP GET to the homepage to extract
`SNlM0e` (CSRF) and `FdrFJe` (session ID). If this GET redirects (Google's anti-bot detecting
a non-browser client), falls back to CDP JavaScript evaluation:
```python
result = cdp.evaluate("JSON.stringify(window.WIZ_global_data)")
data = json.loads(result)
csrf = data["SNlM0e"]
session_id = data["FdrFJe"]
```

**Method 3: Manual JSON import**

For automated environments where neither Playwright nor debug Chrome is available. The user
exports cookies from a browser extension (e.g., Cookie-Editor), saves to a JSON file, and
passes `--cookies-json path/to/cookies.json`. The CLI validates that the file contains at
minimum `SID`, `HSID`, and `SSID` before proceeding to token extraction.

### Google Anti-Bot Protections

NotebookLM is protected at multiple layers:

**Layer 1: Login blocking**
Google detects automated HTTP login attempts (even with correct credentials) and shows CAPTCHA
or silently redirects to a login loop. Solution: never attempt programmatic login. Use browser
cookies instead (any of the 3 login methods above).

**Layer 2: Session token embedding**
CSRF token (`SNlM0e`) and session ID (`FdrFJe`) are embedded in page JavaScript, not in HTTP
headers. They cannot be guessed or hardcoded. Solution: HTTP GET to homepage after cookie
extraction, parse from HTML with regex. CDP fallback if HTTP GET is blocked.

**Layer 3: Build label changes**
The `bl` build label parameter changes with each deployment (typically multiple times per day).
Hardcoding it breaks all requests after the next deployment. Solution: extract it dynamically
from the homepage HTML alongside `SNlM0e` and `FdrFJe`.

**Layer 4: `x-same-domain: 1` header check**
Google's batchexecute endpoint verifies the presence of `x-same-domain: 1` header as a
basic same-origin check. Without it, requests are rejected with 400 or 403. Solution:
always include this header in all batchexecute POST requests.

**Layer 5: `Origin` and `Referer` headers**
The server may also check that `Origin: https://notebooklm.google.com` and `Referer:
https://notebooklm.google.com/` are present. Solution: always include both headers.

**Layer 6: `_reqid` pattern**
The `_reqid` counter in the URL starts at a large random number in browsers (e.g., 100000)
and increments by a browser-specific amount per request. Incrementing by 1 is suspicious.
Solution: observe the increment pattern from captured traffic and replicate it.

**Layer 7: Token expiry**
`SNlM0e` and `FdrFJe` tokens expire. On 401 or 403 response, auto-refresh by re-fetching
the homepage and re-extracting tokens. This is handled transparently by the client's
retry logic.

### RPC Encoder/Decoder Architecture

The `core/rpc/` subpackage encapsulates the batchexecute protocol:

**`encoder.py` — building requests:**
The request format has three nesting levels:
1. Method call level: `[rpc_id, json.dumps(params), null, "generic"]`
   - Note: `params` is JSON-serialized to a string here, not embedded as a JSON object
2. Call list level: `[[<method_call>]]` — wraps the method call in a list of calls
3. Body level: URL-encode the JSON string as `f.req=<encoded>` combined with `at=<csrf>`

The encoder provides `encode_rpc_request(rpc_id, params)` and `build_request_body(rpc_id,
params, csrf)` as the public API. `client.py` calls these without knowing the protocol details.

**`decoder.py` — parsing responses:**
Three-step pipeline:
1. Strip the anti-XSSI prefix: `)]}'\n` (4 chars + newline)
2. Parse length-prefixed chunks: each chunk is preceded by its byte length on its own line
3. Find the `wrb.fr` entry matching the method's `rpcids`, apply a second `json.loads()`
   to `entry[2]` since it is a JSON string not a JSON object

Special handling:
- Streaming chat: the `GenerateFreeFormStreamed` method produces multiple chunks. Each chunk
  may contain a partial text update. Accumulate `entry[2]` values across all matching chunks.
- Error detection: if any chunk contains `entry[0] == "er"`, extract the error message and
  raise `RPCError`.
- Size limit: the byte count header tells us exactly how many bytes to read per chunk,
  preventing truncation on long responses.

**`types.py` — constants:**
Defines all `RPCMethod` values as class attributes (not an Enum, to avoid issues with
non-identifier characters). Also defines `BASE_URL`, `BATCHEXECUTE_PATH`, and
`REQUIRED_HEADERS` as constants. Method IDs are the only things that may need updating
when Google redeploys — having them in one file makes maintenance straightforward.

### Critical Headers

| Header | Value | Why it's required |
|---|---|---|
| `x-same-domain` | `1` | Google's same-origin check — requests without this are rejected |
| `Content-Type` | `application/x-www-form-urlencoded;charset=UTF-8` | batchexecute requires this exact value |
| `Origin` | `https://notebooklm.google.com` | Matches the app's origin for CORS-like validation |
| `Referer` | `https://notebooklm.google.com/` | Server may check for referrer consistency |
| `Cookie` | Full Google auth cookie string | Carries the authenticated session |

The `Cookie` header must include all Google auth cookies. The minimum required set (based on
known patterns) is `SID`, `HSID`, `SSID`. Other cookies (`APISID`, `SAPISID`,
`__Secure-1PSID`, etc.) should also be included as captured.

---

## Quality Checklist (50-Check Validation Preview)

Before declaring the implementation complete, validate against all 50 checks:

**Directory Structure (6):** `agent-harness/cli_web/notebooklm/` exists, `NOTEBOOKLM.md`
at harness root, `cli_web/` has no `__init__.py`, `notebooklm/` has `__init__.py`,
all subdirectories present, `setup.py` at root.

**Required Files (13):** `README.md`, `notebooklm_cli.py`, `__main__.py`, all 4 core modules,
`core/rpc/` with 3 files (since protocol is non-REST), all 3 utils files, `TEST.md`,
`test_core.py`, `test_e2e.py`.

**CLI Implementation (6):** Click framework with groups, `--json` on every command, REPL via
`invoke_without_command=True`, `ReplSkin` used, auth group with login/status/refresh, global
session state.

**Core Modules (5):** `client.py` has centralized auth injection + backoff + JSON parsing,
`auth.py` has all 3 login methods + refresh + `chmod 600`, `session.py` has undo/redo stack,
`models.py` has typed dataclasses, `core/rpc/` exists with `types.py`/`encoder.py`/`decoder.py`.

**Test Standards (8):** TEST.md has both parts, unit tests use mock.patch with no real network,
E2E fixture tests replay from `fixtures/`, E2E live tests FAIL without auth, `TestCLISubprocess`
class exists, uses `_resolve_cli`, subprocess `_run` does not set `cwd`, supports `CLI_WEB_FORCE_INSTALLED=1`.

**Documentation (3):** README has auth setup + install + examples, `NOTEBOOKLM.md` has full
API map, no `HARNESS.md` inside app package.

**PyPI Packaging (5):** `find_namespace_packages`, package name `cli-web-notebooklm`, correct
entry point, all imports use `cli_web.notebooklm.*`, `python_requires=">=3.10"`.

**Code Quality (5):** No syntax errors, no hardcoded tokens, no hardcoded `f.sid`/`bl`/CSRF,
no bare `except:`, all errors have actionable messages.
