# Google batchexecute RPC Protocol

## Contents
- When You'll See This
- URL Format
- Request Headers
- Request Body Encoding
- Response Decoding
- Token Extraction
- RPC Method Discovery
- Recommended Code Organization
- Auth Refresh Pattern
- Cookie Priority for Google Apps (Critical)

Google's internal RPC protocol used by NotebookLM, Google Keep, Google Contacts,
Gemini/Bard, and other Google web apps. Unlike REST APIs, all operations go through
a single endpoint with method IDs in query parameters.

## When You'll See This

Detection signals during Phase 1 traffic capture:
- URL contains `/_/<ServiceName>/data/batchexecute`
- POST method with `Content-Type: application/x-www-form-urlencoded`
- Request body contains `f.req=` with triple-nested JSON arrays
- URL has `rpcids=<method_id>` query parameter
- Response starts with `)]}'\n` anti-XSSI prefix

## URL Format

```
https://<app>.google.com/_/<ServiceName>/data/batchexecute?rpcids=<ID>&source-path=<PATH>&f.sid=<SESSION_ID>&bl=<BUILD_LABEL>&hl=en&_reqid=<COUNTER>&rt=c
```

| Parameter | Source | Description |
|-----------|--------|-------------|
| `rpcids` | Traffic capture | The RPC method ID (e.g., `wXbhsf` for list notebooks) |
| `source-path` | Current page | URL path context (e.g., `/` or `/notebook/<id>`) |
| `f.sid` | Page HTML (`FdrFJe`) | Session ID — extract from `WIZ_global_data` |
| `bl` | Page HTML | Build label — changes per deployment, extract dynamically |
| `hl` | Static | Language code (e.g., `en`) |
| `_reqid` | Counter | Incrementing request ID (start at 100000) |
| `rt` | Static | Response type: `c` for chunked |

**Never hardcode `f.sid` or `bl`** — they change between sessions and deployments.

## Request Headers

```
Content-Type: application/x-www-form-urlencoded;charset=UTF-8
x-same-domain: 1
Cookie: SID=...; HSID=...; SSID=...; (all Google auth cookies)
Origin: https://<app>.google.com
Referer: https://<app>.google.com/
```

The `x-same-domain: 1` header is **critical** — without it, Google rejects the request.

## Request Body Encoding

The body is URL-encoded form data with two fields:

```
f.req=<URL_ENCODED_JSON>&at=<CSRF_TOKEN>
```

The `f.req` value is a triple-nested JSON array:
```python
# Python encoding
inner = [rpc_id, json.dumps(params), None, "generic"]
freq = json.dumps([[inner]])
body = urllib.parse.urlencode({"f.req": freq, "at": csrf_token})
```

Example for listing notebooks (rpc_id = "wXbhsf", params = [None, 1, None, [2]]):
```
f.req=[[[%22wXbhsf%22%2C%22[null%2C1%2Cnull%2C[2]]%22%2Cnull%2C%22generic%22]]]&at=AIXQIk...
```

## Response Decoding

Three-step pipeline:

### Step 1: Strip anti-XSSI prefix
```python
if text.startswith(")]}'"):
    text = text[4:].lstrip("\n")
```

### Step 2: Parse length-prefixed chunks
The response contains alternating byte-count lines and JSON chunks:
```
96132
[["wrb.fr","wXbhsf","[[[\"notebook_id\",...]]]\n",null,...]]
42
[["di",95]]
```

```python
def parse_chunks(text):
    chunks = []
    pos = 0
    while pos < len(text):
        # Skip whitespace
        while pos < len(text) and text[pos] in " \t\r\n":
            pos += 1
        if pos >= len(text):
            break
        # Read byte count
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
```

### Step 3: Extract RPC result
Each chunk is a JSON array. Find the entry matching your RPC ID:
```python
for chunk in chunks:
    outer = json.loads(chunk)
    for entry in outer:
        if entry[0] == "wrb.fr" and entry[1] == rpc_id:
            # entry[2] is a JSON STRING that needs another json.loads()
            return json.loads(entry[2])
```

Error responses use `"er"` instead of `"wrb.fr"`.

## Token Extraction

Two tokens must be extracted from the NotebookLM homepage HTML:

