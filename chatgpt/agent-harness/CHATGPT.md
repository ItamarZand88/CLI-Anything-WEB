# CHATGPT.md — Software-Specific SOP

## Overview
CLI for ChatGPT web interface. Ask questions, generate/download images, list conversations, browse models.

## Architecture (Hybrid)
- **Read-only endpoints**: `curl_cffi` with Chrome TLS impersonation (instant, no browser)
- **Chat + image generation**: Camoufox headless browser (stealth Firefox, bypasses Cloudflare)
- **Base URL**: `https://chatgpt.com/backend-api`
- **Protection**: Cloudflare managed challenge — blocked headless Chromium/Playwright, bypassed by Camoufox

## Auth Flow
1. User captures browser session via `playwright-cli` (Phase 1 capture)
2. Cookies saved to `chatgpt/traffic-capture/fresh-auth.json`
3. Access token obtained from `GET /api/auth/session` using session cookies
4. Read-only API calls use Bearer JWT + cookies via `curl_cffi`
5. Chat/image calls inject cookies into Camoufox browser context

### Token Storage
- `~/.config/cli-web-chatgpt/auth.json` — cookies + access_token for curl_cffi endpoints
- `chatgpt/traffic-capture/fresh-auth.json` — full browser state for Camoufox
- Env var: `CLI_WEB_CHATGPT_AUTH_JSON`

## API Endpoints (curl_cffi — read-only)

### Conversations
```
GET /conversations?offset=0&limit=28&order=updated&is_archived=false&is_starred=false
Response: {"items": [{"id": "uuid", "title": "...", "create_time": "...", "update_time": "..."}]}

GET /conversation/{conversation_id}
Response: Full conversation with message mapping
```

### Models
```
GET /models?iim=false&is_gizmo=false
Response: {"models": [{"slug": "gpt-5-3", "title": "GPT-5.3", ...}]}
```

### User Info
```
GET /me
Response: {"id": "user-...", "email": "...", "name": "...", ...}
```

### Image Download
```
GET /files/download/{file_id}?conversation_id={id}&inline=false
Response: {"status": "success", "download_url": "https://...estuary/content?...", "file_size_bytes": N}
```

### Recent Generated Images
```
GET /my/recent/image_gen?limit=25
Response: {"items": [{"id": "s_...", "title": "...", "url": "...", "width": 1024, "height": 1024}]}
```

### Image Styles
```
GET /images/styles
Response: {"styles": [{"id": "...", "title": "..."}]}
```

## Browser-Based Operations (Camoufox)

### Chat Ask
- Opens `chatgpt.com` in headless Camoufox
- Optionally selects model via `[data-testid="model-switcher-{slug}"]` dropdown
- Types message in textbox, clicks send
- Waits for "Copy response" button (completion indicator)
- Extracts text from `.markdown` container inside `[data-message-author-role="assistant"]`
- For Instruments/canvas widgets: extracts from `<input>` value

### Image Generation
- Same as chat but prefixes prompt with "Generate an image: "
- Waits for "Download this image" button (completion indicator)
- Extracts `file_id` from `img[alt*="Generated image"]` src attribute
- Downloads via `GET /files/download/{file_id}` (curl_cffi)

### Model Selection
- Clicks "Model selector" button
- Selects `[data-testid="model-switcher-{slug}"]` menu item
- Available slugs discoverable via `GET /models` API

## CLI Command Structure

```
cli-web-chatgpt [--json]
  chat ask <question>              Ask a question, get response
    --model <slug>                 Model (e.g. gpt-5-4-thinking)
    --conversation <id>            Continue existing conversation
  chat image <prompt>              Generate an image
    --style <id>                   Apply a style to prompt
    --output/-o <path>             Save image to file
    --conversation <id>            Continue existing conversation
  conversations list               List recent conversations
    --limit/-n <N>                 Number to show (default: 20)
    --archived                     Show archived
    --starred                      Show starred only
  conversations get <id>           View conversation details
  images list                      List recently generated images
    --limit/-n <N>                 Number to show (default: 10)
  images download <file_id>        Download a generated image
    --conversation/-c <id>         (required) Conversation ID
    --output/-o <path>             Save path
  images styles                    List available image styles
  models                           List available models
  me                               Show current user info
  auth login                       Login via browser
  auth status                      Check auth status
  auth logout                      Remove stored credentials
```

## Dependencies
- `curl_cffi` — HTTP client for read-only API (Chrome TLS impersonation)
- `camoufox` — Headless stealth Firefox for chat/image (Cloudflare bypass)
- `click` — CLI framework
- `rich` — Terminal formatting
- `playwright` — (optional) for auth login flow
