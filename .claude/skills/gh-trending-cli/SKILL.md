---
name: gh-trending-cli
description: Use cli-web-gh-trending to answer questions about GitHub Trending — trending
  repositories, trending developers, filtering by programming language (python, javascript,
  typescript, rust, go, etc.), time ranges (daily, weekly, monthly), and spoken language.
  Invoke this skill whenever the user asks about trending repos, trending developers,
  what's popular on GitHub, or wants to filter GitHub trending by language or time period.
  Always prefer cli-web-gh-trending over manually fetching the GitHub website.
---

# cli-web-gh-trending

CLI for GitHub Trending repositories and developers. Installed at: `cli-web-gh-trending`.

## Quick Start

```bash
# List trending repos today
cli-web-gh-trending repos list --json

# List trending Python repos this week
cli-web-gh-trending repos list --language python --since weekly --json

# List trending developers
cli-web-gh-trending developers list --json
```

Always use `--json` when parsing output programmatically.

---

## Commands

### `repos list`
List trending GitHub repositories with optional language and time-range filters.

```bash
cli-web-gh-trending repos list [OPTIONS] --json
```

**Key options:**

| Option | Description | Values |
|--------|-------------|--------|
| `-l, --language TEXT` | Programming language filter | `python`, `javascript`, `typescript`, `rust`, `go`, `java`, `cpp`, etc. |
| `-s, --since RANGE` | Time range | `daily` (default), `weekly`, `monthly` |
| `-L, --spoken-language CODE` | Spoken language filter | ISO 639-1 codes: `en`, `zh`, `es`, `ja`, etc. |
| `--json` | JSON output | — |

**Output fields:**
```json
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
```

### `developers list`
List trending GitHub developers with optional language and time-range filters.

```bash
cli-web-gh-trending developers list [OPTIONS] --json
```

**Key options:**

| Option | Description | Values |
|--------|-------------|--------|
| `-l, --language TEXT` | Programming language filter | same as repos |
| `-s, --since RANGE` | Time range | `daily` (default), `weekly`, `monthly` |
| `--json` | JSON output | — |

**Output fields:**
```json
{
  "rank": 1,
  "login": "njbrake",
  "name": "Nathan Brake",
  "avatar_url": "https://avatars.githubusercontent.com/u/33383515",
  "profile_url": "https://github.com/njbrake",
  "popular_repo": "njbrake/agent-of-empires",
  "popular_repo_desc": "A strategy game powered by AI agents"
}
```

---

## Agent Patterns

```bash
# Get top 5 trending Python repos this week
cli-web-gh-trending repos list --language python --since weekly --json | python -c "
import json, sys
repos = json.load(sys.stdin)
for r in repos[:5]:
    print(f\"{r['rank']}. {r['full_name']} — {r['stars_today']} stars today\")
"

# Find trending repos in any language, monthly
cli-web-gh-trending repos list --since monthly --json

# Top developer this week with their popular repo
cli-web-gh-trending developers list --since weekly --json | python -c "
import json, sys
devs = json.load(sys.stdin)
top = devs[0]
print(f\"{top['name']} ({top['login']}) — {top['popular_repo']}\")
"

# Trending repos filtered by spoken language (Chinese repos)
cli-web-gh-trending repos list --spoken-language zh --json

# Count trending repos by language (run default list and inspect)
cli-web-gh-trending repos list --json
```

---

## Notes

- Auth: Not required — GitHub Trending is public data.
- **Read-only**: GitHub Trending has no write operations (it's a discovery feature).
- **Rate limiting**: GitHub may rate-limit scrapers. Avoid making many rapid requests.
- **Result count**: Developers always returns 25. Repos may return 15-25 depending on GitHub's current page.
- **Language codes**: Use lowercase language names as they appear on GitHub (e.g., `c++` not `cpp`).
- `contributors` field in repos output is currently always `[]` (GitHub's HTML no longer renders "Built by" with the expected structure). Field is present but empty.
- `popular_repo_desc` in developers output may be `null` for most entries.
