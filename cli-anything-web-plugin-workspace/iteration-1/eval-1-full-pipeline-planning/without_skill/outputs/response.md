# Plan: Python CLI for Google NotebookLM

## Executive Summary

Google NotebookLM does not expose a public REST API. All interactions happen through a browser-based SPA at https://notebooklm.google.com/. This means a Python CLI cannot call documented endpoints — it must either (a) automate the browser via Playwright/Selenium, (b) reverse-engineer the internal gRPC/JSON-over-HTTP calls the SPA makes and replay them with authenticated session cookies, or (c) wait for Google to publish an official API (announced in limited preview as of early 2025 for enterprise).

This plan covers approach (b) as the primary strategy — reverse-engineering the internal API — with Playwright-based browser automation as a fallback for operations that are too complex to replay reliably.

---

## 1. Feasibility Analysis

### 1.1 What NotebookLM Uses Internally

The web app communicates with Google's backend using:
- **gRPC-Web** or **JSON-RPC** calls routed through `https://notebooklm.google.com/` (proxied internally)
- Standard Google OAuth2 / session cookies (`__Secure-1PSID`, `__Secure-3PSID`, etc.) for authentication
- Some calls go to `https://alkalimakersuite-pa.clients6.google.com/` (the internal Maker Suite / AI Studio backend that powers NotebookLM)

### 1.2 Authentication Reality

There is no OAuth2 client_id for NotebookLM. The only viable auth path is:
1. User logs in via browser (manually or Playwright-automated)
2. CLI extracts session cookies from the browser's cookie store or from a Playwright session
3. CLI reuses those cookies for subsequent HTTP calls

This means the CLI will be **session-cookie authenticated**, not token-authenticated. Session lifetimes are typically 2 weeks. The CLI must handle re-authentication gracefully.

### 1.3 Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Google changes internal API | High (no SLA) | Version-pin the reverse-engineered calls; wrap in adapter layer so updates are isolated |
| Rate limiting / bot detection | Medium | Respect delays; fall back to Playwright if raw HTTP is blocked |
| TOS concerns | Real | Users accept Google's TOS; document this clearly; the CLI is a personal productivity tool |
| Official API released | Possible | Design adapter layer so swapping to official API is a one-file change |

---

## 2. Architecture Overview

```
cli-notebooklm/
├── notebooklm_cli/
│   ├── __init__.py
│   ├── cli.py                  # Click/Typer entry point
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── session.py          # Cookie extraction, persistence, refresh
│   │   └── browser_login.py    # Playwright-based login flow
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py           # Low-level HTTP client (httpx + cookie jar)
│   │   ├── notebooks.py        # Notebook CRUD operations
│   │   ├── sources.py          # Source management (PDF, URL, text)
│   │   ├── chat.py             # Q&A / grounding queries
│   │   └── audio.py            # Audio overview management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── notebook.py         # Pydantic models for notebooks
│   │   ├── source.py           # Pydantic models for sources
│   │   └── audio.py            # Pydantic models for audio overviews
│   └── utils/
│       ├── __init__.py
│       ├── output.py           # Rich-based pretty printing
│       └── config.py           # Config file (~/.notebooklm/config.toml)
├── tests/
│   ├── unit/
│   └── integration/            # Requires live session; skip in CI
├── pyproject.toml
└── README.md
```

---

## 3. Authentication Design

### 3.1 Session Cookie Flow

```
Step 1: notebooklm login
  - Launch Playwright (headless=False for first login)
  - Navigate to https://notebooklm.google.com/
  - Wait for user to complete Google OAuth in browser
  - Extract cookies from Playwright context
  - Persist cookies to ~/.notebooklm/session.json (file-mode 600)

Step 2: Subsequent commands
  - Load cookies from ~/.notebooklm/session.json
  - Inject into httpx.Client cookie jar
  - Make API calls
  - If 401/403 returned, prompt user to re-run `notebooklm login`
```

### 3.2 Cookie Storage Format

```json
{
  "cookies": [
    {
      "name": "__Secure-1PSID",
      "value": "...",
      "domain": ".google.com",
      "path": "/",
      "expires": 1234567890,
      "httpOnly": true,
      "secure": true
    }
  ],
  "saved_at": "2026-03-15T10:00:00Z",
  "expires_at": "2026-03-29T10:00:00Z"
}
```

### 3.3 Alternative: Chrome Cookie Extraction

