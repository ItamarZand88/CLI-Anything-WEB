# Reconnaissance Report — ChatGPT (chatgpt.com)

**URL:** https://chatgpt.com
**Date:** 2026-03-17
**Skill version:** web-reconnaissance v0.1.0

---

## Pre-Recon Predictions (Expected Column — filled BEFORE running commands)

Before touching a browser, here is what we know about ChatGPT from public knowledge:

- OpenAI rebuilt chatgpt.com as a Next.js App Router application (not Pages Router) in 2023-2024.
  The original chat.openai.com was a Next.js Pages Router app; the new chatgpt.com domain uses
  App Router and React Server Components.
- The conversation API is a private internal REST API under `/backend-api/` or `/api/`. Requests
  use Bearer token auth sourced from an OAuth session (via Clerk or a custom auth provider).
- Streaming responses use Server-Sent Events (SSE) on the conversation POST endpoint, not WebSockets.
  Each SSE chunk delivers a `data: {...}` event with a partial message delta.
- File uploads go through a separate multipart endpoint before being referenced in message payloads.
- Protections: Cloudflare in front (cf-ray headers), aggressive rate limits per user account,
  and likely Turnstile or hCaptcha on auth flows.
- robots.txt is known to be restrictive — OpenAI disallows most crawlers from the chat interface.

---

## Step 1.1: Open & Observe

### Exact Commands

```bash
# 1. Open the target in a headed browser
npx @playwright/cli@latest -s=recon open "https://chatgpt.com"

# 2. Take a full DOM snapshot of the loaded page
npx @playwright/cli@latest -s=recon snapshot

# 3. Check for a common SPA root element
npx @playwright/cli@latest -s=recon eval "document.querySelector('#app, #root, #__next, #__nuxt, #__sveltekit')?.id || 'no-spa-root'"
```

### What to look for

- Is there an immediate login redirect, or does the page show a chat interface?
- Is content rendered on arrival (SSR) or does a spinner appear first (client-side hydration)?
- Does the URL change without a full page reload when clicking "New chat" or switching conversations?
  (Confirms client-side routing — a prerequisite for the Force SPA Navigation trick to work.)
- Are there any cookie/consent banners that must be dismissed before the main UI is usable?
- Does the page gate behind Cloudflare's "Checking your browser" challenge on fresh sessions?

---

## Step 1.2: Framework Detection

### Exact Commands

```bash
# Next.js Pages Router check — will return null if App Router
npx @playwright/cli@latest -s=recon eval "document.getElementById('__NEXT_DATA__')?.textContent?.substring(0, 200)"

# Next.js App Router check — look for RSC flight push marker
npx @playwright/cli@latest -s=recon eval "document.documentElement.outerHTML.includes('self.__next_f.push') ? 'next-app-router' : 'not-app-router'"

# Nuxt check (should be negative)
npx @playwright/cli@latest -s=recon eval "typeof window.__NUXT__ !== 'undefined' ? JSON.stringify(Object.keys(window.__NUXT__)) : 'not-nuxt'"

# Remix check (should be negative)
npx @playwright/cli@latest -s=recon eval "typeof window.__remixContext !== 'undefined' ? 'remix' : 'not-remix'"

# Redux / Preloaded state check
npx @playwright/cli@latest -s=recon eval "typeof window.__INITIAL_STATE__ !== 'undefined' ? 'has-state' : typeof window.__PRELOADED_STATE__ !== 'undefined' ? 'has-preloaded' : 'no-state'"

# Generic SPA root (confirm #__next or similar)
npx @playwright/cli@latest -s=recon eval "document.querySelector('#app, #root, #__next, #__nuxt, #__sveltekit')?.id || 'no-spa-root'"
```

### Expected Results

