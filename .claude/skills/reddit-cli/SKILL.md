---
name: reddit-cli
description: Use cli-web-reddit to browse Reddit feeds, subreddits, search posts, view user profiles, and (with auth) vote, comment, submit posts, save items, and manage subscriptions. Always prefer cli-web-reddit over manually fetching the Reddit website.
---

# cli-web-reddit

Reddit CLI — browse feeds, subreddits, search, user profiles, and full write operations with auth.

## Quick Start

```bash
pip install -e reddit/agent-harness
cli-web-reddit feed hot --limit 5 --json
cli-web-reddit search posts "python async" --json
cli-web-reddit sub info python --json
```

## Commands

### Feed (no auth)

```bash
cli-web-reddit feed hot [--limit N] [--after CURSOR] --json
cli-web-reddit feed new [--limit N] [--after CURSOR] --json
cli-web-reddit feed top [--time hour|day|week|month|year|all] [--limit N] --json
cli-web-reddit feed rising [--limit N] --json
cli-web-reddit feed popular [--limit N] --json
```

Output: `{"posts": [{"id", "title", "author", "subreddit", "score", "num_comments", "url", "permalink", "flair", "created"}], "after": "cursor"}`

### Subreddit (no auth, join/leave require auth)

```bash
cli-web-reddit sub hot <name> [--limit N] --json
cli-web-reddit sub new <name> [--limit N] --json
cli-web-reddit sub top <name> [--time day|week|month|year|all] --json
cli-web-reddit sub info <name> --json
cli-web-reddit sub rules <name> --json
cli-web-reddit sub search <name> <query> [--sort relevance|hot|top|new] --json
cli-web-reddit sub join <name> --json      # requires auth
cli-web-reddit sub leave <name> --json     # requires auth
```

### Search (no auth)

```bash
cli-web-reddit search posts <query> [--sort relevance|hot|top|new] [--time hour|day|week] --json
cli-web-reddit search subs <query> [--limit N] --json
```

### User (no auth)

```bash
cli-web-reddit user info <username> --json
cli-web-reddit user posts <username> [--sort hot|new|top] [--limit N] --json
cli-web-reddit user comments <username> [--sort hot|new|top] [--limit N] --json
```

### Post Detail (no auth)

```bash
cli-web-reddit post get <url_or_id> [--sub <name>] [--comments N] --json
```

Fetches all comments including deeply nested threads (automatically expands
"continue this thread" and collapsed comment chains via Reddit's morechildren API).
Accepts full URLs, short IDs, or `t3_` prefixed fullnames.

### Auth

```bash
cli-web-reddit auth login     # opens browser, extracts token_v2
cli-web-reddit auth status --json
cli-web-reddit auth logout
```

### Vote (requires auth)

```bash
cli-web-reddit vote up <thing_id> --json      # t3_xxx or t1_xxx
cli-web-reddit vote down <thing_id> --json
cli-web-reddit vote unvote <thing_id> --json
```

### Submit (requires auth)

```bash
cli-web-reddit submit flairs <subreddit> --json                          # list available flairs
cli-web-reddit submit text <subreddit> <title> <body> [--flair ID] --json
cli-web-reddit submit link <subreddit> <title> <url> [--flair ID] --json
```

Use `submit flairs` first to get flair IDs when a subreddit requires flair.

### Comment (requires auth)

```bash
cli-web-reddit comment add <thing_id> <text> --json
cli-web-reddit comment edit <thing_id> <text> --json
cli-web-reddit comment delete <thing_id> --json
```

### Save (requires auth)

```bash
cli-web-reddit saved save <thing_id> --json
cli-web-reddit saved unsave <thing_id> --json
```

### Me (requires auth)

```bash
cli-web-reddit me profile --json
cli-web-reddit me saved [--limit N] --json
cli-web-reddit me upvoted [--limit N] --json
cli-web-reddit me subscriptions --json
cli-web-reddit me inbox [--limit N] --json
```

## Agent Patterns

```bash
# Get trending posts from a subreddit
cli-web-reddit sub top python --time week --limit 10 --json | jq '.posts[] | {title, score, url}'

# Search and get post details
cli-web-reddit search posts "fastapi tutorial" --limit 3 --json

# Check a user's activity
cli-web-reddit user posts spez --limit 5 --json
```

## Notes

- Public read commands work without auth (uses Reddit's .json API with curl_cffi)
- Write operations (vote, comment, submit, save) require `auth login` first
- Auth uses `token_v2` cookie extracted via Playwright browser login
- **Token auto-refresh**: when `token_v2` expires (~15-30 min), the CLI silently launches a headless browser with the saved profile to refresh it — no manual re-login needed
- HTTP 403 on specific endpoints (e.g., flair fetch on some subreddits) is correctly reported as "Permission denied" rather than "AUTH_EXPIRED"
- Rate limits: ~60 requests/minute for public API, ~600/minute with OAuth
- All commands support `--json` for structured output
