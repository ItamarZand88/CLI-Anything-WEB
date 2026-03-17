# cli-web-suno

Agent-native CLI for [Suno](https://suno.com) AI Music Generator.

## Installation

```bash
cd suno/agent-harness
pip install -e .
```

With Playwright browser login support:
```bash
pip install -e ".[browser]"
```

## Authentication

### Option 1: From Chrome debug profile (recommended for dev)

1. Launch Chrome with debug profile:
   ```bash
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\.chrome-debug-profile"
   ```
2. Log into suno.com in that browser
3. Extract cookies:
   ```bash
   cli-web-suno auth login --from-browser
   cli-web-suno auth status
   ```

### Option 2: Playwright (for end users)

```bash
pip install playwright && playwright install chromium
cli-web-suno auth login
```

### Option 3: Manual cookie import

```bash
cli-web-suno auth login --cookies-json cookies.json
```

## Usage

### One-shot commands

```bash
# List your songs
cli-web-suno songs list
cli-web-suno --json songs list --limit 5

# Check generation status
cli-web-suno songs status

# Generate a song
cli-web-suno songs generate --description "a happy pop song about coding"

# Download a song
cli-web-suno songs download --id <song-id> --output song.mp3

# View billing/credits
cli-web-suno billing info

# Explore tags
cli-web-suno explore tags

# List projects
cli-web-suno projects list

# Get prompt suggestions
cli-web-suno prompts suggestions
```

### JSON output (for agents)

Add `--json` before any command:

```bash
cli-web-suno --json songs list
cli-web-suno --json billing info
cli-web-suno --json explore tags --tags "pop,rock"
```

### REPL mode

Run without arguments to enter interactive mode:

```bash
cli-web-suno
```

## Commands

| Group | Command | Description |
|-------|---------|-------------|
| `auth` | `login` | Login (Playwright / --from-browser / --cookies-json) |
| `auth` | `status` | Show auth status with live validation |
| `auth` | `refresh` | Refresh JWT token |
| `songs` | `list` | List your songs |
| `songs` | `get` | Get song details by ID |
| `songs` | `generate` | Generate a new song |
| `songs` | `status` | Check generation queue |
| `songs` | `download` | Download song audio |
| `explore` | `feed` | Homepage/trending feed |
| `explore` | `tags` | Get recommended style tags |
| `projects` | `list` | List your projects |
| `projects` | `get` | Get project with clips |
| `billing` | `info` | Show credits, plan, limits |
| `billing` | `plans` | List available plans |
| `prompts` | `list` | List saved prompts |
| `prompts` | `suggestions` | Get prompt suggestions |

## Testing

```bash
# Unit tests
python -m pytest cli_web/suno/tests/test_core.py -v

# E2E tests (requires auth)
cli-web-suno auth login --from-browser
python -m pytest cli_web/suno/tests/test_e2e.py -v -s

# Subprocess tests
CLI_WEB_FORCE_INSTALLED=1 python -m pytest cli_web/suno/tests/test_e2e.py -v -s -k subprocess
```