```python
import re

def extract_tokens(html):
    """Extract CSRF and session ID from page HTML."""
    csrf = None
    session_id = None

    # CSRF token (SNlM0e) — used as 'at' body parameter
    m = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', html)
    if m:
        csrf = m.group(1)

    # Session ID (FdrFJe) — used as 'f.sid' URL parameter
    m = re.search(r'"FdrFJe"\s*:\s*"([^"]+)"', html)
    if m:
        session_id = m.group(1)

    return csrf, session_id
```

**How to get the HTML:** HTTP GET to the app homepage with session cookies.
Some Google apps redirect raw HTTP clients — if that happens, extract via CDP
(evaluate JavaScript in the connected Chrome session via autoConnect or debug profile to read `window.WIZ_global_data`).

## RPC Method Discovery

During Phase 1 traffic capture, map each user action to its `rpcids` value:

| User Action | rpcids | CLI Command |
|-------------|--------|-------------|
| Load notebook list | `wXbhsf` | `notebooks list` |
| Create notebook | `CCqFvf` | `notebooks create` |
| Get notebook details | `rLM1Ne` | `notebooks get` |
| Add source | `izAoDd` | `sources add` |
| Send chat query | `GenerateFreeFormStreamed` | `chat ask` |
| List artifacts | `gArtLc` | `artifacts list` |

Store as an enum:
```python
# rpc/types.py
class RPCMethod:
    LIST_NOTEBOOKS = "wXbhsf"
    CREATE_NOTEBOOK = "CCqFvf"
    GET_NOTEBOOK = "rLM1Ne"
    ADD_SOURCE = "izAoDd"
    LIST_ARTIFACTS = "gArtLc"
```

## Recommended Code Organization

For batchexecute apps, add an `rpc/` subpackage under `core/`:

```
core/
├── client.py          # High-level API (delegates to rpc/)
├── auth.py            # Cookie + token management
├── rpc/
│   ├── __init__.py    # Public API: encode_request, decode_response
│   ├── types.py       # RPCMethod enum, URL constants
│   ├── encoder.py     # encode_rpc_request(), build_request_body()
│   └── decoder.py     # strip_prefix(), parse_chunks(), extract_result()
```

## Auth Refresh Pattern

On 401/403 response:
1. Re-fetch the app homepage with current cookies
2. Re-extract CSRF + session ID tokens
3. Update the client's token cache
4. Retry the failed request once

```python
async def call_rpc(self, method, params):
    try:
        return await self._do_rpc(method, params)
    except AuthError:
        self.csrf, self.session_id = await fetch_tokens(self.cookies)
        return await self._do_rpc(method, params)
```

## Cookie Priority for Google Apps (Critical)

Google's auth cookies (`SID`, `__Secure-1PSID`, `__Secure-3PSID`, `HSID`, `SAPISID`,
etc.) may exist on multiple domains simultaneously when captured by playwright
`state-save`. For an Israeli user, the state file will contain:

```
SID: .google.com         → "g.a0007whSv1rz..."  ← CORRECT for batchexecute
SID: .youtube.com        → "g.a0007whSvXyz..."
SID: .google.co.il       → "g.a0007whSvAbc..."  ← WRONG for batchexecute
__Secure-1PSID: .google.com    → "g.a0007whSv1rz..."  ← CORRECT
__Secure-1PSID: .google.co.il  → "g.a0007whSvDef..."  ← WRONG
```

When you flatten `{c["name"]: c["value"] for c in cookies}`, the LAST value wins.
If `.google.co.il` appears after `.google.com` in the list, the regional cookie
overwrites the base domain cookie. The batchexecute endpoint at
`<app>.google.com/_/<Service>/data/batchexecute` only trusts `.google.com` cookies.
Sending the `.google.co.il` value causes a redirect to `accounts.google.com`.

**Always use domain-priority extraction:**
```python
# Prioritize .google.com over regional domains
for c in raw_cookies:
    domain = c.get("domain", "")
    name = c.get("name", "")
    if name not in result or domain == ".google.com":
        result[name] = c.get("value", "")
```

This affects all Google batchexecute apps (NotebookLM, Google Keep, Gemini/Bard,
Google Contacts, etc.) for users in any of the 60+ regional Google domains.
See `auth-strategies.md` "Cookie domain priority" for the complete pattern.
