# NOTEBOOKLM.md — Software-Specific SOP

**Target:** https://notebooklm.google.com/
**CLI name:** `cli-web-notebooklm`
**Python namespace:** `cli_web.notebooklm`
**Protocol:** Google batchexecute (single endpoint, RPC by `rpcids` query param)
**Auth:** Google session cookies + WIZ_global_data tokens (SNlM0e CSRF, FdrFJe session ID)

---

## API Endpoint

All operations use a single endpoint:
```
POST https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute
```

URL query params:
- `rpcids` — method identifier (see table below)
- `source-path` — current page context (e.g., `/` or `/notebook/<id>`)
- `f.sid` — session ID from `FdrFJe` in WIZ_global_data
- `bl` — build label from `cfb2h` in WIZ_global_data
- `hl` — language code (`en`)
- `_reqid` — incrementing counter (start 100000, +1 per request)
- `rt` — response type (`c` for chunked)

Request body (URL-encoded form):
```
f.req=[[[rpcid, json.dumps(params), null, "generic"]]]&at=<CSRF_TOKEN>
```

---

## rpcid Map

| rpcid     | Operation               | Params (simplified)                                   | Returns                        |
|-----------|-------------------------|-------------------------------------------------------|--------------------------------|
| `wXbhsf`  | List notebooks          | `[null, 1, null, [2]]`                                | Array of notebook objects      |
| `CCqFvf`  | Create notebook         | `["title"]`                                           | New notebook object            |
| `rLM1Ne`  | Get notebook + sources  | `[notebook_id, null, [2], null, 0]`                   | Notebook + embedded sources    |
| `s0tc2d`  | Rename notebook         | `[null, null, notebook_id, new_title]`                | Updated notebook object        |
| `WWINqb`  | Delete notebook         | `[null, null, notebook_id]`                           | `[]`                           |
| `izAoDd`  | Add URL source          | `[[[null,null,[url],null*5]], nb_id, [2], null, null]`| Source data with ID            |
| `izAoDd`  | Add text source         | `[[[null,[title,text],null*6]], nb_id, [2], null, null]`| Source data with ID          |
| `hizoJc`  | Get source              | `[null, null, source_id, notebook_id]`                | Source object                  |
| `tGMBJ`   | Delete source           | `[null, null, notebook_id, [source_id]]`              | `[]`                           |
| `yyryJe`  | Chat (streaming)        | `[src_ids, query, null, [2,null,[1],[1]], conv_id, null, null, nb_id, 1]` | Streamed answer |
| `yyryJe`  | Generate mind map       | `[src_ids, null*4, ["interactive_mindmap",...], null, [2,null,[1]]]` | Mind map JSON |
| `R7cb6c`  | Create artifact         | `[[2], nb_id, [null,null, type_code, src_ids, ...type_config]]` | `[[artifact_id, title, ...]]` |
| `gArtLc`  | List artifacts          | `[[2], nb_id, filter_str]`                            | Array of artifact objects      |
| `v9rmvd`  | Get interactive HTML    | `[artifact_id]`                                       | HTML with quiz/flashcard data  |
| `ciyUvf`  | Suggested reports       | `[null, null, notebook_id, type_id]`                  | `[[[title, summary, ...]]]`    |
| `sqTeoe`  | List audio types        | `[null, null, notebook_id]`                           | Array of audio types           |
| `hPTbtc`  | Get conversation ID     | `[[], null, notebook_id, 1]`                          | `[[[conversation_id]]]`        |
| `JFMDGd`  | Get share status        | `[null, 1]`                                           | Share/user object              |
| `ZwVcOc`  | Get user settings       | `[null, 1]`                                           | Config object                  |
| `VfAZjd`  | Summarize sources       | `[notebook_id, [url]]`                                | Summary text                   |

**Note:** `izAoDd` is used for ALL source add operations (URL, text, file) — differentiated by param structure.
Chat and mind map both use `yyryJe` — differentiated by the prompt structure.
Sources list is extracted from `rLM1Ne` (GET_NOTEBOOK), not a separate RPC.

---

## Data Models