| Check | Expected return value | Reasoning |
|---|---|---|
| `__NEXT_DATA__` | `null` | App Router does not embed a Pages Router blob |
| `self.__next_f.push` | `'next-app-router'` | RSC streaming uses flight push marker |
| `__NUXT__` | `'not-nuxt'` | Not a Nuxt app |
| `__remixContext` | `'not-remix'` | Not a Remix app |
| Preloaded state | `'no-state'` | Auth state is managed by Next.js session, not Redux |
| SPA root | `'__next'` | Next.js always mounts under `#__next` |

---

## Step 1.3: Network Traffic Analysis (Force SPA Navigation Trick)

### Why ChatGPT Needs the SPA Trick

ChatGPT is an App Router Next.js application. On the first load, the server renders the shell of
the UI (sidebar with conversation list, empty chat area) as React Server Components. The conversation
messages for the active chat may be embedded in the initial RSC flight payload. This means the
initial page load trace will show either zero XHR requests or only RSC flight requests — not the
clean `/backend-api/conversation` calls we need.

The Force SPA Navigation trick bypasses this: once logged in, clicking "New chat" or selecting a
different conversation in the sidebar triggers client-side navigation. The SPA router calls the
conversation history and message APIs directly, without a full page reload. Those API calls are
the ones we need to capture.

### Exact Commands

```bash
# CRITICAL: Start tracing BEFORE any navigation
npx @playwright/cli@latest -s=recon tracing-start

# Trigger client-side navigation #1 — click "New chat" button
# (creates a new conversation, fires the conversation-init API)
npx @playwright/cli@latest -s=recon click "button[aria-label='New chat'], a[href='/']"

# Trigger client-side navigation #2 — click an existing conversation in the sidebar
# (fires the conversation history fetch for that conversation ID)
npx @playwright/cli@latest -s=recon click "nav a[href*='/c/']"

# Trigger client-side navigation #3 — click a second conversation
# (confirms the conversation API pattern with a second conversation ID)
npx @playwright/cli@latest -s=recon click "nav li:nth-child(2) a"

# Trigger an action that fires the full conversation message stream:
# type a message and submit it (this is the most important captured request)
npx @playwright/cli@latest -s=recon fill "textarea[data-id='root'], #prompt-textarea" "hello"
npx @playwright/cli@latest -s=recon press "Enter"

# Wait for the streaming response to begin (look for the response container)
npx @playwright/cli@latest -s=recon wait "[data-message-author-role='assistant']"

# Stop tracing now that we have a complete conversation round-trip
npx @playwright/cli@latest -s=recon tracing-stop

# Parse the trace into structured JSON
python scripts/parse-trace.py .playwright-cli/traces/ --output recon-traffic.json
```

### What the Trace Should Reveal

After parsing `recon-traffic.json`, filter for:

1. **`/backend-api/conversations`** — GET request listing all conversations.
   This is the conversation index endpoint. Parameters: `offset`, `limit`, `order`.

2. **`/backend-api/conversation/<conversation_id>`** — GET request fetching the full
   message history for a specific conversation. Returns a JSON structure with `mapping`
   (a dict of message nodes) and `current_node`.

3. **`/backend-api/conversation`** — POST request that initiates a new message.
   This is the SSE streaming endpoint. The request body contains:
   - `model`: string (e.g., `"gpt-4o"`)
   - `messages`: array of message objects
   - `conversation_id`: string or null for new conversations
   - `parent_message_id`: UUID of the parent node
   - `action`: `"next"` for a follow-up, `"variant"` for regeneration

4. **`/backend-api/me`** — GET request for the authenticated user profile.
   Auth token validity check; returns account tier and user ID.

5. **`/backend-api/models`** — GET request returning available model list.

6. **`/backend-api/files/`** — POST multipart endpoint for file uploads (if a file is attached).

7. **Auth token source** — look for the `Authorization: Bearer <token>` header in all
   backend-api requests. The token is a short-lived JWT issued by OpenAI's auth system.
   Also check for `__Secure-next-auth.session-token` cookie as the session credential.

### How the Force SPA Navigation Trick Reveals the Conversation API

