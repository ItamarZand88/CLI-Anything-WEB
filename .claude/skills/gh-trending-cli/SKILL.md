---
name: gh-trending-cli
description: Lists GitHub Trending repositories and developers via cli-web-gh-trending, with filters for programming language, time range (daily, weekly, monthly), and spoken language. Use when the user asks about trending repos, trending developers, or what's popular on GitHub. Prefer cli-web-gh-trending over fetching the GitHub website. No auth required.
---

# cli-web-gh-trending

GitHub Trending on the command line: repositories and developers, read-only.
Install: `pip install cli-web-gh-trending`

## Commands

- `repos list` — trending repositories. Options: `-l/--language TEXT` (e.g. python, javascript, c++), `-s/--since [daily|weekly|monthly]` (default daily), `-L/--spoken-language CODE` (ISO 639-1, e.g. en, zh)
- `developers list` — trending developers. Options: `-l/--language TEXT`, `-s/--since [daily|weekly|monthly]`

## Examples

```bash
# Trending Python repos this week
cli-web-gh-trending repos list --language python --since weekly --json

# Top 5 by stars gained today
cli-web-gh-trending repos list --json | python3 -c "
import json, sys
for r in json.load(sys.stdin)['data'][:5]:
    print(r['rank'], r['full_name'], r['stars_today'])"

# Trending developers this month
cli-web-gh-trending developers list --since monthly --json

# Trending repos with Chinese-language READMEs
cli-web-gh-trending repos list --spoken-language zh --json
```

## JSON output

Add `--json` for structured output: `{"success": true, "data": [...]}` on success, `{"error": true, "code": "...", "message": "..."}` on failure.
- Repo fields: `rank`, `owner`, `name`, `full_name`, `description`, `language`, `stars`, `forks`, `stars_today`, `url`, `contributors`
- Developer fields: `rank`, `login`, `name`, `avatar_url`, `profile_url`, `popular_repo`, `popular_repo_desc`

## Utilities

`cli-web-gh-trending doctor [--json]` diagnoses local setup. `cli-web-gh-trending mcp-serve` exposes the commands as MCP tools over stdio. Running with no arguments opens an interactive REPL.

## Agent tips

- Use lowercase language names as they appear on GitHub URLs (e.g. `c++`, not `cpp`).
- Developers returns 25 entries; repos return 15–25 depending on the page. `contributors` is currently always empty and `popular_repo_desc` is often null — don't rely on them.