For users who are already logged into NotebookLM in Chrome, the CLI can read cookies directly from Chrome's SQLite cookie database using `browser-cookie3` or `rookiepy`. This avoids requiring a separate Playwright login. The cookie database lives at:
- Windows: `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Network\Cookies`
- macOS: `~/Library/Application Support/Google/Chrome/Default/Cookies`
- Linux: `~/.config/google-chrome/Default/Cookies`

---

## 4. Internal API Reverse Engineering

### 4.1 Methodology

1. Open Chrome DevTools → Network tab → filter by `notebooklm.google.com`
2. Perform each operation in the UI and record the exact request:
   - URL, method, headers, request body, response body
3. Identify the pattern (REST vs gRPC-Web vs JSON-RPC)
4. Reproduce with `httpx` in a Jupyter notebook
5. Parameterize and wrap in the `api/` module

### 4.2 Expected Endpoint Patterns

Based on other Google SPA reverse engineering (Bard, AI Studio), NotebookLM likely uses one of:
- `POST /api/v1/notebooks` style REST (less common for Google SPAs)
- `POST /$rpc/google.internal.notebooklm.SomeService/SomeMethod` gRPC-Web (common)
- `POST /v1/projects:batchExecute` JSON-RPC style (common in Google APIs)

The reverse-engineering step is a prerequisite before any implementation begins. Estimated time: 4-8 hours of browser observation.

### 4.3 Required Headers

Every authenticated request will need:
```
Cookie: <session cookies>
X-Goog-AuthUser: 0
Content-Type: application/json (or application/grpc-web+proto)
Origin: https://notebooklm.google.com
Referer: https://notebooklm.google.com/
```

---

## 5. Feature Implementation Plan

### 5.1 Notebook Management

**Commands:**
```
notebooklm notebook list
notebooklm notebook create --title "My Research"
notebooklm notebook show <notebook-id>
notebooklm notebook rename <notebook-id> --title "New Title"
notebooklm notebook delete <notebook-id> [--confirm]
```

**Internal operations to reverse-engineer:**
- `GET /` or equivalent that returns the notebook list (likely a POST with empty body to a list endpoint)
- Create notebook (POST with title)
- Get notebook metadata + sources (GET or POST with notebook ID)
- Rename (PATCH or POST)
- Delete (DELETE or POST)

**Notebook model:**
```python
class Notebook(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    source_count: int
    sources: list[Source] = []
```

### 5.2 Source Management

**Commands:**
```
notebooklm source add <notebook-id> --url https://example.com/paper.pdf
notebooklm source add <notebook-id> --file ./paper.pdf
notebooklm source add <notebook-id> --text "Paste text here" --title "My Notes"
notebooklm source add <notebook-id> --gdrive <gdrive-url>
notebooklm source list <notebook-id>
notebooklm source show <notebook-id> <source-id>
notebooklm source delete <notebook-id> <source-id>
```

**Source types and their upload mechanics:**

| Type | Mechanism | Notes |
|------|-----------|-------|
| PDF file | Multipart upload to Google storage, then attach | May use resumable upload protocol |
| Web URL | POST with URL; Google fetches and processes | Simplest case |
| Plain text | POST with text content + title | |
| Google Drive | POST with Drive file ID/URL | Requires Drive access in same Google account |
| YouTube URL | POST with YouTube URL | NotebookLM supports this; Google transcribes |

**Source model:**
```python
class Source(BaseModel):
    id: str
    notebook_id: str
    title: str
    type: Literal["pdf", "url", "text", "gdrive", "youtube"]
    status: Literal["processing", "ready", "failed"]
    created_at: datetime
    url: str | None = None
    file_name: str | None = None
    word_count: int | None = None
```

**File upload flow for PDFs:**
1. Initiate resumable upload session (POST to Google upload endpoint)
2. Upload file in chunks (PUT requests with Content-Range)
3. Get upload token/file ID from Google
4. Call NotebookLM's "attach source" endpoint with that file ID

This is the most complex operation. Playwright fallback is strongly recommended for file upload if the raw HTTP approach proves brittle.

### 5.3 Q&A / Chat

**Commands:**
```
notebooklm ask <notebook-id> "What are the key findings?"
notebooklm ask <notebook-id> "Summarize source 3" --source <source-id>
notebooklm chat <notebook-id>   # interactive REPL mode
```

