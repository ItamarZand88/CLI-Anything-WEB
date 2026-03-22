# Traffic Patterns Reference

## Contents
- Documented Public API
- REST APIs
- GraphQL APIs
- gRPC-Web / Protobuf
- Google batchexecute RPC
- Batch / Multiplex APIs
- WebSocket / Real-time
- Async Content Generation
- CAPTCHA / Bot Detection
- Plain HTML (No Framework)
- Server-Sent Events (SSE) / Streaming APIs
- JSON-RPC APIs
- tRPC APIs
- Firebase Realtime Database
- SSR / Server-Rendered Sites

## Documented Public API

Sites with official, documented REST/JSON APIs that don't require browser traffic capture.

### Detection signals:
- API docs page exists (developer.example.com, `/api/docs`, Swagger/OpenAPI)
- `/api/` prefix with versioning (`/api/v1/`, `/api/articles`)
- JSON responses from direct HTTP requests (no browser needed)
- Rate limit headers present (`X-RateLimit-Remaining`)
- Examples: Hacker News Firebase API, Dev.to API, Reddit API, Wikipedia API, GitHub API

### CLI strategy:
- **Skip browser capture** — probe endpoints directly with httpx/curl
- Construct `raw-traffic.json` from API probe results
- No playwright-cli needed (unless auth requires browser login)
- Use API docs to discover endpoints instead of reverse-engineering traffic

### CLI mapping:
```
GET /api/articles         → articles list [--tag T] [--page N]
GET /api/articles/:id     → articles get <id>
GET /api/articles/search  → articles search <query>
GET /api/tags             → tags list
GET /api/users/:username  → users get <username>
```

### Auth patterns:
- **No auth** — fully public read access (HN, Wikipedia)
- **API key** — optional `api-key` or `Authorization` header for writes
- **OAuth** — for user-specific operations

---

## REST APIs

Most common pattern. Endpoints follow resource-based URLs.

### Detection signals:
- URLs like `/api/v1/resources/`, `/api/v2/resources/:id`
- Standard HTTP methods: GET (list/get), POST (create), PUT/PATCH (update), DELETE
- JSON request/response bodies
- Pagination via `?page=`, `?offset=`, `?cursor=`

### CLI mapping:
```
GET    /api/v1/boards          → boards list [--page N]
GET    /api/v1/boards/:id      → boards get --id <id>
POST   /api/v1/boards          → boards create --name <name>
PUT    /api/v1/boards/:id      → boards update --id <id> --name <name>
DELETE /api/v1/boards/:id      → boards delete --id <id>
```

## GraphQL APIs

Single endpoint, operation type in body.

### Detection signals:
- Single URL: `/graphql` or `/api/graphql`
- POST method always
- Body contains `query` or `mutation` field
- `operationName` field identifies the action

### CLI mapping:
- Extract operation names from captured queries
- Map each operation to a CLI command
- Abstract GraphQL complexity behind simple flags
- Store query templates in `queries/` directory

```
mutation CreateBoard → boards create --name <name>
query GetBoards     → boards list
query GetBoard      → boards get --id <id>
```

## gRPC-Web / Protobuf

Binary protocol over HTTP.

### Detection signals:
- Content-Type: `application/grpc-web` or `application/x-protobuf`
- Binary request/response bodies
- URL paths match service/method pattern: `/package.Service/Method`

### CLI mapping:
- Requires proto file reconstruction or manual mapping
- Each gRPC method → one CLI command
- Flag cli-anything-web that manual decoding may be needed

## Google batchexecute RPC

Google's internal RPC protocol. Single endpoint, method ID in query params.

### Detection signals:
- URL contains `/_/<ServiceName>/data/batchexecute`
- POST with `Content-Type: application/x-www-form-urlencoded`
- Body contains `f.req=` with URL-encoded nested JSON arrays
- URL has `rpcids=<method_id>` query parameter
- Response starts with `)]}'\n` anti-XSSI prefix
- Used by: NotebookLM, Google Keep, Google Contacts, Gemini/Bard

### CLI mapping:
- Each `rpcids` value maps to one CLI command
- Discover method IDs from captured traffic
- Requires dedicated `rpc/` codec layer (encoder + decoder)
- Example: `rpcids=wXbhsf` → `notebooks list`

### Key differences from REST:
- Single endpoint (not resource-based URLs)
- Method ID in query params (not URL path or HTTP method)
- Triple-nested array encoding (not JSON body)
- Requires page-embedded tokens (CSRF + session ID)
- Response needs multi-step decoding (anti-XSSI + chunks + double-JSON)
- Auth requires cookies + `x-same-domain: 1` header

### Reference:
See `references/google-batchexecute.md` for the full protocol specification
including encoding, decoding, token extraction, and code organization patterns.

