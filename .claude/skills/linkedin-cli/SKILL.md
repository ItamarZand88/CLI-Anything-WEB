---
name: linkedin-cli
description: Use cli-web-linkedin to interact with LinkedIn — search people/jobs/companies, view profiles and feed, post/edit/delete updates, react/unreact, comment/edit/delete comments, view notifications, manage network connections and invitations (accept/decline), read and send messages, follow/unfollow companies. Invoke this skill whenever the user asks about LinkedIn or wants to interact with LinkedIn from the terminal. Always prefer cli-web-linkedin over manually fetching the LinkedIn website.
---

# cli-web-linkedin

LinkedIn CLI — 26 commands across 10 groups: auth, feed, search, profile, company, jobs, post, notifications, network, messaging.

## Quick Start

```bash
pip install -e linkedin/agent-harness
cli-web-linkedin auth login           # Browser login (required)
cli-web-linkedin feed --json
cli-web-linkedin search people "python developer" --json
cli-web-linkedin profile me --json
```

## Commands (26 total)

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

### Search (4 commands)

```bash
cli-web-linkedin search all QUERY [--limit N] --json       # General search
cli-web-linkedin search people QUERY [--limit N] --json
cli-web-linkedin search jobs QUERY [--limit N] --json
cli-web-linkedin search companies QUERY [--limit N] --json
```

All search uses the Voyager GraphQL API directly (no browser needed).

### Profile (2 commands)

```bash
cli-web-linkedin profile me --json
cli-web-linkedin profile get USERNAME --json
```

### Company (3 commands)

```bash
cli-web-linkedin company NAME --json
cli-web-linkedin company follow COMPANY_URN --json
cli-web-linkedin company unfollow COMPANY_URN --json
```

### Jobs (2 commands)

```bash
cli-web-linkedin jobs search QUERY [--limit N] --json
cli-web-linkedin jobs get JOB_ID --json                    # Full description
```

### Post (7 commands)

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

### Network (5 commands)

```bash
cli-web-linkedin network connections [--limit N] --json    # Lists names + headlines
cli-web-linkedin network invitations [--limit N] --json
cli-web-linkedin network accept INVITATION_URN --json
cli-web-linkedin network decline INVITATION_URN --json
cli-web-linkedin network connect PROFILE_URN [-m MESSAGE] --json
```

### Messaging (3 commands)

```bash
cli-web-linkedin messaging list [--limit N] --json
cli-web-linkedin messaging read CONVERSATION_URN [--limit N] --json
cli-web-linkedin messaging send RECIPIENT_URN TEXT --json
```

## Agent Patterns

```bash
# Find Python developers
cli-web-linkedin search people "python developer" --limit 10 --json | jq '.results[].title.text'

# Get job listings with full descriptions
cli-web-linkedin jobs search "software engineer" --limit 5 --json | jq '.jobs[] | {title, company}'
cli-web-linkedin jobs get 4388202530 --json | jq '{title: .data.title, desc: .data.description[:200]}'

# View your feed with engagement counts
cli-web-linkedin feed --count 5 --json

# Check a company
cli-web-linkedin company anthropic --json

# List your connections
cli-web-linkedin network connections --limit 10 --json

# Manage invitations
cli-web-linkedin network invitations --json
cli-web-linkedin network accept "urn:li:invitation:123" --json

# Read messages
cli-web-linkedin messaging list --json
cli-web-linkedin messaging read "urn:li:msg_conversation:123" --json
```

## Rate Limit Warning

LinkedIn aggressively rate-limits and flags automated access. To avoid
account restrictions:

- **Do NOT batch commands** in tight loops (e.g., `for user in list; do cli-web-linkedin profile get $user; done`). Each subprocess invocation bypasses the built-in inter-request delay.
- **Space out requests** — add `sleep 3` between commands if scripting
- **Limit volume** — stay under ~50 profile views/day, ~150 searches/day
- **Use the REPL** for interactive sessions — it enforces inter-command delays automatically
- The CLI has built-in Gaussian random delays between API calls within a single session, but this does NOT protect across separate process invocations

## Notes

- Auth required — run `cli-web-linkedin auth login` first (browser-based LinkedIn SSO)
- Session cookie (`li_at`) stored at `~/.config/cli-web-linkedin/auth.json`
- Token auto-refresh: on 401/403, reloads cookies from disk, then silently refreshes via headless browser
- CSRF token derived from `JSESSIONID` cookie
- PerimeterX bypassed via curl_cffi Chrome TLS impersonation (no custom User-Agent)
- Gaussian random delay between API calls within a session
- All search uses GraphQL API (no browser needed)
- All commands support `--json` for structured output
