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
