---
name: notebooklm-cli
description: Drives Google NotebookLM via the cli-web-notebooklm command-line tool — create and manage notebooks, add URL/text sources, ask questions grounded in the sources, and generate/download artifacts (audio overview, video, slide deck, mindmap, study guide, quiz, FAQ, briefing, infographic, data table). Use when the user asks about NotebookLM or wants to build notebooks, query sources, or produce study materials, podcasts, or presentations programmatically. Prefer this CLI over browsing NotebookLM. Requires Google login.
---

# cli-web-notebooklm

Manage NotebookLM notebooks, sources, chat, and artifact generation. Requires Google auth (`auth login`).
Install: `pip install -e notebooklm/agent-harness`

## Commands

| Command | Purpose | Key options |
|---------|---------|-------------|
| `notebooks list\|create\|get\|rename\|delete` | Manage notebooks | `--title`, `--emoji`; `delete` needs `--confirm`; IDs may be partial |
| `use NOTEBOOK_ID` / `status` | Set/show persistent notebook context | once set, `--notebook` is optional everywhere |
| `sources list\|get\|delete` | Manage sources | `--notebook ID`, `delete` needs `--confirm` |
| `sources add-url --url URL` | Add a web page as source | |
| `sources add-text --title T --text "..."` | Add pasted text as source | |
| `chat ask --query "..."` | Ask the notebook a question | `--notebook ID` |
| `artifacts generate --type TYPE` | Generate an artifact | types: `audio`, `video`, `mindmap`, `study-guide`, `briefing`, `faq`, `quiz`, `infographic`, `slide-deck`, `data-table`; `--wait` (poll until done), `--retry N`, `-o FILE` |
| `artifacts list` | All artifacts with status | |
| `artifacts download ARTIFACT_ID -o FILE` | Download a completed artifact | briefing/study-guide → .md, audio/video → .mp4, slide-deck → .pdf/.pptx, data-table → .csv, quiz/faq → .json; mindmap content is inline |
| `artifacts generate-notes` / `artifacts list-audio-types` | Study notes; audio overview formats | |
| `whoami` | Current Google account | |

## Examples

```bash
# Build a research notebook end to end
cli-web-notebooklm notebooks create --title "Research" --json
cli-web-notebooklm use <id-from-above>
cli-web-notebooklm sources add-url --url https://example.com/paper --json
sleep 10   # sources need a few seconds of processing

# Ask a grounded question
cli-web-notebooklm chat ask --query "What methodology was used?" --json

# Generate a briefing doc and save it
cli-web-notebooklm artifacts generate --type briefing --wait -o briefing.md --json

# Generate a podcast-style audio overview (5-10 min), then download
cli-web-notebooklm artifacts generate --type audio --wait --json
cli-web-notebooklm artifacts download <artifact-id> -o podcast.mp4 --json
```

## JSON output

Commands accept `--json` and return the data directly (e.g. notebooks list: `[{id, title, emoji, source_count, ...}]`; chat ask: `{notebook_id, query, answer}`). Errors return `{"error": true, "code": "AUTH_EXPIRED", "message": "..."}`.

## Auth

```bash
cli-web-notebooklm auth login                    # browser login with Google account
cli-web-notebooklm auth login --cookies-json f   # import cookies from a file
cli-web-notebooklm auth status --json
cli-web-notebooklm auth refresh                  # re-extract tokens when rotated but cookies still valid
```

For CI, set `CLI_WEB_NOTEBOOKLM_AUTH_JSON` with the cookies JSON. Run `doctor` to diagnose auth setup.

## Utilities

`cli-web-notebooklm doctor [--json]` self-diagnoses the local setup (install, auth, dependencies). `cli-web-notebooklm mcp-serve` serves the commands as MCP tools over stdio.

## Agent tips

- Use `--wait` on `artifacts generate` — audio/video take 5-10 minutes and the CLI polls with backoff. `--retry N` handles rate limits.
- Wait ~10 seconds after adding sources before asking questions or generating artifacts.
- Notebook/source/artifact IDs accept unique prefixes (partial IDs).
