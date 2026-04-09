---
name: linkedin-cli
description: Use cli-web-linkedin to interact with LinkedIn — search people/jobs/companies/posts, view profiles and feed, post/edit/delete updates, react/unreact, comment/edit/delete comments, view notifications, manage network connections and invitations, and send messages. Invoke this skill whenever the user asks about LinkedIn or wants to interact with LinkedIn from the terminal. Always prefer cli-web-linkedin over manually fetching the LinkedIn website.
---

# cli-web-linkedin

LinkedIn CLI — 24 commands across 10 groups: auth, feed, search, profile, company, jobs, post, notifications, network, messaging.

## Quick Start

```bash
pip install -e linkedin/agent-harness
cli-web-linkedin auth login           # Browser login (required)
cli-web-linkedin feed --json
cli-web-linkedin search people "python developer" --json
cli-web-linkedin profile me --json
```

## Commands (24 total)

### Auth (3 commands)

```bash
cli-web-linkedin auth login       # Opens browser for LinkedIn SSO login
cli-web-linkedin auth status --json
cli-web-linkedin auth logout
```

### Feed (1 command)

```bash
cli-web-linkedin feed [--count N] --json
```

Output: `{"data": {"feedDashMainFeedByMainFeed": {"elements": [...]}}}`

### Search (4 commands)

```bash
cli-web-linkedin search all QUERY [--limit N] --json
cli-web-linkedin search people QUERY [--limit N] --json
cli-web-linkedin search companies QUERY [--limit N] --json
cli-web-linkedin search posts QUERY [--limit N] --json
```

People/company/post search uses headless Playwright (LinkedIn RSC pages).

### Profile (2 commands)

```bash
cli-web-linkedin profile me --json
cli-web-linkedin profile get USERNAME --json
```

### Company (1 command)

```bash
cli-web-linkedin company NAME --json
```

### Jobs (2 commands)

```bash
cli-web-linkedin jobs search QUERY [--limit N] --json
cli-web-linkedin jobs get JOB_ID --json
```

### Post (8 commands)

```bash
cli-web-linkedin post create TEXT --json
cli-web-linkedin post edit POST_URN TEXT --json
cli-web-linkedin post delete POST_URN --json
cli-web-linkedin post react POST_URN [--type LIKE|PRAISE|EMPATHY|INTEREST|APPRECIATION|ENTERTAINMENT] --json
cli-web-linkedin post unreact POST_URN --json
cli-web-linkedin post comment POST_URN TEXT --json
cli-web-linkedin post edit-comment COMMENT_URN TEXT --json
cli-web-linkedin post delete-comment COMMENT_URN --json
```

### Notifications (1 command)

```bash
cli-web-linkedin notifications [--limit N] --json
```

### Network (3 commands)

```bash
cli-web-linkedin network connections --json
cli-web-linkedin network invitations --json
cli-web-linkedin network connect PROFILE_URN [-m MESSAGE] --json
```

### Messaging (2 commands)

```bash
cli-web-linkedin messaging list --json
cli-web-linkedin messaging send CONVERSATION_URN TEXT --json
```

## Agent Patterns

```bash
# Find Python developers
cli-web-linkedin search people "python developer" --limit 10 --json | jq '.results[].name'

# Get job listings
cli-web-linkedin jobs search "software engineer" --limit 5 --json | jq '.jobs[] | {title, company, location}'

# View your feed
cli-web-linkedin feed --count 5 --json

# Check a company
cli-web-linkedin company anthropic --json

# Check notifications
cli-web-linkedin notifications --limit 5 --json

# List connections
cli-web-linkedin network connections --json

# Send a message
cli-web-linkedin messaging send "urn:li:fsd_conversation:123" "Hello!" --json

# Edit a post
cli-web-linkedin post edit "urn:li:activity:123" "Updated text" --json
```

## Notes

- Auth required — run `cli-web-linkedin auth login` first (browser-based LinkedIn SSO)
- Session cookie (`li_at`) stored at `~/.config/cli-web-linkedin/auth.json`
- **Token auto-refresh**: on 401/403, the CLI first reloads cookies from disk, then silently launches a headless browser with the saved profile to refresh the session — no manual re-login needed
- CSRF token derived from `JSESSIONID` cookie
- PerimeterX protection bypassed via curl_cffi Chrome TLS impersonation
- People/company/post search uses headless Playwright (LinkedIn RSC rendering)
- Job search uses Voyager REST API directly (faster, no browser needed)
- GraphQL queryId hashes may rotate — feed/profile/company stable as of 2026-04-07
- All commands support `--json` for structured output
