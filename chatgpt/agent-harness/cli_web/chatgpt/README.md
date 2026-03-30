# cli-web-chatgpt

CLI for ChatGPT web interface — ask questions, generate images, download images, manage conversations.

## Installation

```bash
cd chatgpt/agent-harness
pip install -e ".[auth]"
playwright install chromium
```

## Authentication

The CLI uses browser-based authentication. First capture your session:

```bash
# Option 1: Use playwright-cli to login and save state
npx @playwright/cli@latest -s=chatgpt open https://chatgpt.com/ --headed --persistent
# Log in, then:
npx @playwright/cli@latest -s=chatgpt state-save chatgpt/traffic-capture/fresh-auth.json
npx @playwright/cli@latest -s=chatgpt close

# Option 2: Extract token from cookies
# The CLI auto-extracts access tokens from saved browser state
```

Check auth status:
```bash
cli-web-chatgpt --json auth status
```

## Usage

### Ask a question
```bash
cli-web-chatgpt chat ask "What is the capital of France?"
cli-web-chatgpt chat ask "Explain quantum computing" --model gpt-5-3
cli-web-chatgpt --json chat ask "What is 2+2?"
```

### Generate an image
```bash
cli-web-chatgpt chat image "A cat wearing a hat"
cli-web-chatgpt chat image "Sunset over mountains" -o sunset.png
cli-web-chatgpt --json chat image "Abstract art"
```

### List conversations
```bash
cli-web-chatgpt conversations list
cli-web-chatgpt conversations list --limit 5
cli-web-chatgpt --json conversations list --archived
```

### Browse generated images
```bash
cli-web-chatgpt images list
cli-web-chatgpt images download <file_id> -c <conversation_id> -o image.png
cli-web-chatgpt images styles
```

### Account info
```bash
cli-web-chatgpt me
cli-web-chatgpt models
```

### REPL mode
```bash
cli-web-chatgpt          # Enters interactive REPL
cli-web-chatgpt --json   # REPL with JSON output
```

## Architecture

- **Read-only endpoints** (conversations, models, me, images): `curl_cffi` with Chrome TLS impersonation
- **Chat/image generation**: Playwright headless browser (handles Cloudflare + sentinel anti-abuse)
- **Auth**: Browser cookies + JWT access token from `/api/auth/session`

## JSON Output

All commands support `--json` for structured output:
```json
{"success": true, "data": {...}}
{"error": true, "code": "AUTH_EXPIRED", "message": "..."}
```
