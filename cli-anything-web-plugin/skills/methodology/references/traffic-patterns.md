# Traffic Patterns Reference

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

## WebSocket / Real-time

Persistent connections for live data.

### Detection signals:
- `wss://` or `ws://` URLs
- Upgrade headers
- Repeated message patterns

### CLI mapping:
- `<resource> watch` or `<resource> stream` commands
- `--poll` fallback if WebSocket is too complex
- Consider SSE (Server-Sent Events) alternatives

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
