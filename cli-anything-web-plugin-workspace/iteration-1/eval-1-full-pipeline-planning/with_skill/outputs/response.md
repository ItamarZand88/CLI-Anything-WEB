# NotebookLM CLI — Full Pipeline Plan

**Target:** https://notebooklm.google.com/
**CLI name:** `cli-web-notebooklm`
**Python namespace:** `cli_web.notebooklm`
**App SOP file:** `NOTEBOOKLM.md`

---

## Overview

Google NotebookLM is a research assistant that lets users organize sources (PDFs, URLs, text snippets, Google Docs/Drive files) into notebooks, ask questions grounded in those sources, and generate audio overviews (podcast-style summaries). It has no public API. This plan walks through the full 8-phase CLI-Anything-Web pipeline to produce a production-ready Python CLI for it.

---

## Phase 1 — Record (Traffic Capture)

### Goal
Capture all meaningful HTTP traffic triggered by NotebookLM's web UI across every feature we want to expose.

### Setup
1. Call `navigate` (chrome-devtools MCP) with `https://notebooklm.google.com/`.
2. NotebookLM requires a Google account. Pause and ask the user to complete the Google OAuth login flow manually in the opened browser window.
3. Once logged in and the notebook list is visible, begin network monitoring via `read_network_requests`.

### Traffic capture sessions

Each session below maps to a distinct CLI feature area. Within each session, perform actions slowly and deliberately — capture the full request/response cycle before moving on.

#### Session A — Notebook CRUD
- Observe the initial load: what API call fetches the notebook list?
- Click "New Notebook" — capture the creation request (method, URL, body, response with assigned notebook ID).
- Rename the notebook — capture the update/patch request.
- Reload the list — confirm the notebook appears.
- Delete the notebook — capture the delete request and the confirmation of removal.

#### Session B — Source Management
Create a fresh test notebook, then:
- Upload a PDF — capture the multipart/form-data upload request, the polling/status endpoint if upload is async, and the final source record response.
- Add a URL source — capture the POST with the URL payload, observe whether it returns immediately or requires polling.
- Add a plain text snippet — capture the POST with raw text body.
- (If accessible in the UI) Add a Google Docs/Drive link — capture the request structure.
- List sources within the notebook — capture the GET that returns source metadata.
- Delete a source — capture the DELETE request.

#### Session C — Q&A / Chat
Within a notebook that has at least one source:
- Type a question and submit — capture the POST (likely a streaming SSE or chunked response; note the full URL and body schema).
- Note how the session/conversation ID is managed across turns.
- Ask a follow-up question — capture whether a thread/session ID is sent in the body.
- Note citations in the response (source IDs referenced).

#### Session D — Audio Overview
- Click "Generate Audio Overview" — capture the POST request.
- Observe whether generation is synchronous or async; if async, identify the polling endpoint.
- Capture the GET that retrieves audio overview status and/or a download URL.
- If a download URL is returned, capture its pattern.

#### Session E — Edge Cases
- Attempt to add a source with an invalid URL — capture the error response structure.
- Ask a question in a notebook with no sources — capture the error or empty-state response.
- Trigger a 401 (log out, try a request manually via devtools `fetch`) to observe the auth error shape.

### Filtering rules
- **Discard:** `.js`, `.css`, `.png`, fonts, Google Analytics, Firebase Crashlytics, any CDN asset requests.
- **Keep:** Every request to `notebooklm.googleapis.com`, `generativelanguage.googleapis.com`, or any path under `/_/NotebookLMUi/` or similar RPC-style endpoints.

### Auth token capture
Note all authentication artifacts present:
- Google session cookies (likely `SID`, `HSID`, `SSID`, `APISID`, `SAPISID`, `__Secure-*` variants)
- Any `Authorization: Bearer` headers or `X-Goog-AuthUser` headers
- CSRF tokens (`X-Goog-Xsrf-Token` or similar)
- The full `Cookie` header used on API requests

NotebookLM is a Google product and very likely uses Google's BFF (backend-for-frontend) RPC format — either `_/rpc/` style calls or Protobuf-over-HTTP (gRPC-Web). Record these verbatim.

