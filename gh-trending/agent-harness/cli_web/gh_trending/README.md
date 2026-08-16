# cli-web-gh-trending

A CLI for [GitHub Trending](https://github.com/trending) — explore trending repositories and developers.

## Installation

```bash
pip install cli-web-gh-trending
```

## Usage

### REPL Mode (default)

```bash
cli-web-gh-trending
```

### One-shot Commands

```bash
# List trending repos today
cli-web-gh-trending repos list

# Filter by language and time range
cli-web-gh-trending repos list --language python --since weekly
cli-web-gh-trending repos list --language typescript --since monthly

# Filter by spoken language
cli-web-gh-trending repos list --spoken-language zh

# List trending developers
cli-web-gh-trending developers list
cli-web-gh-trending developers list --language javascript --since weekly

# JSON output (for agents)
cli-web-gh-trending repos list --json
cli-web-gh-trending developers list --language rust --json
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
cli-web-gh-trending repos list --language python --json
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
cli-web-gh-trending auth login

# Check auth status
cli-web-gh-trending auth status

# Import cookies from JSON
cli-web-gh-trending auth login --cookies-json /path/to/cookies.json
```

Auth is stored at `~/.config/cli-web-gh-trending/auth.json` (chmod 600).

## CI/CD

Override auth file location via environment variable:

```bash
export CLI_WEB_GH_TRENDING_AUTH_JSON=/path/to/auth.json
cli-web-gh-trending repos list --json
```
