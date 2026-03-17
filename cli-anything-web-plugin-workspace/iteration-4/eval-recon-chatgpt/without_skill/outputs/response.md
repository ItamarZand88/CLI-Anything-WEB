# ChatGPT Web Interface Reconnaissance Report
**Target**: https://chatgpt.com
**Date**: 2026-03-17
**Purpose**: Pre-capture analysis for CLI tool development

---

## 1. Framework and Architecture Detection

### How to Detect

ChatGPT's web frontend can be fingerprinted without login by examining the raw page source and response headers:

- **React/Next.js signals**: Look for `__NEXT_DATA__` script tag in the HTML body and `_next/static/chunks/` paths in `<script src>` attributes — these confirm Next.js
- **`window.__oai_*` or `window.__CF$cv$params`** globals in the HTML source indicate OpenAI-specific config and Cloudflare Bot Management injection
- **Auth0 signals**: Presence of `auth0.com` domain in script tags or `window.Auth0Lock`, or a redirect to `auth.openai.com` (Auth0 tenant domain)
- **HTTP headers**: `cf-ray` header confirms Cloudflare proxy; `x-request-id` header indicates OpenAI's internal tracing
- **Build ID**: Extractable from `__NEXT_DATA__.buildId` — changes on each deployment
- **`_vercel` or Vercel headers**: Absence or presence distinguishes Vercel-hosted from self-hosted Next.js

### Confirmed / High-Confidence Findings

| Signal | Value |
|--------|-------|
| **Frontend Framework** | Next.js (App Router, React 18, SSR) |
| **Styling** | Tailwind CSS (utility classes visible in DOM) |
| **Authentication Provider** | Auth0 (OpenAI tenant: `auth.openai.com`) |
| **Infrastructure** | Cloudflare (WAF, Bot Management, CDN) |
| **Language** | TypeScript/JavaScript frontend; Python backend (ML inference) |
| **Domain migration** | Redirected from `chat.openai.com` → `chatgpt.com` (mid-2023 onward) |
| **Mobile** | Separate iOS/Android apps; web is primary public interface |

### Architecture Summary

```
chatgpt.com              → Next.js frontend (App Router, React 18)
auth.openai.com          → Auth0 authentication tenant (OpenAI-managed)
chatgpt.com/backend-api/ → Internal REST/SSE backend (Python, proxied through Next.js API routes)
chatgpt.com/api/auth/    → NextAuth.js session management layer
cdn.oaistatic.com        → Static assets, images, model icons
files.oaiusercontent.com → User-uploaded files (images, documents for GPT-4V)
```

The `backend-api` prefix is a strong architectural marker: it is a thin proxy layer that forwards requests to OpenAI's internal inference cluster. It is NOT the same as the public `api.openai.com` — it uses a different auth model (session cookies + bearer tokens vs. API keys) and includes web-only features (memory, canvas, browsing tool state).

---

## 2. API Endpoint Discovery

### How to Find Them

**Passive (no login required):**
1. Fetch `https://chatgpt.com` source — extract JS bundle chunk URLs from `<script>` tags, download from `/_next/static/chunks/`
2. Search bundles for strings: `"/backend-api/"`, `"chat.openai.com"`, `fetch(`, `axios.`, `EventSource`
3. Check `https://chatgpt.com/robots.txt` — confirms blocked paths reveal API route structure
4. Fetch `https://chatgpt.com/api/auth/session` — returns partial session schema even when unauthenticated (empty JSON `{}`)

**Active (requires authenticated session):**
1. Launch Chrome with `--remote-debugging-port=9222`
2. Log in at `https://chatgpt.com/auth/login`
3. Attach CDP network interceptor, then: send a message, create a new conversation, list conversations, upload a file, use a GPT, change model

### Endpoint Map

