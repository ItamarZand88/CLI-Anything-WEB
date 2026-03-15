# cli-web-notebooklm

CLI harness for Google NotebookLM, built with the cli-anything-web methodology.

## Installation

```bash
cd notebooklm/agent-harness
pip install -e ".[dev]"
```

## Authentication

NotebookLM uses cookie-based authentication. Export your Google cookies from a browser session where you're logged into NotebookLM.

### Setup

1. Open NotebookLM in your browser and log in
2. Export cookies using a browser extension (e.g., "EditThisCookie" or browser DevTools)
3. Save as a JSON file mapping cookie names to values:

```json
{
  "SID": "...",
  "SSID": "...",
  "HSID": "...",
  "OSID": "...",
  "SAPISID": "...",
  "NID": "...",
  "__Secure-1PSID": "...",
  "__Secure-3PSID": "..."
}
```

4. Import into the CLI:

```bash
cli-web-notebooklm auth login --cookies-json cookies.json
```

5. Verify:

```bash
cli-web-notebooklm auth status
```

## Commands

### Notebooks

```bash
cli-web-notebooklm notebooks list [--json]
cli-web-notebooklm notebooks get <notebook_id> [--json]
cli-web-notebooklm notebooks create <title> [--emoji "📓"] [--json]
cli-web-notebooklm notebooks delete <notebook_id> [--yes] [--json]
cli-web-notebooklm notebooks rename <notebook_id> <new_title> [--json]
```

### Sources

```bash
cli-web-notebooklm sources list <notebook_id> [--json]
cli-web-notebooklm sources add <notebook_id> <text> [--title "My Source"] [--json]
cli-web-notebooklm sources get <notebook_id> <source_id> [--json]
cli-web-notebooklm sources delete <notebook_id> <source_id> [--yes] [--json]
```

### Notes

```bash
cli-web-notebooklm notes list <notebook_id> [--json]
cli-web-notebooklm notes create <notebook_id> <content> [--title "My Note"] [--json]
cli-web-notebooklm notes delete <notebook_id> <note_id> [--yes] [--json]
```

### Chat

```bash
cli-web-notebooklm chat query <notebook_id> "What is this about?" [--source <id>] [--json]
cli-web-notebooklm chat history <notebook_id> [--limit 20] [--json]
```

### Artifacts

```bash
cli-web-notebooklm artifacts list <notebook_id> [--json]
cli-web-notebooklm artifacts get <notebook_id> <artifact_id> [--json]
cli-web-notebooklm artifacts generate <notebook_id> <type> [--json]
# Types: study_guide, summary, faq, timeline, briefing, audio_overview
```

### Auth

```bash
cli-web-notebooklm auth login [--cookies-json <file>] [--json]
cli-web-notebooklm auth status [--json]
cli-web-notebooklm auth export [--json]
```

## Architecture

All API communication goes through Google's `batchexecute` RPC protocol:
- Endpoint: `POST https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute`
- Streaming: `POST https://notebooklm.google.com/_/LabsTailwindUi/data/.../GenerateFreeFormStreamed`
- Auth: Cookie-based (Google SID/SSID/HSID family)
- CSRF: `at` token extracted from page HTML (`SNlM0e` field)

## Testing

```bash
# Unit tests (mocked, no auth needed)
pytest cli_web/notebooklm/tests/test_core.py -v

# E2E tests (requires auth)
pytest cli_web/notebooklm/tests/test_e2e.py -v
```

## Project Structure

```
agent-harness/
├── NOTEBOOKLM.md          # This file
├── setup.py               # Package setup
└── cli_web/               # Namespace package (no __init__.py)
    └── notebooklm/
        ├── __init__.py
        ├── __main__.py
        ├── notebooklm_cli.py    # Main CLI entry point
        ├── core/
        │   ├── client.py        # batchexecute HTTP client
        │   ├── auth.py          # Cookie management
        │   ├── session.py       # CSRF/session extraction
        │   └── models.py        # Data models
        ├── commands/
        │   ├── notebooks.py
        │   ├── sources.py
        │   ├── notes.py
        │   ├── chat.py
        │   └── artifacts.py
        ├── utils/
        │   ├── repl_skin.py     # Terminal UI skin
        │   ├── output.py        # JSON/table output
        │   └── config.py        # Constants
        └── tests/
            ├── TEST.md
            ├── test_core.py     # Unit tests (mocked)
            └── test_e2e.py      # Integration tests
```