## Batch / Multiplex APIs

Multiple operations in single request.

### Detection signals:
- POST to `/batch` or `/api/batch`
- Request body is an array of operations
- Google APIs style: `multipart/mixed` boundary

### CLI mapping:
- Unbundle individual operations into separate commands
- Optionally support `--batch` flag for efficiency

## Async Content Generation

Apps that generate content asynchronously (AI music, images, documents, audio).

### Detection signals:
- POST to create/generate endpoint returns a job/task ID, not the content
- Subsequent GET/poll requests check status (`pending` → `processing` → `complete`)
- Final response contains a download URL (often on a CDN domain)
- Examples: Suno (music), Midjourney (images), NotebookLM (audio overviews), Canva (designs)

### CLI mapping:
- Single command handles full lifecycle: trigger → poll → download
- `<resource> generate --prompt "..." --output file.mp3`
- Show progress during polling (spinner or percentage)
- Download binary content with correct extension
- `--output` flag for save path, default to descriptive filename
- `--wait/--no-wait` flag for async vs sync behavior
- Include CDN domains in auth cookie filter if download requires auth

### Traffic capture notes:
- Capture BOTH the create request AND the polling requests
- Note the status field name and completion value
- Capture the download URL pattern (may be signed/temporary)
- Check if download requires same auth cookies or is publicly accessible

## CAPTCHA / Bot Detection

Challenges that interrupt normal API flow.

### Detection signals:
- HTTP 403 with HTML challenge page (not JSON)
- Response body contains: "captcha", "challenge", "verify", "robot", "human"
- Redirect to challenge URL (e.g., `/challenge`, `/verify`)
- Cloudflare challenge page (`cf-chl-bypass`, `__cf_bm` cookie)
- reCAPTCHA or hCaptcha scripts in response

### CLI handling:
- Detect CAPTCHA response by checking status code + body content
- Do NOT retry automatically — CAPTCHAs punish repeated attempts
- Pause and prompt user:
  ```
  CAPTCHA detected. Please solve it:
  1. Open: <url>
  2. Complete the challenge
  3. Press ENTER when done
  ```
- After user confirms, retry the original request once
- If CAPTCHA persists, suggest reducing request frequency

## Plain HTML (No Framework)

Traditional server-rendered sites with no JavaScript framework.

### Detection signals:
- No `__NEXT_DATA__`, `__NUXT__`, `__remixContext`, or SPA root elements
- No framework-specific script tags (`_next/`, `_nuxt/`, etc.)
- Data is in HTML `<table>`, `<div>`, `<article>` elements with CSS classes
- Example sites: Hacker News, Craigslist, older forums, government sites

### CLI strategy:
- **First check for a public API** — many plain HTML sites have separate JSON APIs
  (HN has Firebase API, Reddit has `/api/`, Wikipedia has MediaWiki API). If found,
  use the API and skip HTML scraping entirely.
- If no API exists, use httpx + BeautifulSoup4 to parse HTML
- Identify CSS classes/selectors for data extraction from the page source
- Store example HTML in `tests/fixtures/` for unit testing parsers

### CLI mapping:
```python
# client.py for plain HTML scraping
resp = httpx.get(f"{BASE_URL}/page")
soup = BeautifulSoup(resp.text, "html.parser")
items = []
for row in soup.select("tr.athing"):  # CSS selector from page
    items.append(Story(
        title=row.select_one(".titleline a").text,
        url=row.select_one(".titleline a")["href"],
    ))
```

### Key considerations:
- HTML structure changes break parsers — include version detection
- Pagination is usually `?p=N` or `?page=N` query params
- No auth needed for most plain HTML sites (public content)

---

## WebSocket / Real-time APIs

Live bidirectional communication over persistent connections.

### Detection signals:
- URLs starting with `wss://` or `ws://`
- `Upgrade: websocket` header in request
- Persistent connection (not request/response)
- Examples: Slack, Discord, chat apps, live dashboards, collaborative editors

### CLI mapping:
- `<resource> stream` or `<resource> watch` — subscribe to real-time updates
- `<resource> send` — send a message through the WebSocket
- Consider `--poll` fallback for environments without WebSocket support
- WebSocket CLIs typically need a background listener + command sender

### Key considerations:
- WebSocket connections require maintaining state between commands
- Authentication usually happens via initial HTTP handshake (cookies/tokens)
- Messages may use JSON, binary (protobuf), or custom formats
- The CLI must handle reconnection gracefully

---

## Server-Sent Events (SSE) / Streaming APIs

One-directional streaming from server to client over HTTP.