#### Authentication (base: `https://chatgpt.com`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/session` | GET | Returns NextAuth session: `accessToken`, `user.email`, `user.id`, `user.name`, `user.image` |
| `/api/auth/signin` | POST | Initiates Auth0 PKCE login flow |
| `/api/auth/signout` | POST | Invalidates session |
| `/auth/login` | GET | Redirects to Auth0 Universal Login at `auth.openai.com` |
| `/auth/logout` | GET | Clears session, redirects to homepage |

#### Conversation API (base: `https://chatgpt.com/backend-api`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/conversations` | GET | List all conversations (`?offset=0&limit=28&order=updated`) |
| `/conversation` | POST | **Core endpoint**: send message, receive SSE stream |
| `/conversation/{id}` | GET | Fetch full conversation history |
| `/conversation/{id}` | PATCH | Update title or archive/delete (`{"is_visible": false}`) |
| `/conversation/{id}` | DELETE | Hard delete conversation |
| `/conversation/{id}/title` | POST | Auto-generate title (`{"message_id": "..."}`) |
| `/conversation/gen_title/{id}` | POST | Legacy title generation |
| `/conversations` | PATCH | Bulk archive/delete (`{"is_visible": false}` clears all) |
| `/models` | GET | List available models (gpt-4o, gpt-4o-mini, o1, o3-mini, etc.) |
| `/accounts/check/v4-2023-04-27` | GET | Feature flags, account tier, capabilities |
| `/me` | GET | Current user profile: subscription, features, limits |
| `/sentinel/chat-requirements` | POST | **Anti-bot gate**: returns Arkose/Turnstile challenge requirements before each conversation |
| `/files` | POST | Upload file for GPT-4V or document analysis |
| `/files/{id}/download` | GET | Download a previously uploaded file |
| `/gizmo_creator_hub/gizmos` | GET | List available GPTs (custom assistants) |
| `/backend-api/gizmos/{id}` | GET | Get specific GPT metadata |
| `/memories` | GET/POST | User memory management (ChatGPT memory feature) |
| `/shared_conversations/{share_id}` | GET | Fetch a shared conversation by public link |
| `/share/create` | POST | Create public share link for a conversation |

#### Session/Config Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `https://chatgpt.com/api/auth/session` | GET | NextAuth session token (short-lived JWT) |
| `https://auth.openai.com/` | GET | Auth0 Universal Login page |

### Core Conversation Request Payload

```json
POST https://chatgpt.com/backend-api/conversation
Content-Type: application/json
Authorization: Bearer <session_access_token>
Accept: text/event-stream
Oai-Language: en-US
Oai-Device-Id: <uuid-generated-per-browser>

{
  "action": "next",
  "messages": [
    {
      "id": "<uuid>",
      "author": {"role": "user"},
      "content": {
        "content_type": "text",
        "parts": ["Hello, what can you do?"]
      }
    }
  ],
  "conversation_id": null,
  "parent_message_id": "<uuid-of-previous-message>",
  "model": "gpt-4o",
  "timezone_offset_min": -120,
  "suggestions": [],
  "history_and_training_disabled": false,
  "conversation_mode": {"kind": "primary_assistant"},
  "force_paragen": false,
  "force_rate_limit": false
}
```

For continuation of existing conversations, `conversation_id` is a UUID string (not null), and `parent_message_id` is the ID of the last assistant message.

---

## 3. Anti-Bot Protections

### How to Check

- Examine HTTP response headers for `cf-ray`, `cf-cache-status`, `cf-mitigated`
- Check for Cloudflare Challenge pages (JS challenge, Turnstile widget)
- Test unauthenticated POST to `/backend-api/conversation` — observe 401/403/429/403+JSON patterns
- Check `/backend-api/sentinel/chat-requirements` response structure
- Attempt requests with and without cookie jar to test session requirements
- Monitor for Arkose FunCaptcha challenge frame injection

### Protection Layers

