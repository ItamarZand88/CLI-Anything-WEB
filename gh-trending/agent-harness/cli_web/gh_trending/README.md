# cli-web-github

A CLI for [GitHub Trending](https://github.com/trending) — explore trending repositories and developers.

## Installation

```bash
cd github/agent-harness
pip install -e .
```

## Usage

### REPL Mode (default)

```bash
cli-web-github
```

### One-shot Commands

```bash
# List trending repos today
cli-web-github repos list

# Filter by language and time range
cli-web-github repos list --language python --since weekly
cli-web-github repos list --language typescript --since monthly

# Filter by spoken language
cli-web-github repos list --spoken-language zh

# List trending developers
cli-web-github developers list
cli-web-github developers list --language javascript --since weekly

# JSON output (for agents)
cli-web-github repos list --json
cli-web-github developers list --language rust --json
```

## Options

### repos list

| Option | Description | Default |
|--------|-------------|---------|
| `-l, --language TEXT` | Programming language filter (python, javascript, etc.) | any |
| `-s, --since RANGE` | Time range: `daily`, `weekly`, `monthly` | `daily` |
| `-L, --spoken-language CODE` | Spoken language ISO 639-1 code (zh, en, es...) | any |
| `--json` | Output as JSON | false |

### developers list

| Option | Description | Default |
|--------|-------------|---------|
| `-l, --language TEXT` | Programming language filter | any |
| `-s, --since RANGE` | Time range: `daily`, `weekly`, `monthly` | `daily` |
| `--json` | Output as JSON | false |

## JSON Output Example

```bash
cli-web-github repos list --language python --json
```

```json
[
  {
    "rank": 1,
    "owner": "langchain-ai",
    "name": "open-swe",
    "full_name": "langchain-ai/open-swe",
    "description": "An Open-Source Asynchronous Coding Agent",
    "language": "Python",
    "stars": 6777,
    "forks": 854,
    "stars_today": 955,
    "url": "https://github.com/langchain-ai/open-swe",
    "contributors": ["bracesproul", "aran-yogesh"]
  }
]
```

## Auth (Optional)

GitHub Trending is publicly accessible. Auth is optional but available for future features.

```bash
# Login via browser
cli-web-github auth login

# Check auth status
cli-web-github auth status

# Import cookies from JSON
cli-web-github auth login --cookies-json /path/to/cookies.json
```

Auth is stored at `~/.config/cli-web-github/auth.json` (chmod 600).

## CI/CD

Override auth file location via environment variable:

```bash
export CLI_WEB_GITHUB_AUTH_JSON=/path/to/auth.json
cli-web-github repos list --json
```