On initial load, Next.js App Router streams the full conversation UI as RSC flight data. This means
the conversation message content is delivered via `self.__next_f.push([...])` chunks — not via an
XHR to `/backend-api/conversation/<id>`. So the initial load trace is "empty" from a useful API
perspective.

The moment you click a second conversation in the sidebar, the App Router's client-side navigation
kicks in. It cannot re-use the RSC-streamed data for a different conversation, so it makes a real
XHR call to `/backend-api/conversation/<conversation_id>` to fetch that conversation's messages.
This is the endpoint we need. Without the Force SPA trick, we would never see it in the trace.

Similarly, submitting a message fires the SSE POST to `/backend-api/conversation` — this is the
core CLI target and would not appear at all in a passive observation of the initial page load.

---

## Step 1.4: Protection Assessment

### All-in-One Detection Command

```bash
npx @playwright/cli@latest -s=recon eval "(() => {
  const body = document.body.textContent.toLowerCase();
  const html = document.documentElement.outerHTML;
  const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
  return {
    cloudflare: body.includes('cloudflare') || html.includes('cf-ray') || html.includes('__cf_bm'),
    captcha: !!document.querySelector('.g-recaptcha, #px-captcha, .h-captcha'),
    akamai: scripts.some(s => s.includes('akamai')),
    datadome: scripts.some(s => s.includes('datadome')),
    perimeterx: scripts.some(s => s.includes('perimeterx') || s.includes('px-')),
    rateLimit: html.includes('429') || body.includes('too many requests'),
    fingerprinting: scripts.some(s => s.includes('fingerprint') || s.includes('fp-'))
  };
})()"
```

### Detailed Cloudflare Check

```bash
npx @playwright/cli@latest -s=recon eval "(() => {
  const cookies = document.cookie;
  const html = document.documentElement.outerHTML;
  return {
    cfBmCookie: cookies.includes('__cf_bm'),
    cfClearance: cookies.includes('cf_clearance'),
    cfRay: html.includes('cf-ray'),
    challengePage: document.body.textContent.includes('Checking your browser'),
    turnstile: !!document.querySelector('.cf-turnstile, [data-sitekey]')
  };
})()"
```

### robots.txt Check

```bash
npx @playwright/cli@latest -s=recon open "https://chatgpt.com/robots.txt"
npx @playwright/cli@latest -s=recon snapshot
```

### Rate Limit Check (run after Step 1.3 trace)

```bash
npx @playwright/cli@latest -s=recon eval "(() => {
  const body = document.body.textContent.toLowerCase();
  return {
    is429: document.title.includes('429') || body.includes('429'),
    tooManyRequests: body.includes('too many requests'),
    retryAfter: body.includes('retry-after'),
    rateLimitHit: body.includes('rate limit')
  };
})()"
```

### Specific hCaptcha Check (OpenAI uses hCaptcha on auth)

```bash
npx @playwright/cli@latest -s=recon eval "!!document.querySelector('.h-captcha, iframe[src*=\"hcaptcha\"]') ? 'hcaptcha-present' : 'no-hcaptcha'"
```

---

## Step 1.5: RECON-REPORT.md

---

## Site Architecture

| Aspect | Expected (pre-recon) | Confirmed (post-recon) |
|--------|---------------------|------------------------|
| Type | SSR+SPA Hybrid | (fill after Step 1.1) |
| Framework | Next.js App Router | (fill after Step 1.2) |
| SSR Data | RSC flight payload (`self.__next_f.push`) | (fill after Step 1.2) |
| SPA Root | `#__next` | (fill after Step 1.1 eval) |
| Client-side routing | Yes — URL changes without reload | (fill after Step 1.1 observation) |
| Auth wall | Yes — login required for API access | (fill after Step 1.1) |

---

## API Surface