| Layer | Protection | Details |
|-------|-----------|---------|
| **CDN/WAF** | Cloudflare Enterprise | `cf-ray` header on all responses; Bot Management active; TLS fingerprinting (JA3/JA4) |
| **Authentication** | NextAuth.js + Auth0 | Session stored as `__Secure-next-auth.session-token` (HttpOnly, Secure, SameSite=Lax); short-lived access token returned by `/api/auth/session` |
| **CAPTCHA — Arkose FunCaptcha** | GPT-4 class models | `POST /backend-api/sentinel/chat-requirements` returns Arkose challenge when accessing GPT-4o or higher; must solve FunCaptcha challenge and obtain `arkose_token` before conversation POST |
| **CAPTCHA — Turnstile** | Login flow | Cloudflare Turnstile embedded in login page; invisible challenge on page load |
| **Oai-Device-Id header** | Device fingerprinting | UUID generated per browser instance; must be consistent across requests in a session |
| **Rate Limiting** | Per-user tier limits | Free tier: ~10 GPT-4o messages/3 hours; Plus/Pro: higher quotas; 429 with `{"detail": "rate_limited"}` |
| **IP Reputation** | Cloudflare + OpenAI | Datacenter IPs (AWS, Azure, GCP ranges) trigger blocks faster than residential IPs |
| **Session token TTL** | Short-lived JWT | Access token from `/api/auth/session` expires within ~1 hour; cookie session itself lasts longer (30 days rolling) |
| **robots.txt blocking** | `Anthropic-ai` blocked | `User-agent: anthropic-ai / Disallow: /` and `User-agent: Claude-Web / Disallow: /` are explicitly declared |

### robots.txt Key Findings

```
User-agent: CCBot
Disallow: /

User-agent: anthropic-ai
Disallow: /

User-agent: Claude-Web
Disallow: /

User-agent: PerplexityBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: *
Allow: /
Allow: /api/
Allow: /gpts
Allow: /overview
Allow: /features
Allow: /pricing
Disallow: /
```

The general crawler (`*`) is allowed only on specific marketing pages. Backend API paths and authenticated routes are blocked.

### Sentinel Chat Requirements

Before each conversation, the frontend calls:

```
POST /backend-api/sentinel/chat-requirements
{"conversation_id": null, "system_hints": [], "supports_buffering": true}
```

The response dictates which challenge (if any) must be solved:

```json
{
  "token": "<per-request-token>",
  "arkose": {
    "required": true,
    "dx": null,
    "client": {
      "blob": null
    }
  },
  "turnstile": {
    "required": false
  },
  "proofofwork": {
    "required": true,
    "seed": "<hex-seed>",
    "difficulty": "<hex-difficulty>"
  }
}
```

The `proofofwork` challenge (hashcash-style computation) is enforced even for free-tier users on some models. The CLI must implement PoW solving and Arkose token acquisition.

---

## 4. Streaming Response Handling

### Protocol

ChatGPT uses **Server-Sent Events (SSE)** over HTTP/1.1 or HTTP/2. The `POST /backend-api/conversation` response has:

```
Content-Type: text/event-stream
Cache-Control: no-cache
Transfer-Encoding: chunked
```

### SSE Event Format

Each event line begins with `data: ` followed by a JSON object. Events arrive incrementally as the model generates tokens:

```
data: {"message": {"id": "<uuid>", "author": {"role": "assistant"}, "create_time": 1710000000.0, "update_time": null, "content": {"content_type": "text", "parts": ["Hello"]}, "status": "in_progress", "end_turn": null, "weight": 1.0, "metadata": {"finish_details": null, "citations": [], "model_slug": "gpt-4o", "parent_id": "<uuid>", "timestamp_": "absolute"}, "recipient": "all"}, "conversation_id": "<uuid>", "error": null}

data: {"message": {"id": "<uuid>", "author": {"role": "assistant"}, "content": {"content_type": "text", "parts": ["Hello! I can help you with many things..."]}, "status": "in_progress", ...}, "conversation_id": "<uuid>", "error": null}

data: {"message": {"id": "<uuid>", "author": {"role": "assistant"}, "content": {"content_type": "text", "parts": ["Hello! I can help you with many things..."]}, "status": "finished_successfully", "end_turn": true, ...}, "conversation_id": "<uuid>", "error": null}

data: [DONE]
```

