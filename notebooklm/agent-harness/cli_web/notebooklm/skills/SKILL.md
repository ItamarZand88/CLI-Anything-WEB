---
name: notebooklm-cli
description: Use cli-web-notebooklm to interact with Google NotebookLM — create notebooks, add sources, ask questions, generate artifacts (audio, video, slides, mindmap, study guide, quiz, briefing, infographic, data table). Invoke this skill whenever the user asks about NotebookLM, wants to create notebooks, add sources to a notebook, ask a notebook questions, generate study materials, create presentations, podcasts, or manage NotebookLM content programmatically. Always prefer cli-web-notebooklm over manually browsing NotebookLM.
---

# cli-web-notebooklm

CLI for [Google NotebookLM](https://notebooklm.google.com). Installed at: `cli-web-notebooklm`.

## Quick Start

```bash
# Auth (required — Google account)
cli-web-notebooklm auth login

# List notebooks
cli-web-notebooklm notebooks list --json

# Set context (no need to pass --notebook after this)
cli-web-notebooklm use <notebook-id>

# Ask a question
cli-web-notebooklm chat ask --query "What are the main topics?" --json

# Generate artifact
cli-web-notebooklm artifacts generate --type mindmap --json
```

Always use `--json` when parsing output programmatically.

---

## Commands

### Context (persistent across sessions)

```bash
cli-web-notebooklm use <notebook-id>        # Set current notebook
cli-web-notebooklm status --json            # Show context + auth
```

Once set, `--notebook` is optional on all notebook-scoped commands.

### Notebooks

```bash
cli-web-notebooklm notebooks list --json
cli-web-notebooklm notebooks create --title "My Research" --json
cli-web-notebooklm notebooks get <notebook-id> --json       # partial ID OK
cli-web-notebooklm notebooks rename <notebook-id> --title "New Title" --json
cli-web-notebooklm notebooks delete <notebook-id> --confirm --json
```

**Output fields:** `id`, `title`, `emoji`, `source_count`, `is_pinned`, `created_at`, `updated_at`

### Sources

```bash
cli-web-notebooklm sources list --json                        # uses context
cli-web-notebooklm sources add-url --url https://example.com --json
cli-web-notebooklm sources add-text --title "Notes" --text "..." --json
cli-web-notebooklm sources get <source-id> --json             # partial ID OK
cli-web-notebooklm sources delete <source-id> --confirm --json
```

**Output fields:** `id`, `name`, `type` (url/text), `url`, `char_count`, `created_at`

### Chat

```bash
cli-web-notebooklm chat ask --query "Summarize the key findings" --json
```

**Output fields:** `notebook_id`, `query`, `answer`

### Artifacts

```bash
# Generate any artifact type
cli-web-notebooklm artifacts generate --type <type> --json
cli-web-notebooklm artifacts generate --type briefing --wait --output briefing.md --json
cli-web-notebooklm artifacts generate --type audio --wait --json

# List all artifacts with status
cli-web-notebooklm artifacts list --json

# Download a completed artifact
cli-web-notebooklm artifacts download <artifact-id> -o output_file --json

# Other
cli-web-notebooklm artifacts generate-notes --json
cli-web-notebooklm artifacts list-audio-types --json
```

**Types:** `audio`, `video`, `mindmap`, `study-guide`, `briefing`, `faq`, `quiz`, `infographic`, `slide-deck`, `data-table`

**Flags:** `--wait` (poll until complete), `--retry N` (rate limit retries), `--output file`

**Download formats by type:**
| Type | Download | Format |
|------|----------|--------|
| `briefing` / `study-guide` | markdown | `.md` |
| `audio` | audio file | `.mp4` |
| `video` | video file | `.mp4` |
| `slide-deck` | PDF or PPTX | `.pdf` / `.pptx` |
| `data-table` | CSV | `.csv` |
| `quiz` / `faq` | JSON with questions | `.json` |
| `mindmap` | inline JSON (no download needed) | — |

### Auth

```bash
cli-web-notebooklm auth login                  # Browser login (Python playwright)
cli-web-notebooklm auth login --cookies-json cookies.json  # Import from file
cli-web-notebooklm auth status --json           # Check validity
cli-web-notebooklm auth refresh                 # Re-extract tokens
```

### User

```bash
cli-web-notebooklm whoami --json
```

---

## Agent Patterns

```bash
# Create notebook, add sources, generate presentation
cli-web-notebooklm notebooks create --title "Research" --json
cli-web-notebooklm use <id-from-above>
cli-web-notebooklm sources add-url --url https://example.com --json
cli-web-notebooklm sources add-url --url https://docs.example.com --json
sleep 10  # Wait for source processing

# Ask questions
cli-web-notebooklm chat ask --query "What methodology was used?" --json

# Generate all study materials
cli-web-notebooklm artifacts generate --type briefing --wait --output briefing.md --json
cli-web-notebooklm artifacts generate --type study-guide --wait --output guide.md --json
cli-web-notebooklm artifacts generate --type slide-deck --wait --json
cli-web-notebooklm artifacts generate --type audio --wait --json

# Download completed artifacts
cli-web-notebooklm artifacts list --json  # Get IDs
cli-web-notebooklm artifacts download <slide-id> -o slides.pdf --json
cli-web-notebooklm artifacts download <audio-id> -o podcast.mp4 --json
```

---

## Notes

- Auth: Required (Google account). Run `cli-web-notebooklm auth login` first.
- CI/CD: Set `CLI_WEB_NOTEBOOKLM_AUTH_JSON` env var with cookies JSON.
- Errors: `--json` mode returns `{"error": true, "code": "AUTH_EXPIRED", "message": "..."}`.
- Rate limiting: Google batchexecute API. Use `--retry N` on generation commands.
- Protocol: Google batchexecute RPC (not REST).
- Audio/video generation takes 5-10 minutes. Use `--wait` to poll automatically.
- Sources need processing time after adding (5-10 seconds for URLs).