| Endpoint | Method | Auth? | Discovered in | Notes |
|----------|--------|-------|---------------|-------|
| `/backend-api/me` | GET | Yes — Bearer JWT | Step 1.3 trace | User profile, account tier |
| `/backend-api/models` | GET | Yes — Bearer JWT | Step 1.3 trace | Available model list |
| `/backend-api/conversations` | GET | Yes — Bearer JWT | Step 1.3 trace | Paginated conversation list; params: `offset`, `limit`, `order` |
| `/backend-api/conversation/<id>` | GET | Yes — Bearer JWT | Step 1.3 (SPA trick) | Full conversation history; returns message mapping |
| `/backend-api/conversation` | POST | Yes — Bearer JWT | Step 1.3 trace | **Core SSE streaming endpoint** — sends message, receives streamed response |
| `/backend-api/conversation/<id>` | PATCH | Yes — Bearer JWT | Step 1.3 trace | Update conversation title or archived status |
| `/backend-api/conversation/<id>` | DELETE | Yes — Bearer JWT | Step 1.3 trace | Delete a conversation |
| `/backend-api/files/` | POST | Yes — Bearer JWT | Step 1.3 trace | Multipart file upload; returns `file_id` for use in messages |
| `/auth/session` | GET | Yes — session cookie | Step 1.3 trace | Returns the current JWT access token from the session |

- **Protocol:** REST (JSON) + SSE (streaming)
- **Total endpoints expected:** 8-12 distinct endpoints
- **Auth type:** Bearer JWT (short-lived, ~1 hour). Sourced from `GET /auth/session` using
  the `__Secure-next-auth.session-token` cookie as the session credential. The CLI must implement
  token refresh before expiry.
- **SSE streaming:** The POST `/backend-api/conversation` response is a Server-Sent Events
  stream, not a standard JSON response. Each event is `data: {"id":"...","object":"...","delta":{"content":"..."}}`.
  The stream ends with `data: [DONE]`.

---

## Protections

| Protection | Expected | Confirmed |
|-----------|----------|-----------|
| Cloudflare | Yes — cf-ray headers, `__cf_bm` cookie present | (fill after Step 1.4) |
| hCaptcha | Yes — on login/signup flows | (fill after Step 1.4) |
| reCAPTCHA v2/v3 | Unlikely (OpenAI uses hCaptcha) | (fill after Step 1.4) |
| Rate limits per user | Yes — hard 429 limits per account/model | (fill after Step 1.4 trace) |
| Rate limits per model | Yes — GPT-4o has stricter limits than GPT-3.5 | (fill after Step 1.4 trace) |
| WAF (Akamai) | No | (fill after Step 1.4) |
| WAF (PerimeterX) | No | (fill after Step 1.4) |
| WAF (DataDome) | No | (fill after Step 1.4) |
| robots.txt | Restrictive — `/c/` conversations blocked | (fill after Step 1.4 robots.txt check) |
| Token expiry | Yes — JWT expires ~1 hour; session cookie longer | (fill from auth/session response) |
| TOS enforcement | Yes — OpenAI TOS prohibits automated scraping of conversations | Known |

---

## Recommended Strategy

**Capture approach:** API-first (with Protected-Manual for initial auth session)

**Rationale:**

ChatGPT exposes a well-structured internal REST API under `/backend-api/`. While this API is
not officially documented as public, it is not obfuscated — it uses standard JSON request/response
patterns and standard Bearer token auth. The API-first strategy applies here with one key modification:
the initial auth session must be established manually (the user logs in via a real browser session),
because the login flow uses hCaptcha and Cloudflare challenges that cannot be automated.

Once a session is established and the `__Secure-next-auth.session-token` cookie is captured, the
CLI can exchange it for a short-lived JWT via `GET /auth/session`, then use that JWT for all
subsequent API calls. This pattern is fully automatable after the one-time manual browser login.

**CLI generation impact:**

The generated CLI needs:
1. A `chatgpt auth login` command that opens a browser for manual login and persists the session
   cookie to a config file (keyring storage preferred).