**Internal mechanics:**
- The chat endpoint accepts a notebook ID + user message + optional source filter
- Returns a streamed response (Server-Sent Events or chunked JSON)
- Citations are returned as structured references to source IDs + page/paragraph positions

**Streaming output:**
- Use `httpx` with `stream=True`
- Parse SSE chunks and print incrementally using `rich.live`
- Collect full response + citations for optional `--json` output

**Citation display:**
```
Answer: The study found a 23% improvement in accuracy...
  [1] Source: "Smith et al. 2024.pdf" — Page 7, Section 3.2
  [2] Source: "arxiv_2401.12345" — Abstract
```

**Chat REPL mode:**
- Use `prompt_toolkit` for readline-style input with history
- Maintain conversation context (send prior turns to API if it supports multi-turn)
- Commands: `/sources`, `/clear`, `/export <filename>`, `/quit`

### 5.4 Audio Overview Management

**Commands:**
```
notebooklm audio generate <notebook-id>
notebooklm audio status <notebook-id>
notebooklm audio download <notebook-id> --output ./overview.mp3
notebooklm audio delete <notebook-id>
```

**Internal mechanics:**
- Audio overview generation is an async operation (can take 2-5 minutes)
- POST to trigger generation → returns a job ID or status field
- Poll for status: `processing` → `ready`
- Download: GET request that returns an audio file (MP3 or similar)

**Generate + wait pattern:**
```
notebooklm audio generate <notebook-id> --wait
# Shows a progress spinner while polling every 10 seconds
# Prints "Ready! Run: notebooklm audio download <id>" when done
```

**Audio model:**
```python
class AudioOverview(BaseModel):
    notebook_id: str
    status: Literal["not_generated", "generating", "ready", "failed"]
    generated_at: datetime | None = None
    duration_seconds: int | None = None
    download_url: str | None = None
```

---

## 6. CLI Framework and UX

### 6.1 CLI Framework: Typer

Typer (built on Click) is the recommended choice because:
- Type-hint driven — less boilerplate than raw Click
- Automatic `--help` generation
- Shell completion support (bash, zsh, fish, PowerShell)
- Works well with Pydantic models

### 6.2 Output Formatting

Use `rich` for all terminal output:
- Tables for `list` commands
- Panels for `show` commands
- Progress bars for file uploads
- Spinners for async operations (audio generation)
- Syntax-highlighted JSON for `--json` output flag

Every command supports `--json` for scripting use:
```
notebooklm notebook list --json | jq '.[].id'
```

### 6.3 Global Options

```
notebooklm --profile work notebook list   # use alternate credentials
notebooklm --no-color notebook list       # disable rich formatting
notebooklm --debug notebook list          # show raw HTTP requests/responses
```

### 6.4 Configuration File

Location: `~/.notebooklm/config.toml`

```toml
[default]
session_file = "~/.notebooklm/session.json"
output_format = "table"  # or "json"
download_dir = "~/Downloads"

[profiles.work]
session_file = "~/.notebooklm/session-work.json"
```

---

## 7. Error Handling Strategy

| Scenario | Handling |
|----------|----------|
| Session expired (401/403) | Print clear message: "Session expired. Run: notebooklm login" |
| Rate limited (429) | Exponential backoff with jitter; warn user |
| Source still processing | Polling with timeout; `--wait` flag |
| Network error | Retry with backoff (3 attempts); print error |
| API shape changed | Catch Pydantic validation errors; print raw response in `--debug` mode |
| File too large | Check file size before upload; warn if >200MB (NotebookLM limit) |
| Unsupported file type | Validate extension before attempting upload |

---

## 8. Testing Strategy

### 8.1 Unit Tests (no live session needed)

- Test Pydantic models with fixture JSON responses
- Test CLI argument parsing with Typer's `CliRunner`
- Test cookie loading/saving with temp files
- Mock `httpx.Client` to test API client logic
- Test output formatting with Rich's `Console(record=True)`

### 8.2 Integration Tests (require live session)

- Mark with `@pytest.mark.integration`
- Skipped in CI by default (`pytest -m "not integration"`)
- Run manually with `pytest -m integration --session-file ~/.notebooklm/session.json`
- Test full CRUD cycle: create notebook → add source → ask question → delete notebook

### 8.3 VCR / Cassette Testing

Use `pytest-recording` (wraps VCR.py) to record real HTTP interactions once, then replay them in CI without a live session. Sensitive cookie values are scrubbed from cassette files before committing.