### Key Parsing Details

- **Delta extraction**: Each event contains the **full accumulated text** so far in `message.content.parts[0]`, NOT just the delta. The CLI must track the previous length and subtract to display incremental output.
- **Completion signal**: `data: [DONE]` is the termination marker (identical to the official API).
- **Status field**: `"in_progress"` during streaming; `"finished_successfully"` on the last content event before `[DONE]`.
- **`end_turn: true`** marks the final message from the assistant.
- **Error events**: `{"error": "message_not_created_error", ...}` can appear inline if the model fails mid-stream.
- **Tool call events**: When browsing/code interpreter is active, intermediate events with `content_type: "tether_browsing_display"` or `content_type: "code"` appear before the final text.

### CLI Streaming Implementation

```python
import httpx
import json

def stream_conversation(access_token: str, message: str, conversation_id: str = None, parent_message_id: str = None):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
        "Oai-Language": "en-US",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    payload = {
        "action": "next",
        "messages": [{"id": str(uuid4()), "author": {"role": "user"}, "content": {"content_type": "text", "parts": [message]}}],
        "conversation_id": conversation_id,
        "parent_message_id": parent_message_id or str(uuid4()),
        "model": "gpt-4o",
        "history_and_training_disabled": False,
    }

    last_text = ""
    with httpx.stream("POST", "https://chatgpt.com/backend-api/conversation", headers=headers, json=payload) as resp:
        for line in resp.iter_lines():
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            event = json.loads(line[6:])
            msg = event.get("message", {})
            parts = msg.get("content", {}).get("parts", [])
            if parts and isinstance(parts[0], str):
                current_text = parts[0]
                delta = current_text[len(last_text):]
                if delta:
                    print(delta, end="", flush=True)
                last_text = current_text
    print()  # newline after completion
```

### Challenges for CLI

| Challenge | Mitigation |
|-----------|-----------|
| Full-text-per-event (not delta) | Track `last_text` length and slice new content |
| SSE over HTTPS with Cloudflare | Use `httpx` with HTTP/2 support; set realistic headers |
| Session token expiry (~1 hour) | Re-fetch `/api/auth/session` before each request using the cookie jar |
| Arkose FunCaptcha requirement | Pre-solve via browser automation (Playwright) or third-party solver service |
| Proof-of-Work challenge | Implement hashcash SHA-256 solver in the CLI |

---

## 5. Suitability Assessment and CLI Design

### Is ChatGPT Suitable for CLI Generation?

**Verdict: Moderate suitability, with significant operational friction.**

| Factor | Assessment |
|--------|-----------|
| **API surface** | Moderately well-structured `backend-api` REST+SSE API; documented by community reverse engineering |
| **Auth complexity** | HIGH — NextAuth session cookie + short-lived JWT + Arkose FunCaptcha + Proof-of-Work = multi-layer auth pipeline |
| **Stability** | MEDIUM — OpenAI changes the web API without notice; `text-davinci-002-render-sha` model slug changed multiple times; sentinel requirements evolve |
| **Terms of service** | Prohibited — OpenAI's ToS explicitly forbids unauthorized API access; risk of account termination |
| **Official alternative** | `api.openai.com` provides a clean, stable, documented API with API keys — the web scraping approach adds cost with no benefit for most use cases |
| **Streaming support** | YES — SSE works well in CLI contexts with progressive terminal output |
| **Offline/local** | NO — requires active OpenAI session |