### Notebook
```json
{
  "id": "43b77b47-6db4-4744-b3ae-c595cc451cf2",
  "title": "My Notebook",
  "emoji": "📓",
  "created_at": 1773851996,
  "updated_at": 1773851719,
  "source_count": 4,
  "is_pinned": false
}
```

### Source
```json
{
  "id": "c84ec171-3655-4287-b670-e8addde0e41a",
  "name": "NotebookLM - Wikipedia",
  "type": "url",
  "url": "https://en.wikipedia.org/wiki/NotebookLM",
  "char_count": 11756,
  "created_at": 1773852295
}
```

### User
```json
{
  "email": "user@gmail.com",
  "display_name": "User Name",
  "avatar_url": "https://lh3.googleusercontent.com/..."
}
```

---

## Auth Scheme

### Cookie-Based Auth
- Google session cookies stored at `~/.config/cli-web-notebooklm/auth.json`
- Relevant cookies: `SID`, `HSID`, `SSID`, `APISID`, `SAPISID`, `__Secure-1PSID`, `__Secure-3PSID`, `__Secure-1PSIDTS`, `__Secure-3PSIDTS`, `NID`
- Filter to `.notebooklm.google.com` and `.google.com` cookies

### Dynamic Tokens
- `SNlM0e` → CSRF token (used as `at` body param) — extract from homepage HTML
- `FdrFJe` → session ID (used as `f.sid` URL param) — extract from homepage HTML
- `cfb2h` → build label (used as `bl` URL param) — extract from homepage HTML
- **Never hardcode** — extract dynamically by GET to homepage with session cookies

### Token Extraction
```python
import re
html = httpx.get("https://notebooklm.google.com/", cookies=cookies, follow_redirects=True).text
csrf = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', html).group(1)
session_id = re.search(r'"FdrFJe"\s*:\s*"([^"]+)"', html).group(1)
build_label = re.search(r'"cfb2h"\s*:\s*"([^"]+)"', html).group(1)
```

### Auth Refresh
On 401/403: re-fetch homepage, re-extract tokens, retry once.

---

## CLI Command Design

### Notebook Commands (`notebooks`)
```
notebooks list                          # List all notebooks
notebooks create --title "My NB"        # Create new notebook
notebooks get --id <notebook_id>        # Get notebook details
notebooks rename --id <id> --title <t>  # Rename notebook
notebooks delete --id <id>              # Delete notebook (--confirm)
```

### Source Commands (`sources`)
```
sources list --notebook <id>            # List all sources in notebook
sources add-url --notebook <id> --url <url>  # Add URL source
sources add-text --notebook <id> --title <t> --text <text>  # Add text
sources get --notebook <id> --id <sid>  # Get source details
sources delete --notebook <id> --id <sid>  # Delete source
```

### Chat Commands (`chat`)
```
chat ask --notebook <id> --query "question"  # Ask a question
```

### Artifact Commands (`artifacts`)
```
artifacts generate --notebook <id> --type mindmap   # Generate mind map
artifacts generate --notebook <id> --type notes     # Generate study notes
artifacts list-types --notebook <id>                # List available audio types
```

### Auth Commands (`auth`)
```
auth login                              # Open browser for Google login
auth login --cookies-json <file>        # Import cookies from JSON file
auth status                             # Show current session status
auth refresh                            # Re-extract tokens from homepage
```

### Info Commands
```
whoami                                  # Show current user info
```

---

## REPL Mode

Default when invoked without subcommands:
```
$ cli-web-notebooklm
📓 NotebookLM CLI
Authenticated as user@gmail.com
Type 'help' or press Tab for commands.

notebooklm> notebooks list
notebooklm> chat ask --notebook abc-123 --query "what is the main theme?"
```

---

## Rate Limits and Behavior

- From `ZwVcOc` response: `[null,[1,100,50,500000,1]]` → 100 requests/session limit
- Always add exponential backoff on 429 responses
- Source upload may take a few seconds — add short delay after add-url

---

## Notes

- Source-path in request URL should match current context: `/` for general, `/notebook/<id>` for notebook-specific calls
- The `at` CSRF token expires — re-extract if getting 403 "Invalid request"
- Hebrew UI text in responses is expected (user's locale) — display as-is