2. A `chatgpt auth refresh` command (or auto-refresh logic in the client) that calls `GET /auth/session`
   to get a fresh JWT when the current one is within 5 minutes of expiry.
3. An `httpx` client configured with `stream=True` for conversation POST calls, with an SSE decoder
   that reconstructs the full response from delta chunks.
4. File upload pre-processing: if a file is attached to a message, upload it first via `POST /backend-api/files/`
   and inject the returned `file_id` into the message payload.

**The CLI command surface would look like:**

```bash
chatgpt send "What is the capital of France?"
chatgpt send --model gpt-4o "Explain RSC in 3 bullets"
chatgpt send --conversation <id> "Follow up question"
chatgpt conversations list
chatgpt conversations show <id>
chatgpt conversations delete <id>
chatgpt conversations rename <id> "New title"
chatgpt models list
chatgpt upload ./file.pdf
chatgpt auth login        # opens browser, persists session
chatgpt auth refresh      # refresh JWT from session cookie
chatgpt auth status       # show current auth state
```

---

## Warnings

### 1. Server-Sent Events (SSE) Streaming — Non-trivial to implement

The `POST /backend-api/conversation` endpoint does NOT return a normal JSON response. It returns
an SSE stream that delivers incremental message deltas. The CLI client must:

- Use `httpx` with `stream=True` (or `requests` with `stream=True`)
- Parse each `data: {...}` line from the stream
- Accumulate deltas into the final response text
- Handle `data: [DONE]` as the stream terminator
- Handle mid-stream errors gracefully (the stream can deliver error events before closing)
- Print to stdout incrementally so the user sees tokens as they arrive (not all at once at the end)

This is significantly more complex than a standard JSON REST call. If the CLI implementation uses
a synchronous httpx client, it must use the `with client.stream(...)` context manager. For async
CLIs, use `async for line in response.aiter_lines()`.

**Example SSE parsing pattern (pseudocode):**
```python
with httpx.stream("POST", "/backend-api/conversation", json=payload) as resp:
    for line in resp.iter_lines():
        if line.startswith("data: ") and line != "data: [DONE]":
            chunk = json.loads(line[6:])
            delta = chunk.get("message", {}).get("content", {}).get("parts", [""])[0]
            print(delta, end="", flush=True)
```

Note: the exact delta structure has changed across ChatGPT versions. The trace will reveal the
current format; capture a full SSE stream in Step 1.3 to get the actual structure.

### 2. Conversation State — Stateful, not Stateless

Unlike a typical REST API that is fully stateless, ChatGPT conversation calls are stateful:

- Each message must reference a `parent_message_id` (the UUID of the last assistant message node)
- The `conversation_id` must be passed for follow-up messages; omit it for new conversations
- Branching (regenerating a response) requires sending `action: "variant"` with the correct
  parent UUID
- If the CLI loses track of the current `conversation_id` + `current_node`, the conversation thread
  breaks and subsequent messages start a new conversation instead

**The CLI must maintain a local conversation state file** (e.g., `~/.chatgpt-cli/state.json`) that
records the active `conversation_id` and `parent_message_id` between invocations.

### 3. File Uploads — Two-Step Process

Attaching a file to a message is NOT done by including file content in the conversation POST. It is
a two-step process:

1. Upload the file to `POST /backend-api/files/` as multipart form data. The response returns a
   `file_id` (a UUID) and `download_url`.
2. Reference the `file_id` in the conversation message payload under the `attachments` or
   `content_parts` field.

The CLI must handle this transparently: when the user passes `--file ./doc.pdf`, the CLI should
upload first, receive the `file_id`, then include it in the message payload automatically.

Additionally, file uploads are subject to their own rate limits and size restrictions. The current
known limits are approximately 512MB per file and 25 files per message, but these may vary by
account tier.

### 4. Short-Lived JWT — Token Refresh Required

