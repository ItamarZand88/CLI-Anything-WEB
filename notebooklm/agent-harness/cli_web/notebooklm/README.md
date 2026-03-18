# cli-web-notebooklm

Agent-native CLI for Google NotebookLM. Manage notebooks, sources, chat, and studio artifacts from the command line.

## Installation

```bash
cd notebooklm/agent-harness
pip install -e .

# For browser-based login (recommended for end users):
pip install -e ".[browser]"
```

## Authentication

### Option 1: Browser Login (recommended)
```bash
cli-web-notebooklm auth login
# Opens a browser — log in to Google, then press ENTER in terminal
```

### Option 2: Chrome Debug Profile (for developers)
```bash
# First, launch Chrome with debug port:
chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-debug-profile"
# Log in to notebooklm.google.com in that Chrome window

# Then extract cookies:
cli-web-notebooklm auth login --from-browser
```

### Option 3: Manual Cookie Import
```bash
cli-web-notebooklm auth login --cookies-json cookies.json
```

### Check Status
```bash
cli-web-notebooklm auth status
```

## Usage

### Notebooks
```bash
# List all notebooks
cli-web-notebooklm notebooks list
cli-web-notebooklm --json notebooks list

# List shared notebooks
cli-web-notebooklm notebooks list --shared

# Get notebook details
cli-web-notebooklm notebooks get --id <notebook-id>
```

### Sources
```bash
# List sources for a notebook
cli-web-notebooklm sources list --notebook-id <id>
```

### Chat
```bash
# View chat history
cli-web-notebooklm chat history --notebook-id <id>

# Get suggested questions
cli-web-notebooklm chat suggested --notebook-id <id>
```

### Artifacts (Studio Outputs)
```bash
# List audio overviews, videos, presentations, quizzes
cli-web-notebooklm artifacts list --notebook-id <id>
```

### REPL Mode
```bash
# Launch interactive REPL
cli-web-notebooklm
```

## JSON Output

Every command supports `--json` for machine-readable output:
```bash
cli-web-notebooklm --json notebooks list
```