### Output
`notebooklm/traffic-capture/raw-traffic.json` — full dump of all captured API requests and responses, including headers.

---

## Phase 2 — Analyze (API Discovery)

### Goal
Map `raw-traffic.json` into a structured model of endpoints, schemas, and auth.

### Expected API shape (hypotheses to confirm/refine during analysis)

NotebookLM is built on Google infrastructure and almost certainly uses one of two patterns:

**Hypothesis A — gRPC-Web / Protobuf RPC**
Requests go to a single or small set of URLs like:
```
POST /_/NotebookLMUi/data/batchexecute
POST /v1/corpora
POST /v1/corpora/{id}/documents
POST /v1/corpora/{id}/query
```
The body is either a JSON-wrapped protobuf blob or a `f.req=` encoded array (Google's standard BFE format). These need careful decoding.

**Hypothesis B — REST-ish JSON API**
More conventional endpoints:
```
GET  /api/notebooks
POST /api/notebooks
GET  /api/notebooks/{notebook_id}
PUT  /api/notebooks/{notebook_id}
DELETE /api/notebooks/{notebook_id}
GET  /api/notebooks/{notebook_id}/sources
POST /api/notebooks/{notebook_id}/sources
...
```

The analysis phase will determine the actual shape. For gRPC-Web or BFE RPC formats, the analysis must decode the wire format to extract logical operations.

### Entities to map

| Entity | Expected fields |
|--------|----------------|
| Notebook | `id`, `name`, `created_at`, `updated_at`, `source_count` |
| Source | `id`, `notebook_id`, `type` (pdf/url/text/gdoc), `title`, `url` (if applicable), `status`, `created_at` |
| Message / Chat Turn | `id`, `notebook_id`, `query`, `response_text`, `citations`, `created_at` |
| Audio Overview | `id`, `notebook_id`, `status` (pending/ready/failed), `audio_url`, `created_at` |

### Auth scheme analysis
Determine exactly:
1. Which cookies are required on every API request.
2. Whether a CSRF/Xsrf token must be sent as a header (and how it is obtained — from a cookie value, from page HTML, or from a dedicated endpoint).
3. Whether there is an OAuth access token (`Authorization: Bearer`) separate from session cookies.
4. Token lifetimes and refresh mechanism (Google sessions typically refresh via `accounts.google.com`).

### Output
`NOTEBOOKLM.md` — the software-specific SOP document containing:
- Confirmed API endpoint table (method, URL pattern, request body, response schema)
- Entity model
- Auth scheme with exact header/cookie names
- Known limitations (e.g., streaming responses, binary audio payloads)
- Rate limiting observations

---

## Phase 3 — Design (CLI Architecture)

### CLI command structure

```
cli-web-notebooklm                          # launches REPL
cli-web-notebooklm --help
cli-web-notebooklm --json <command>         # machine-readable output

# Auth
cli-web-notebooklm auth login               # interactive browser-based Google auth
cli-web-notebooklm auth status              # show current session validity
cli-web-notebooklm auth refresh             # force session refresh

# Notebooks
cli-web-notebooklm notebooks list           # list all notebooks
cli-web-notebooklm notebooks get --id <id>  # get notebook detail
cli-web-notebooklm notebooks create --name <name>
cli-web-notebooklm notebooks rename --id <id> --name <name>
cli-web-notebooklm notebooks delete --id <id>

# Sources
cli-web-notebooklm sources list --notebook <id>
cli-web-notebooklm sources add-url --notebook <id> --url <url>
cli-web-notebooklm sources add-pdf --notebook <id> --file <path>
cli-web-notebooklm sources add-text --notebook <id> --text <text> [--title <title>]
cli-web-notebooklm sources get --notebook <id> --source <id>
cli-web-notebooklm sources delete --notebook <id> --source <id>

# Q&A (Chat)
cli-web-notebooklm ask --notebook <id> --query "What is the main argument?"
cli-web-notebooklm ask --notebook <id> --query "..." --session <session_id>  # follow-up

# Audio Overview
cli-web-notebooklm audio generate --notebook <id>
cli-web-notebooklm audio status --notebook <id>
cli-web-notebooklm audio download --notebook <id> --out <path>
```

### Auth design

Google auth is the central challenge for this CLI. The approach:

1. **`auth login`** — launches a local browser flow using `selenium` or a simple `webbrowser.open()` pointing to Google OAuth, captures the resulting cookies, and stores them in `~/.config/cli-web-notebooklm/auth.json` with `chmod 600`.
2. **Cookie extraction strategy** — The most reliable approach is to use the Chrome DevTools MCP itself: navigate to NotebookLM, let the user log in, then use `javascript_tool` to extract `document.cookie` and the relevant `Authorization` headers from a test fetch. This captures the full live session.
3. **CSRF token** — Detect whether a CSRF header is needed (common in Google apps). Extract it from the session cookie value (Google's XSRF is typically derived from `SAPISID` via a HMAC computation) or from the page HTML.
4. **Token refresh** — Google session cookies have long validity but expire. `auth refresh` will navigate to `https://accounts.google.com` in a headless browser to refresh, then re-extract cookies.
5. **Multi-account** — Store sessions under named profiles: `~/.config/cli-web-notebooklm/auth_<profile>.json`.

### Session state
- `--notebook` is the primary context parameter. In REPL mode, `use <notebook_id>` sets a persistent notebook context so it doesn't need to be typed on every command.
- Undo/redo stack for mutating operations (notebook create/delete, source add/delete).

### Streaming response handling
The Q&A `ask` command will likely receive a streaming SSE response. The implementation will:
- Buffer the stream and print tokens incrementally in interactive mode.
- Buffer the entire stream and return the final concatenated text when `--json` is set.

### Audio download
The `audio download` command fetches a binary audio file (MP3 likely). It streams the response to disk, not to stdout. `--json` returns `{"path": "<output_path>", "size_bytes": N}`.

---

## Phase 4 — Implement (Code Generation)

### Package structure

```
notebooklm/
└── agent-harness/
    ├── NOTEBOOKLM.md                        # Software-specific SOP (from Phase 2)
    ├── setup.py
    └── cli_web/
        └── notebooklm/
            ├── __init__.py
            ├── __main__.py
            ├── notebooklm_cli.py            # Main Click group + REPL entry
            ├── core/
            │   ├── __init__.py
            │   ├── client.py                # httpx-based HTTP client
            │   ├── auth.py                  # Cookie/token management
            │   ├── session.py               # Notebook context + undo/redo
            │   └── models.py                # Dataclasses: Notebook, Source, Message, Audio
            ├── commands/
            │   ├── __init__.py
            │   ├── auth_cmd.py              # auth login/status/refresh
            │   ├── notebooks.py             # notebooks CRUD
            │   ├── sources.py               # sources CRUD (url/pdf/text)
            │   ├── ask.py                   # Q&A with streaming
            │   └── audio.py                 # audio overview generate/status/download
            ├── utils/
            │   ├── __init__.py
            │   ├── repl_skin.py             # Copied from plugin
            │   ├── output.py                # JSON/rich-table formatting
            │   └── config.py               # ~/.config/cli-web-notebooklm/ management
            └── tests/
                ├── __init__.py
                ├── TEST.md
                ├── fixtures/               # Captured responses for replay
                │   ├── notebooks_list.json
                │   ├── notebook_create.json
                │   ├── sources_list.json
                │   ├── source_add_url.json
                │   ├── source_add_pdf.json
                │   ├── ask_response.json    # or .jsonl for SSE
                │   ├── audio_generate.json
                │   └── audio_status.json
                ├── test_core.py
                └── test_e2e.py
```

### Key implementation notes per module

**`client.py`**
- Uses `httpx` for both sync and streaming requests.
- `_inject_auth(request)` attaches the full Cookie header and any CSRF header automatically via an httpx event hook.
- `_handle_response(response)` raises typed exceptions: `AuthError` (401/403), `NotFoundError` (404), `RateLimitError` (429), `ServerError` (5xx).
- For streaming (Q&A), exposes a `stream_lines(url, body)` generator.
- Exponential backoff on 429 with `Retry-After` header awareness.

**`auth.py`**
- `load_auth() -> AuthConfig` — reads `~/.config/cli-web-notebooklm/auth.json`, raises `AuthError` with actionable message if missing.
- `save_auth(config: AuthConfig)` — writes with `os.chmod(path, 0o600)`.
- `compute_sapisidhash(sapisid: str, origin: str) -> str` — implements Google's standard SAPISIDHASH computation (SHA-1 of `"{timestamp} {sapisid} {origin}"`), needed for the `Authorization: SAPISIDHASH` header that Google APIs require.
- `is_valid(config: AuthConfig) -> bool` — basic expiry check.

**`models.py`**
- `@dataclass Notebook(id, name, created_at, updated_at, source_count)`
- `@dataclass Source(id, notebook_id, type, title, url, status, created_at)`
- `@dataclass ChatMessage(query, response_text, citations, session_id)`
- `@dataclass AudioOverview(id, notebook_id, status, audio_url, created_at)`
- Each model has a `from_dict(d: dict) -> Self` classmethod.
- Each model has a `to_dict() -> dict` method for `--json` output.

**`ask.py`** (streaming command)
```python
@cli.command()
@click.option("--notebook", required=True)
@click.option("--query", required=True)
@click.option("--session", default=None)
@click.option("--json", "output_json", is_flag=True)
@click.pass_context
def ask(ctx, notebook, query, session, output_json):
    client = ctx.obj["client"]
    tokens = []
    for token in client.stream_ask(notebook, query, session):
        if output_json:
            tokens.append(token)
        else:
            click.echo(token, nl=False)
    if output_json:
        click.echo(json.dumps({"response": "".join(tokens)}))
    else:
        click.echo()  # final newline
```

**`audio.py`**
- `generate` — POST to start generation, returns task/job ID.
- `status` — GET to poll until `status == "ready"` or `status == "failed"`.
- `download` — GET the audio URL, stream bytes to `--out` path, print progress with `rich.progress` if not `--json`.

---

## Phase 5 — Plan Tests (TEST.md Part 1)

### Test inventory

| File | Unit tests | E2E fixture tests | E2E live tests | Subprocess tests |
|------|-----------|-------------------|----------------|-----------------|
| `test_core.py` | ~35 | — | — | — |
| `test_e2e.py` | — | ~15 | ~20 | ~8 |

### Unit test plan (`test_core.py`)

**`client.py` — ~10 tests**
- `test_get_success` — mock 200, verify parsed JSON returned
- `test_auth_injected` — verify Cookie and SAPISIDHASH headers present on every request
- `test_401_raises_auth_error` — mock 401, verify `AuthError` raised
- `test_404_raises_not_found` — mock 404, verify `NotFoundError` raised
- `test_429_triggers_backoff` — mock 429 then 200, verify retry with delay
- `test_500_raises_server_error` — mock 500, verify `ServerError` raised
- `test_stream_lines_yields_tokens` — mock SSE stream, verify generator yields expected strings
- `test_malformed_json_raises` — mock 200 with non-JSON body, verify exception
- `test_rate_limit_respects_retry_after_header` — mock 429 with `Retry-After: 2`, verify sleep called
- `test_multipart_upload` — mock 200 for PDF upload, verify multipart content-type set

**`auth.py` — ~8 tests**
- `test_load_auth_success` — write fixture auth.json, verify `AuthConfig` returned
- `test_load_auth_missing_raises` — no auth.json, verify `AuthError` with install instructions
- `test_save_auth_chmod_600` — call `save_auth`, verify file permissions = 0o600
- `test_compute_sapisidhash_format` — verify output matches `SAPISIDHASH {ts}_{hash}` format
- `test_compute_sapisidhash_deterministic` — same inputs yield same hash
- `test_is_valid_unexpired` — recent timestamp, verify True
- `test_is_valid_expired` — old timestamp, verify False
- `test_auth_config_roundtrip` — serialize and deserialize, verify equality

**`models.py` — ~10 tests**
- `test_notebook_from_dict` — valid dict, verify all fields populated correctly
- `test_notebook_from_dict_missing_optional` — optional fields absent, verify defaults
- `test_notebook_to_dict` — verify serialization keys match expected
- `test_source_from_dict_url_type`
- `test_source_from_dict_pdf_type`
- `test_source_from_dict_text_type`
- `test_chat_message_citations_parsed` — citations as list of source IDs
- `test_audio_status_enum` — verify status values mapped correctly
- `test_source_invalid_type_raises` — unknown source type, verify ValueError
- `test_model_to_dict_json_serializable` — all fields JSON-serializable

**`session.py` — ~7 tests**
- `test_set_notebook_context` — `session.use(id)`, verify `session.current_notebook == id`
- `test_clear_notebook_context`
- `test_undo_create` — push create operation, undo, verify delete called
- `test_undo_empty_stack` — undo on empty stack, verify no-op
- `test_redo_after_undo`
- `test_undo_stack_max_depth` — push > 20 items, verify oldest pruned
- `test_context_persists_across_commands`

### E2E test plan (`test_e2e.py`)

**Fixture replay tests (~15 tests)** — use saved JSON from `fixtures/`
- `test_list_notebooks_fixture` — replay `notebooks_list.json`, verify count and field presence
- `test_create_notebook_fixture` — replay `notebook_create.json`, verify `id` and `name` returned
- `test_list_sources_fixture`
- `test_add_url_source_fixture`
- `test_add_pdf_source_fixture`
- `test_add_text_source_fixture`
- `test_delete_source_fixture`
- `test_ask_fixture` — replay SSE stream fixture, verify concatenated text non-empty
- `test_ask_with_citations_fixture` — verify citations list populated
- `test_audio_generate_fixture` — verify job ID returned
- `test_audio_status_ready_fixture`
- `test_audio_status_pending_fixture`
- `test_audio_download_fixture` — mock binary response, verify file written to disk
- `test_error_invalid_notebook_fixture` — replay 404, verify CLI exits non-zero
- `test_error_unauthenticated_fixture` — replay 401, verify `AuthError` message shown

**Live tests (~20 tests)** — require valid `auth.json`, FAIL without it
- `test_live_list_notebooks` — verify list returns >= 0 items, each has `id` and `name`
- `test_live_notebook_create_rename_delete` — full round-trip: create → get → rename → get (verify name changed) → delete → list (verify absent)
- `test_live_add_url_source` — add URL source to test notebook → list sources → verify present → delete → verify absent
- `test_live_add_text_source` — add text → get → verify title and content → delete
- `test_live_add_pdf_source` — upload small test PDF → poll until status=ready → verify in sources list → delete
- `test_live_ask_basic` — ask question → verify non-empty response string
- `test_live_ask_followup` — ask → ask followup with session_id → verify second response references prior context
- `test_live_ask_no_sources` — ask in empty notebook → verify error or empty response handled gracefully
- `test_live_audio_generate_and_status` — generate audio → poll status up to 60s → verify status in (ready, pending, failed)
- `test_live_auth_status` — verify `auth status` returns valid session
- ... (additional workflow and edge case tests to bring total to ~20)

### Realistic workflow scenarios

**Scenario 1: Research session setup**
- Simulates: researcher importing three sources and querying them
- Operations: create notebook → add URL source → add PDF → add text snippet → ask "Summarize all three sources" → verify response mentions content from each
- Verified: source IDs in citations match the three added sources; response non-empty

**Scenario 2: Notebook lifecycle**
- Simulates: creating, using, and cleaning up a temporary notebook
- Operations: create notebook → rename → create source → list sources → delete source → list (verify empty) → delete notebook → list notebooks (verify absent)
- Verified: field consistency at each step; all reads after writes reflect the write

**Scenario 3: Audio overview generation**
- Simulates: generating a podcast overview for a research notebook
- Operations: create notebook → add URL source → generate audio → poll status every 5s up to 120s → download audio file → verify file size > 0
- Verified: audio file written to disk; JSON output contains path and size_bytes

**Scenario 4: Multi-turn Q&A**
- Simulates: an agent asking multiple questions in a conversation
- Operations: create notebook → add text source → ask Q1 → capture session_id → ask Q2 with session_id → ask Q3 with session_id
- Verified: each response is non-empty; later responses can reference earlier answers (spot-checked)

### Subprocess tests (~8 tests)
- `test_subprocess_help` — `cli-web-notebooklm --help` exits 0 with usage text
- `test_subprocess_json_notebooks_list` — `cli-web-notebooklm --json notebooks list` returns valid JSON array
- `test_subprocess_json_create_delete` — create notebook → capture ID from JSON → delete by ID
- `test_subprocess_json_add_url` — add URL source via subprocess, verify JSON response
- `test_subprocess_json_ask` — ask question via subprocess, verify JSON `{"response": "..."}` shape
- `test_subprocess_auth_status` — `cli-web-notebooklm --json auth status` returns `{"authenticated": true}`
- `test_subprocess_no_auth_error` — with no auth.json, `notebooks list` prints error and exits non-zero
- `test_subprocess_repl_entrypoint` — `cli-web-notebooklm` without subcommand spawns REPL (check banner in output)

---

## Phase 6 — Test (Write Tests)

### Implementation approach

1. Write `test_core.py` first (no auth required, fast feedback loop during development).
2. Write fixture-replay tests in `test_e2e.py`, using the captured `fixtures/` JSON from Phase 1.
3. Write live tests last — they require a real authenticated session.
4. Write subprocess tests after `pip install -e .` is complete.

### Special considerations for NotebookLM

**Streaming responses for `ask`:**
Store the SSE fixture as a `.jsonl` file (one JSON object per line, each representing a token event). The test replays this via `unittest.mock.patch` on `httpx.Client.stream`.

**PDF upload:**
The test PDF fixture should be a minimal valid PDF (can be generated programmatically or stored as a small binary in `fixtures/test.pdf`). The upload mock intercepts `httpx` at the transport layer.

**Audio download:**
The fixture is a small binary blob (even a few bytes) stored as `fixtures/audio_sample.mp3`. The download test verifies the file is written to the path specified by `--out`.

**Auth fixture:**
A `fixtures/auth.json` with fake (expired, placeholder) cookie values is used for unit tests and fixture replay tests only. Live tests load the real `~/.config/cli-web-notebooklm/auth.json`.

---

## Phase 7 — Document (Update TEST.md)

After the full test suite passes:

1. Run: `python3 -m pytest cli_web/notebooklm/tests/ -v --tb=short`
2. Run subprocess suite: `CLI_WEB_FORCE_INSTALLED=1 python3 -m pytest cli_web/notebooklm/tests/ -v -s -k subprocess`
3. Append to `TEST.md`:
   - Full pytest `-v --tb=no` output
   - Summary table: total tests, passed, failed, skipped, execution date
   - Coverage report (`pytest --cov=cli_web.notebooklm`)
   - Notes on any live tests that required manual verification (e.g., audio generation time)

---

## Phase 8 — Publish (Install to PATH)

### `setup.py`

```python
from setuptools import setup, find_namespace_packages

setup(
    name="cli-web-notebooklm",
    version="0.1.0",
    packages=find_namespace_packages(include=["cli_web.*"]),
    install_requires=[
        "click>=8.0",
        "httpx>=0.24",
        "rich>=13.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-web-notebooklm=cli_web.notebooklm.notebooklm_cli:cli",
        ]
    },
    python_requires=">=3.9",
)
```

Note: `cli_web/` has NO `__init__.py` — this is required for the namespace package pattern that allows multiple `cli-web-*` CLIs to coexist.

### Install and verify
```bash
cd notebooklm/agent-harness
pip install -e .
which cli-web-notebooklm   # must resolve
cli-web-notebooklm --help
cli-web-notebooklm --json notebooks list
CLI_WEB_FORCE_INSTALLED=1 python3 -m pytest cli_web/notebooklm/tests/ -v -s
# Output must contain: [_resolve_cli] Using installed command: /path/to/cli-web-notebooklm
```

---

## Key Risks and Mitigations

### Risk 1: Google's RPC format
NotebookLM almost certainly uses Google's internal BFE (Backend-For-Frontend) RPC format, which encodes requests as `f.req=[[["methodName","[[arg1,arg2]]",null,"generic"]]]`. This is JSON-in-JSON, URL-encoded.

**Mitigation:** During Phase 2, carefully decode the `f.req` parameter. The `batchexecute` endpoint may wrap multiple logical operations. Identify the method name token (e.g., `"CreateNotebook"`, `"AddSource"`) for each logical operation. Build a thin RPC client that wraps this encoding transparently.

### Risk 2: SAPISIDHASH computation
Google APIs require an `Authorization: SAPISIDHASH {timestamp}_{sha1hash}` header computed from the `SAPISID` cookie. Absent this, requests return 401/403 even with valid cookies.

**Mitigation:** Implement `compute_sapisidhash` in `auth.py` based on Google's published algorithm: `SHA1("{timestamp} {SAPISID} {origin}")`, where origin is `https://notebooklm.google.com`.

### Risk 3: Session cookie expiry
Google session cookies (particularly `__Secure-1PSID`) expire and require re-authentication. The CLI will not be able to automatically renew them without running a browser.

**Mitigation:** `auth refresh` re-launches a minimal browser session via the chrome-devtools MCP, navigates to NotebookLM, and re-extracts cookies. Include clear error messages when auth is stale.

### Risk 4: Streaming Q&A responses
The `ask` command likely returns tokens via Server-Sent Events or chunked JSON. The format may be non-standard (Google often uses `)]}'` prefix on JSON responses as XSSI protection).

**Mitigation:** In `client.py`, strip any `)]}'` prefix before JSON parsing. For SSE, handle the event stream format explicitly.

### Risk 5: PDF upload complexity
PDF upload may involve multiple steps: (1) request a signed upload URL, (2) PUT the binary to that URL, (3) poll a status endpoint. This multi-step flow needs to be encapsulated in `sources.py` transparently.

**Mitigation:** Capture the full sequence during Phase 1 Session B. Implement a `_upload_file(path)` method in `client.py` that handles all steps.

### Risk 6: Audio generation latency
Audio overview generation can take minutes. Live tests that wait for completion could be slow or flaky.

**Mitigation:** In live tests, set a timeout of 120s and assert `status in ("ready", "pending", "failed")` — not necessarily `"ready"`. A separate manual verification step confirms the full flow.

---

## Open Questions (to resolve in Phase 1/2)

1. What is the exact base URL for NotebookLM's API calls? (`notebooklm.googleapis.com`? `generativelanguage.googleapis.com`? An undocumented internal domain?)
2. Does the API use REST or Google's BFE RPC format?
3. Are sources processed synchronously or asynchronously? Is there a polling endpoint?
4. What is the exact shape of the Q&A streaming response?
5. Does audio generation use a separate job/task system with polling, or is it WebSocket-based?
6. Are there pagination parameters for notebook and source list endpoints?
7. Is there a rate limit and if so what is the threshold?
8. Is the audio output MP3 or another format?

These will all be answered by the traffic capture in Phase 1 and confirmed in Phase 2.

---

## Summary

| Phase | Deliverable |
|-------|------------|
| 1 — Record | `notebooklm/traffic-capture/raw-traffic.json` |
| 2 — Analyze | `NOTEBOOKLM.md` (API map, auth scheme, data model) |
| 3 — Design | Architecture section of `NOTEBOOKLM.md` |
| 4 — Implement | Full Python package under `cli_web/notebooklm/` |
| 5 — Plan Tests | `tests/TEST.md` Part 1 (plan) |
| 6 — Test | `test_core.py` + `test_e2e.py` passing |
| 7 — Document | `tests/TEST.md` Part 2 appended with results |
| 8 — Publish | `cli-web-notebooklm` on PATH, `pip install -e .` verified |