The Bearer JWT obtained from `GET /auth/session` expires approximately every 1 hour (the exact
value is in the JWT's `exp` claim). If the CLI is used in a long-running script or automation,
the token will expire mid-run and all subsequent requests will return 401.

The generated `client.py` must check token expiry before every API call and refresh silently if
within the expiry window. The refresh itself requires the session cookie to be valid, which has a
much longer lifetime (weeks to months). If the session cookie also expires, the user must re-run
`chatgpt auth login`.

### 5. Rate Limits — Per-Model, Per-Account

ChatGPT enforces rate limits at multiple levels:

- **Per model:** GPT-4o has strict message-per-hour limits on free and Plus plans; GPT-3.5 is more
  lenient. The limits are not published precisely but free-tier users hit them within ~10-20 messages
  per hour on GPT-4o.
- **Per account tier:** Free users have the most restrictive limits; Team and Enterprise accounts
  have much higher limits.
- **429 handling:** The API returns `429 Too Many Requests` with a `Retry-After` header indicating
  when the rate limit window resets. The CLI must respect this header.

The generated `client.py` should implement exponential backoff starting at 1 second, respecting
`Retry-After` when present, and surfacing the rate limit message to the user clearly.

### 6. Cloudflare — Challenge Pages on Fresh Sessions

On a fresh browser session or from a new IP address, Cloudflare may serve a challenge page before
allowing access to chatgpt.com. This is transparent in a headed browser but will block headless
automated requests entirely.

For the CLI use case (using the Bearer JWT directly without a browser), Cloudflare challenges are
generally not an issue because the API calls go directly to the `/backend-api/` path with a valid
auth header — not through the Cloudflare WAF that protects the HTML pages. However, if OpenAI
tightens this in the future, the CLI may begin seeing 403 responses from Cloudflare. The RECON-REPORT
should note this as a future risk.

### 7. OpenAI Terms of Service

OpenAI's Terms of Service prohibit using automated means to access the ChatGPT web interface as a
substitute for the official OpenAI API. OpenAI offers a paid API (api.openai.com) with official
client libraries, documented endpoints, and SLAs. A CLI built on the internal `/backend-api/` is
technically in violation of the TOS.

**Recommendation:** For production use, strongly prefer the official `openai` Python library
targeting `api.openai.com`. The web interface CLI is appropriate only for personal/educational
exploration and use cases where the official API is not suitable (e.g., accessing web-browsing
or DALL-E features not yet in the API).

---

## Is ChatGPT CLI-Suitable?

**Verdict: Yes, with significant caveats.**

| Factor | Assessment |
|--------|------------|
| API clarity | Good — well-structured REST+SSE under `/backend-api/` |
| Auth complexity | Medium — one-time manual login; then automated JWT refresh |
| Streaming complexity | High — SSE deltas require non-trivial client implementation |
| State management | High — conversation_id + parent_message_id must be tracked |
| File upload complexity | Medium — two-step upload-then-reference pattern |
| Rate limits | Present but manageable — surfaced clearly, respect Retry-After |
| Protections | Cloudflare present but not blocking on authenticated API calls |
| TOS risk | Significant — consider directing users to official API instead |
| Overall CLI viability | Viable for personal use; not recommended for production |

**The strongest argument for building this CLI** is for personal power-user workflows: scripting
conversation summaries, batch-sending prompts, or integrating ChatGPT responses into shell pipelines.
The biggest technical hurdle is the SSE streaming implementation; once that is solid, everything
else is standard REST.

**The strongest argument against** is the official OpenAI API: it is documented, stable, has
official Python bindings, costs money but is predictable, and does not violate TOS. For most CLI
use cases, `openai chat.completions.create(...)` is the right answer.

---

## Complete Command Reference (All 5 Steps)

```bash
# ── STEP 1.1: OPEN & OBSERVE ──────────────────────────────────────────────
npx @playwright/cli@latest -s=recon open "https://chatgpt.com"
npx @playwright/cli@latest -s=recon snapshot
npx @playwright/cli@latest -s=recon eval "document.querySelector('#app, #root, #__next, #__nuxt, #__sveltekit')?.id || 'no-spa-root'"

# ── STEP 1.2: FRAMEWORK DETECTION ────────────────────────────────────────
npx @playwright/cli@latest -s=recon eval "document.getElementById('__NEXT_DATA__')?.textContent?.substring(0, 200)"
npx @playwright/cli@latest -s=recon eval "document.documentElement.outerHTML.includes('self.__next_f.push') ? 'next-app-router' : 'not-app-router'"
npx @playwright/cli@latest -s=recon eval "typeof window.__NUXT__ !== 'undefined' ? JSON.stringify(Object.keys(window.__NUXT__)) : 'not-nuxt'"
npx @playwright/cli@latest -s=recon eval "typeof window.__remixContext !== 'undefined' ? 'remix' : 'not-remix'"
npx @playwright/cli@latest -s=recon eval "typeof window.__INITIAL_STATE__ !== 'undefined' ? 'has-state' : typeof window.__PRELOADED_STATE__ !== 'undefined' ? 'has-preloaded' : 'no-state'"

# ── STEP 1.3: NETWORK TRAFFIC (FORCE SPA NAVIGATION TRICK) ───────────────
npx @playwright/cli@latest -s=recon tracing-start
npx @playwright/cli@latest -s=recon click "button[aria-label='New chat'], a[href='/']"
npx @playwright/cli@latest -s=recon click "nav a[href*='/c/']"
npx @playwright/cli@latest -s=recon click "nav li:nth-child(2) a"
npx @playwright/cli@latest -s=recon fill "#prompt-textarea" "hello"
npx @playwright/cli@latest -s=recon press "Enter"
npx @playwright/cli@latest -s=recon wait "[data-message-author-role='assistant']"
npx @playwright/cli@latest -s=recon tracing-stop
python scripts/parse-trace.py .playwright-cli/traces/ --output recon-traffic.json

# ── STEP 1.4: PROTECTION ASSESSMENT ──────────────────────────────────────
npx @playwright/cli@latest -s=recon eval "(() => {
  const body = document.body.textContent.toLowerCase();
  const html = document.documentElement.outerHTML;
  const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
  return {
    cloudflare: body.includes('cloudflare') || html.includes('cf-ray') || html.includes('__cf_bm'),
    captcha: !!document.querySelector('.g-recaptcha, #px-captcha, .h-captcha'),
    akamai: scripts.some(s => s.includes('akamai')),
    datadome: scripts.some(s => s.includes('datadome')),
    perimeterx: scripts.some(s => s.includes('perimeterx') || s.includes('px-')),
    rateLimit: html.includes('429') || body.includes('too many requests'),
    fingerprinting: scripts.some(s => s.includes('fingerprint') || s.includes('fp-'))
  };
})()"
npx @playwright/cli@latest -s=recon eval "(() => {
  const cookies = document.cookie;
  const html = document.documentElement.outerHTML;
  return {
    cfBmCookie: cookies.includes('__cf_bm'),
    cfClearance: cookies.includes('cf_clearance'),
    cfRay: html.includes('cf-ray'),
    challengePage: document.body.textContent.includes('Checking your browser'),
    turnstile: !!document.querySelector('.cf-turnstile, [data-sitekey]')
  };
})()"
npx @playwright/cli@latest -s=recon eval "!!document.querySelector('.h-captcha, iframe[src*=\"hcaptcha\"]') ? 'hcaptcha-present' : 'no-hcaptcha'"
npx @playwright/cli@latest -s=recon open "https://chatgpt.com/robots.txt"
npx @playwright/cli@latest -s=recon snapshot

# ── STEP 1.5: REPORT ──────────────────────────────────────────────────────
# Fill in the Confirmed column of this RECON-REPORT.md using the outputs above.
```

---

*Report generated by web-reconnaissance skill v0.1.0 — Expected column filled pre-recon from public knowledge; Confirmed column to be filled after running commands.*
