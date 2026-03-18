# NOTEBOOKLM.md — Software-Specific SOP

## App Overview

**NotebookLM** (notebooklm.google.com) is Google's AI-powered research and note-taking
tool. Users create notebooks, add sources (text, PDFs, URLs, YouTube videos, Google Drive
docs), and interact via chat to ask questions grounded in their sources. The app also
generates "studio" artifacts: audio overviews (podcast-style), videos, presentations,
quizzes, and text summaries.

## Protocol: Google batchexecute

NotebookLM uses Google's proprietary **batchexecute** RPC protocol:

- **Endpoint:** `POST https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute`
- **Content-Type:** `application/x-www-form-urlencoded;charset=UTF-8`
- **Required Header:** `x-same-domain: 1`
- **Request Body:** `f.req=<url-encoded-json>&at=<csrf_token>&`
- **Response:** `)]}'` prefix, then length-prefixed JSON chunks

### Dynamic Parameters (extracted from page JavaScript)

| Parameter | WIZ_global_data key | Description |
|-----------|-------------------|-------------|
| `at` | `SNlM0e` | CSRF/anti-forgery token |
| `bl` | `cfb2h` | Build label (changes per deploy) |
| `f.sid` | `FdrFJe` | Session ID |

These are embedded in the page HTML inside `<script>` tags as `WIZ_global_data`.
Extract via regex: `"SNlM0e":"([^"]+)"`, etc.

### Query String Parameters

| Param | Description |
|-------|-------------|
| `rpcids` | Comma-separated RPC method IDs |
| `source-path` | Current page path (e.g., `/` or `/notebook/<id>`) |
| `bl` | Build label |
| `f.sid` | Session ID |
| `hl` | UI language |
| `_reqid` | Incrementing request counter |
| `rt` | Response type (`c` = complete) |

## Authentication

**Method:** Cookie-based Google session authentication.

**Required cookies:** SID, HSID, SSID, OSID, __Secure-OSID, APISID, SAPISID,
__Secure-1PSID, __Secure-3PSID, __Secure-1PAPISID, __Secure-3PAPISID, NID,
SIDCC, __Secure-1PSIDCC, __Secure-3PSIDCC, __Secure-1PSIDTS, __Secure-3PSIDTS

**Token extraction flow:**
1. Load page with cookies → Extract `at`, `bl`, `f.sid` from WIZ_global_data
2. Use cookies + tokens for all subsequent batchexecute calls

## RPC Method Map

### Notebook Operations

| RPC ID | Operation | Request Params | Response |
|--------|-----------|---------------|----------|
| `wXbhsf` | List notebooks | `[null,1,null,[2]]` | Array of notebook objects |
| `ub2Bae` | List shared notebooks | `[[2]]` | Array of notebook objects |
| `rLM1Ne` | Get notebook | `["<id>",null,[2],null,0]` | Single notebook object |
| `ZwVcOc` | Get user quotas | `[null,[1,...,[1]]]` | Quota limits |
| `ozz5Z` | Get plan info | `[[[null,"1",627],...]]` | Subscription details |
| `CCqFvf` | **Create notebook** | `["",null,null,[2],[1,...,[1]]]` | `["",null,"<new_id>",...]` |
| `WWINqb` | **Delete notebook** | `[[notebook_id],[2]]` | `[]` |

### Source Operations

| RPC ID | Operation | Request Params | Response |
|--------|-----------|---------------|----------|
| (via notebook data) | List sources | Sources are embedded in notebook response | |
| `izAoDd` | **Add text source** | `[[[null,[title,text],null,2,...,1]],notebook_id,[2],[1,...,[1]]]` | Source with new ID |

### Chat Operations

| RPC ID | Operation | Request Params | Response |
|--------|-----------|---------------|----------|
| `hPTbtc` | Get thread IDs | `[[],null,"<notebook_id>",20]` | Thread ID array |
| `khqZz` | Get chat history | `[[],null,null,"<thread_id>",20]` | Message array with full text |
| `VfAZjd` | Get summary + suggested Qs | `["<notebook_id>",[2]]` | Summary text + questions |
| `GenerateFreeFormStreamed` | **Ask question** (streaming) | `[[[source_ids]],question,null,[2,null,[1],[1]],thread_id,null,null,notebook_id,1]` | Streaming text chunks |

Note: `GenerateFreeFormStreamed` uses a different URL path, not the standard batchexecute endpoint.

### Artifact/Studio Operations

| RPC ID | Operation | Request Params | Response |
|--------|-----------|---------------|----------|
| `gArtLc` | List artifacts | `[[2,...],<notebook_id>,"NOT...SUGGESTED"]` | Array of artifacts with media URLs |
| `sqTeoe` | Get output templates | `[[2,...],null,1]` | Available output types |
| `cFji9` | Get saved notes | `["<notebook_id>",null,null,[2]]` | Full note content |
| `R7cb6c` | **Create artifact** | `[[2,...],notebook_id,[null,null,type,[source_refs],...]]` | `[["id","title",type,...]]` |

### Sharing Operations

| RPC ID | Operation | Request Params | Response |
|--------|-----------|---------------|----------|
| `JFMDGd` | Get collaborators | `["<notebook_id>",[2]]` | Email, name, avatar, permissions |

## Data Model

### Notebook
```
{
  id: UUID string,
  title: string,
  emoji: string (icon),
  sources: Source[],
  metadata: {
    is_owner: boolean,
    is_shared: boolean,
    is_writable: boolean,
    last_modified: timestamp,
    created: timestamp
  }
}
```

### Source
```
{
  id: UUID string,
  title: string,
  word_count: int,
  created: timestamp,
  type: enum(pasted_text=4, pdf=3, url=5, youtube=9, drive_doc=1, audio=10, pasted_text_v2=8)
}
```

### Artifact
```
{
  id: UUID string,
  title: string,
  type: enum(audio=1, video=3, quiz=4, presentation=8),
  source_refs: UUID[],
  status: int,
  media_urls: {mp4?: string, hls?: string, dash?: string},
  created: timestamp
}
```

### ChatMessage
```
{
  id: UUID string,
  timestamp: [seconds, nanos],
  role: int (2=user/assistant pair),
  text: string (markdown with citations like [1], [2]),
  citations: [{source_id, offset_start, offset_end}]
}
```

## CLI Command Structure

```
cli-web-notebooklm
├── auth
│   ├── login [--from-browser | --cookies-json <file>]
│   ├── status
│   └── logout
├── notebooks
│   ├── list [--shared]
│   ├── get --id <id>
│   ├── create --title <title>
│   └── delete --id <id>
├── sources
│   ├── list --notebook-id <id>
│   ├── add-text --notebook-id <id> --title <title> --text <text>
│   ├── add-url --notebook-id <id> --url <url>
│   └── delete --notebook-id <id> --source-id <id>
├── chat
│   ├── ask --notebook-id <id> --question <text>
│   ├── history --notebook-id <id>
│   └── suggested --notebook-id <id>
├── artifacts
│   ├── list --notebook-id <id>
│   ├── get --id <id> --notebook-id <id>
│   └── create --notebook-id <id> --type <audio|video|quiz|presentation|summary>
└── (REPL mode when invoked without subcommand)
```

Every command supports `--json` for machine-readable output.

## Anti-Bot Considerations

- Must replicate `x-same-domain: 1` header
- CSRF token (`at`) expires — re-fetch from homepage on 401/403
- Build label (`bl`) changes on deploys — extract dynamically
- Session ID (`f.sid`) is per-page-load — extract dynamically
- Rate limiting: respect server backoff, add delays between batch calls