---

## 9. Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Set up project structure with `pyproject.toml` (Poetry or Hatch)
- [ ] Implement auth module: cookie extraction from Chrome + Playwright login fallback
- [ ] Implement low-level `client.py` with cookie injection and debug logging
- [ ] Reverse-engineer notebook list and create endpoints
- [ ] Implement `notebooklm notebook list` and `notebooklm notebook create`

### Phase 2: Sources (Week 2)
- [ ] Reverse-engineer source list, URL add, and text add endpoints
- [ ] Implement `notebooklm source list` and `notebooklm source add --url`
- [ ] Implement `notebooklm source add --text`
- [ ] Reverse-engineer and implement PDF file upload (most complex)
- [ ] Add `notebooklm source delete`

### Phase 3: Q&A (Week 3)
- [ ] Reverse-engineer chat/ask endpoint including streaming
- [ ] Implement `notebooklm ask` with streaming output and citation display
- [ ] Implement interactive `notebooklm chat` REPL
- [ ] Handle multi-turn conversation context if supported by API

### Phase 4: Audio (Week 4)
- [ ] Reverse-engineer audio generate, status, and download endpoints
- [ ] Implement `notebooklm audio generate` with `--wait` polling
- [ ] Implement `notebooklm audio download`
- [ ] Implement `notebooklm audio status` and `notebooklm audio delete`

### Phase 5: Polish (Week 5)
- [ ] Shell completion (zsh, bash, fish, PowerShell)
- [ ] Profile support for multiple Google accounts
- [ ] VCR cassette recording for test suite
- [ ] Comprehensive `--help` text and a README
- [ ] Package for PyPI: `pip install notebooklm-cli`

---

## 10. Dependencies

```toml
[project]
dependencies = [
    "typer[all]>=0.12",          # CLI framework
    "httpx>=0.27",               # Async-capable HTTP client
    "pydantic>=2.0",             # Data validation / models
    "rich>=13.0",                # Terminal output formatting
    "playwright>=1.44",          # Browser automation for auth
    "browser-cookie3>=0.19",     # Chrome cookie extraction
    "prompt-toolkit>=3.0",       # Interactive chat REPL
    "tomli>=2.0; python_version < '3.11'",  # TOML config parsing
    "keyring>=25.0",             # Optional: OS keychain for session storage
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-recording",          # VCR cassette testing
    "pytest-asyncio",
    "respx",                     # httpx mock library
]
```

---

## 11. Key Design Decisions and Rationale

**Why httpx over requests?**
httpx supports both sync and async usage. The streaming chat response and potentially async audio polling benefit from async support. The CLI commands themselves are sync (Typer is sync-first), but the underlying client can be async with `asyncio.run()` at the boundary.

**Why not wrap Playwright entirely?**
Full Playwright automation is slower (browser startup overhead), harder to script with `--json`, and less reliable for output parsing. Raw HTTP calls are faster and more predictable. Playwright is reserved for operations that are too complex to reproduce (e.g., file picker interactions for PDF upload).

**Why not use the official API when it ships?**
The plan's adapter layer (`api/client.py` + individual `api/*.py` modules) is designed so the transport layer can be swapped. When Google publishes an official API, the `client.py` implementation changes but the CLI commands, models, and tests remain unchanged.

**Why cookies instead of OAuth2?**
NotebookLM has no published OAuth2 client_id or scope. Until Google exposes one, cookies are the only mechanism. The cookie approach is standard for personal automation tools (similar to how `youtube-dl`/`yt-dlp` handles authenticated downloads).

---

## 12. Open Questions to Resolve During Reverse Engineering

1. Does the internal API use gRPC-Web (binary protobuf) or JSON? If protobuf, decompiling the `.proto` definitions will be necessary using tools like `grpc-web-devtools` Chrome extension.
2. Is there a CSRF token (`X-Goog-Csrf-Token` header) required? If so, it must be fetched from the initial page load before each session of API calls.
3. Does the chat endpoint return Server-Sent Events (SSE) or chunked JSON? This determines the streaming parsing approach.
4. What is the exact file upload flow for PDFs? Does it go through Google Drive's resumable upload API or a NotebookLM-specific upload endpoint?
5. Are there per-notebook conversation history IDs, or is each `ask` call stateless?
6. What are the documented limits? (Max sources per notebook, max file size, max text length, rate limits)