**Recommendation**: Use the official `api.openai.com` for a production CLI. The `backend-api` scraping approach is viable only for accessing web-exclusive features not in the official API (memory, custom GPTs with system prompts, canvas mode, browsing tool). For pure chat, the official API is superior.

### Predicted CLI Command Surface

```bash
# Authentication
chatgpt auth login                    # Open browser for OAuth, save session cookie
chatgpt auth logout                   # Clear stored credentials
chatgpt auth status                   # Show current user, tier, token expiry

# Conversation management
chatgpt chat "What is recursion?"     # One-shot message, print streamed response
chatgpt chat --model gpt-4o "..."     # Specify model
chatgpt chat --no-stream "..."        # Wait for full response before printing
chatgpt chat --continue <convo-id>    # Continue an existing conversation
chatgpt chat --file ./doc.pdf "..."   # Upload file, ask question about it

# Conversation history
chatgpt list                          # List recent conversations (id, title, timestamp)
chatgpt show <convo-id>               # Print full conversation transcript
chatgpt delete <convo-id>             # Delete conversation
chatgpt clear                         # Archive/delete all conversations

# Model info
chatgpt models                        # List available models and access tier

# GPTs (custom assistants)
chatgpt gpts list                     # List available GPTs
chatgpt gpts chat <gpt-id> "..."      # Chat with a specific GPT

# Memory
chatgpt memory list                   # List stored memories
chatgpt memory delete <memory-id>     # Delete a memory

# Sharing
chatgpt share <convo-id>              # Create public share link
```

### Example Session Flow

```
$ chatgpt auth login
Opening browser for authentication...
Logged in as user@example.com (ChatGPT Plus)

$ chatgpt chat "Explain monads in Haskell in 3 sentences"
Solving proof-of-work challenge...
Streaming response:
> A monad in Haskell is a type class that provides two operations:
> `return` (wrapping a value) and `>>=` (bind, for chaining computations).
> It abstracts sequential computation patterns...
[conversation: a1b2c3d4-..., model: gpt-4o]
```

---

## 6. Structured Reconnaissance Report

### Predictions (Before Traffic Capture)

| Prediction | Confidence | Basis |
|-----------|-----------|-------|
| Next.js App Router frontend | High | Standard for OpenAI web properties; `_next/static/` paths confirmed in source |
| Auth0 as identity provider | High | `auth.openai.com` Auth0 tenant domain; redirect pattern on login |
| `/backend-api/conversation` as primary SSE endpoint | High | Confirmed by multiple community reverse-engineering projects (2022–2025) |
| Cloudflare Enterprise WAF in front of all endpoints | High | `cf-ray` header present; robots.txt blocking AI bots (Cloudflare Bot Management feature) |
| Arkose FunCaptcha for GPT-4 class requests | High | Documented extensively; sentinel endpoint confirmed in community analysis |
| Proof-of-Work challenge on all requests | Medium-High | Introduced mid-2023; varies by model and rate pressure |
| SSE with full-text-per-event (not delta) | High | Confirmed in multiple browser-client implementations |
| `__Secure-next-auth.session-token` cookie | High | Standard NextAuth.js cookie name pattern |
| `Oai-Device-Id` header required | Medium | Seen in browser traffic captures; UUID per device |
| Conversation threading via parent_message_id UUIDs | High | Confirmed in node-chatgpt-api and revChatGPT implementations |

### Recommended Capture Strategy

#### Phase 1: Static Analysis (No Login)

1. Fetch `https://chatgpt.com` — extract all `<script src>` URLs from `/_next/static/chunks/`
2. Download 3–5 large chunk files; search for: `backend-api`, `/conversation`, `sentinel`, `arkose`, `model_slug`
3. Fetch `https://chatgpt.com/robots.txt` — map blocked vs. allowed paths
4. Fetch `https://chatgpt.com/api/auth/session` (unauthenticated) — observe response schema
5. Fetch `https://chatgpt.com/backend-api/models` (unauthenticated) — likely 401, but reveals exact auth error format

