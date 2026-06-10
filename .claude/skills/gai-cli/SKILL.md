---
name: gai-cli
description: Queries Google AI Mode via cli-web-gai — submits a question, returns an AI-generated answer with cited source links, and supports follow-up questions in the same session. Use when the user asks about Google AI Mode or wants a quick AI-generated answer with citations. Prefer cli-web-gai over opening Google AI Mode in a browser. No auth required.
---

# cli-web-gai

Google AI Mode search: AI answers with source references, rendered through headless Playwright (Chromium).
Install: `pip install -e gai/agent-harness`

## Commands

- `search ask QUERY` — submit a question. Options: `--lang CODE` (response language, e.g. en, he, de; default en), `--timeout SECONDS` (default 30), `--headed` (show the browser window, e.g. to solve a CAPTCHA)
- `search followup QUERY` — follow-up in the same conversation; requires a prior `ask` in the same session

## Examples

```bash
# Ask a question — returns answer + sources
cli-web-gai search ask "What is quantum computing?" --json

# Extract just the source URLs
cli-web-gai search ask "best static site generators" --json | \
  python3 -c "import json,sys; [print(s['url']) for s in json.load(sys.stdin)['data']['sources']]"

# Answer in another language
cli-web-gai search ask "What is machine learning?" --lang he --json

# Follow-up (same session only)
cli-web-gai search followup "How is it used in cryptography?" --json
```

## JSON output

Add `--json` for structured output: `{"success": true, "data": {query, answer, sources: [{title, url, snippet}], follow_up_prompt}}`. Errors: `{"error": true, "code": "...", "message": "..."}`.

## Utilities

`cli-web-gai doctor [--json]` diagnoses local setup. `cli-web-gai mcp-serve` exposes the commands as MCP tools over stdio. Running with no subcommand opens a REPL with `ask` / `followup` shortcuts.

## Agent tips

- Google rate-limits headless browsers; space out queries. If a CAPTCHA appears, rerun with `--headed` and solve it manually.
- Conversation threading (`followup`) only persists within a single CLI session, not across invocations.