### Detection signals:
- `Accept: text/event-stream` in request headers
- `Content-Type: text/event-stream` in response headers
- Response body contains `data:` prefixed lines
- Long-lived HTTP connections (high response times)
- Examples: ChatGPT streaming, AI completion APIs, live feeds, notification streams

### CLI mapping:
- `<resource> stream` — subscribe to event stream, print events as they arrive
- For AI completion: `<resource> generate --stream` — show tokens as they arrive
- `--no-stream` flag to wait for complete response instead
- Parse `data:` lines, handle `event:` types, respect `retry:` directives

### Key considerations:
- SSE is HTTP-based — works with standard auth (Bearer, cookies)
- Responses can be very large (streaming for minutes)
- The CLI must handle `[DONE]` or empty-data termination signals
- JSON parsing per `data:` line (each line is a complete JSON object)

---

## JSON-RPC APIs

Remote procedure calls over HTTP with JSON payloads.

### Detection signals:
- Request body contains `"jsonrpc": "2.0"` and `"method": "..."` fields
- Single POST endpoint (no resource-style URLs)
- Batch requests: array of RPC calls in one request
- `"id"` field for request/response correlation
- Examples: Ethereum/Web3 APIs, some microservices, LSP (Language Server Protocol)

### CLI mapping:
- Each RPC method → one CLI command
- `<method-group> <method-name> [params]`
- Example: `eth call --to 0x... --data 0x...` for `eth_call` RPC method
- Support `--raw` flag for direct JSON-RPC request passthrough

### Key considerations:
- Single endpoint, method name in body (similar to batchexecute but standard)
- Errors have `error.code` and `error.message` in response
- Batch support: multiple calls in one request for efficiency
- Method names are often namespaced: `eth_getBalance`, `net_version`

---

## tRPC APIs

Type-safe RPC framework for Next.js/TypeScript applications.

### Detection signals:
- URLs containing `/api/trpc/` or `/trpc/`
- Procedure names in URL path: `/api/trpc/post.list`, `/api/trpc/user.get`
- Query parameters: `input=` with URL-encoded JSON
- Batch requests: `/api/trpc/post.list,user.get?batch=1`
- Examples: T3 Stack apps, Cal.com, many Next.js applications

### CLI mapping:
- Each tRPC procedure → one CLI command
- Group by router: `post.list` → `posts list`, `user.get` → `users get`
- `input` parameter maps to CLI flags/arguments
- Batch endpoints can be used for efficient multi-resource fetches

### Key considerations:
- tRPC is TypeScript-native — response types are very predictable
- Procedures are either `query` (GET) or `mutation` (POST)
- Input validation is strict — match the expected schema exactly
- The URL structure reveals the full API surface

---

## Firebase Realtime Database

Google's real-time NoSQL database with REST API.

### Detection signals:
- URLs containing `firebaseio.com`
- REST endpoint pattern: `https://<project>.firebaseio.com/<path>.json`
- Authentication via `?auth=<token>` query parameter or Authorization header
- Real-time via SSE: `Accept: text/event-stream` for live updates
- Examples: Hacker News API, many mobile app backends

### CLI mapping:
- `<resource> list` → `GET /<resource>.json`
- `<resource> get <id>` → `GET /<resource>/<id>.json`
- `<resource> create` → `POST /<resource>.json`
- `<resource> update <id>` → `PATCH /<resource>/<id>.json`
- `<resource> delete <id>` → `DELETE /<resource>/<id>.json`
- `<resource> watch` → `GET /<resource>.json` with `Accept: text/event-stream`

### Key considerations:
- Data is a JSON tree — paths map directly to URLs
- Supports filtering: `orderBy`, `equalTo`, `limitToFirst`, `limitToLast`
- Real-time updates via SSE (add `Accept: text/event-stream` header)
- Authentication varies: none (public), Firebase Auth tokens, or legacy secrets

---

## SSR / Server-Rendered Sites

Sites that render data server-side (Next.js, Nuxt, Remix, SvelteKit, Gatsby).

### Detection signals:
- HTML contains full page data on initial load (no XHR/fetch on first render)
- Presence of `__NEXT_DATA__`, `__NUXT__`, `__remixContext`, or similar globals
- SPA root element (`#__next`, `#__nuxt`) with pre-rendered content
- `/_next/data/` or `/__data.json` endpoints in network trace

### CLI mapping:
- Initial data from SSR blobs → use for data models and read endpoints
- Client-side navigation reveals hidden API endpoints (Force SPA Navigation trick)
- Mutation endpoints (create/update/delete) usually go through standard API calls
- Read endpoints may use SSR data routes (`/_next/data/`) or client-side API

### Reference:
See `references/ssr-patterns.md` for framework-specific extraction patterns
and the Force SPA Navigation trick.