#### Phase 2: Authenticated Traffic Capture

1. Launch Chrome: `chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\chatgpt-debug-profile`
2. Log in at `https://chatgpt.com/auth/login`
3. Attach CDP network listener (filter `chatgpt.com`)
4. Perform while capturing:
   - Send a message with gpt-4o-mini (free tier model)
   - Send a message with gpt-4o (may trigger Arkose)
   - Create a new conversation vs. continue an existing one
   - List conversations (sidebar scroll)
   - Upload an image, ask about it
   - Use a public GPT from the store
   - Check `/api/auth/session` to observe token refresh pattern

#### Phase 3: Auth Pipeline Analysis

1. Record the full cookie jar after login: identify `__Secure-next-auth.session-token`, `__Host-next-auth.csrf-token`, `cf_clearance`
2. Call `/api/auth/session` — note the `accessToken` JWT and its expiry
3. Watch for automatic token refresh calls in the network log
4. Record the sentinel challenge flow: `POST /sentinel/chat-requirements` → response → Arkose/PoW solve → `POST /conversation` with `arkose_token` in payload

#### Phase 4: CLI Implementation Plan

```
chatgpt/
├── core/
│   ├── auth.py           # NextAuth session cookie management, token refresh
│   ├── client.py         # httpx client with Cloudflare-friendly headers
│   ├── sentinel.py       # Proof-of-work solver, Arkose token acquisition
│   └── models.py         # Pydantic models for API request/response
├── commands/
│   ├── chat.py           # Streaming conversation command
│   ├── conversations.py  # List, show, delete conversations
│   ├── models.py         # List available models
│   ├── gpts.py           # Custom GPT management
│   └── auth_cmd.py       # Login/logout/status commands
└── utils/
    ├── stream.py         # SSE parser, delta extraction, terminal output
    └── config.py         # Credentials storage (~/.chatgpt/config.json)
```

### Key Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| OpenAI ToS violation | Account ban | Use a dedicated account; accept risk |
| Arkose token requirement | Blocks automated use | Playwright headless solve; or third-party solver (2Captcha) |
| Proof-of-Work solver performance | Adds latency (~100–500ms) | Implement SHA-256 hashcash in Rust/C extension for speed |
| Session cookie theft protection | `HttpOnly` prevents JS access | Must use CDP network interception, not `document.cookie` |
| Backend API schema changes | Broken CLI after updates | Version-lock; add integration tests; monitor GitHub issues |
| Cloudflare JA3 fingerprinting | Requests blocked at TLS layer | Use `curl_cffi` (Chromium TLS fingerprint) instead of standard `httpx` |
| Rate limiting (free tier) | 10 msg/3h on GPT-4o | Expose quota status command; support model fallback |

---

## References

- [waylaidwanderer/node-chatgpt-api](https://github.com/waylaidwanderer/node-chatgpt-api) — Most complete reverse-engineered browser client (archived 2023, still accurate for protocol)
- [acheong08/ChatGPT](https://github.com/acheong08/ChatGPT) — Original Python V1 implementation (archived Aug 2023)
- [acheong08/ChatGPT V1.py](https://raw.githubusercontent.com/acheong08/ChatGPT/main/src/revChatGPT/V1.py) — SSE parsing and Arkose token flow
- [OpenAI robots.txt](https://chatgpt.com/robots.txt) — Crawler policy confirming Cloudflare Bot Management
- [curl_cffi](https://github.com/yifeikong/curl_cffi) — TLS fingerprint spoofing library (recommended transport)
- [NextAuth.js Session Docs](https://next-auth.js.org/configuration/options#session) — Session token architecture
- [Auth0 PKCE Flow](https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow-with-proof-key-for-code-exchange-pkce) — Login flow used by chatgpt.com
- [Arkose Labs FunCaptcha](https://arkoselabs.com/) — CAPTCHA provider requiring browser automation to solve
