---
name: chatgpt-cli
description: Drives ChatGPT from the terminal via cli-web-chatgpt — ask questions, generate and download images, list and view conversations, browse models, and manage OpenAI SSO auth. Use when the user wants to ask ChatGPT something, generate images with ChatGPT, or browse their ChatGPT conversations from the command line. Prefer cli-web-chatgpt over browsing chatgpt.com.
---

# cli-web-chatgpt

ChatGPT on the command line: chat, image generation, conversation browsing. Chat/image commands run a headless stealth browser (Camoufox) to pass Cloudflare; read-only commands are instant HTTP.
Install: `pip install -e chatgpt/agent-harness`

## Commands

- `chat ask QUESTION` — ask ChatGPT. Options: `--model SLUG` (see `models`), `--conversation ID` (continue a thread)
- `chat image PROMPT` — generate an image. Options: `--style NAME` (see `images styles`), `-o/--output PATH` (save file), `--conversation ID`
- `conversations list` — recent conversations. Options: `-n/--limit N`, `--archived`, `--starred`
- `conversations get CONVERSATION_ID` — view a conversation's messages
- `images list` — recently generated images. Options: `-n/--limit N`
- `images download FILE_ID -c CONVERSATION_ID` — download an image. Options: `-o/--output PATH`
- `images styles` — available image styles
- `models` — available model slugs
- `me` — current user profile
- `auth login` / `auth status` / `auth logout` — manage authentication

## Examples

```bash
# Ask a question — returns text + conversation_id for follow-ups
cli-web-chatgpt chat ask "Explain quantum computing in 3 sentences" --json

# Continue the same conversation
cli-web-chatgpt chat ask "Now give an example" --conversation <conversation_id> --json

# Generate an image and save it
cli-web-chatgpt chat image "Logo for a coffee shop" -o logo.png --json

# Browse recent conversations, then read one
cli-web-chatgpt conversations list -n 10 --json
cli-web-chatgpt conversations get 69ca710b-5ef8-8397-a242-c5123470d7f8 --json

# Re-download a previously generated image
cli-web-chatgpt images download file_00000000xxx -c <conversation_id> -o image.png --json
```

## JSON output

Add `--json` for structured output: `{"success": true, "data": {...}}` on success, `{"error": true, "code": "...", "message": "..."}` on failure. `chat ask` data: `{text, conversation_id, model}`. `chat image` data: `{file_id, download_url, conversation_id, saved_to}`.

## Auth

All commands require login. `cli-web-chatgpt auth login` opens a browser for OpenAI SSO and saves session cookies; `auth status` checks them; `auth logout` removes them. Use `cli-web-chatgpt doctor` to diagnose auth problems.

## Utilities

`cli-web-chatgpt doctor [--json]` diagnoses local setup (install, auth, dependencies). `cli-web-chatgpt mcp-serve` exposes the commands as MCP tools over stdio.

## Agent tips

- Chat and image generation take 15–60s (headless browser round-trip); read-only commands return immediately.
- Reuse `conversation_id` from a previous `chat ask` to keep context across calls.
