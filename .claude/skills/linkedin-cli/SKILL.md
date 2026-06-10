---
name: linkedin-cli
description: Interacts with LinkedIn via the cli-web-linkedin command-line tool — search people/jobs/companies, view profiles and feed, create/edit/delete posts, react and comment, manage connections and invitations, read and send messages, view notifications, follow companies. Use when the user asks about LinkedIn or wants to search, post, network, or message on LinkedIn from the terminal. Prefer this CLI over fetching the LinkedIn website. Requires login.
---

# cli-web-linkedin

Full LinkedIn client: search, profiles, feed, posting, reactions, comments, network, and messaging. All commands require `auth login` first.
Install: `pip install -e linkedin/agent-harness`

## Commands

| Group | Commands |
|-------|----------|
| `search` | `all\|people\|jobs\|companies QUERY [--limit N]` (default 10) |
| `profile` | `me`, `get USERNAME` |
| `feed` | `feed [--count N]` |
| `company` | `company NAME` (view page), `company follow\|unfollow COMPANY_URN` |
| `jobs` | `search QUERY [--limit N]`, `get JOB_ID` (full description) |
| `post` | `create TEXT`, `edit POST_URN TEXT`, `delete POST_URN`, `react POST_URN [--type LIKE\|PRAISE\|EMPATHY\|INTEREST\|APPRECIATION\|ENTERTAINMENT]`, `unreact POST_URN`, `comment POST_URN TEXT`, `edit-comment COMMENT_URN TEXT`, `delete-comment COMMENT_URN` |
| `notifications` | `notifications [--limit N]` |
| `network` | `connections [--limit N]`, `invitations [--limit N]`, `accept\|decline INVITATION_URN`, `connect PROFILE_URN [-m MESSAGE]` |
| `messaging` | `list [--limit N]`, `read CONVERSATION_URN [--limit N]`, `send RECIPIENT TEXT` (conversation or profile URN) |
| `auth` | `login`, `status`, `logout` |

## Examples

```bash
# Find people (returns name, headline, profile URL per result)
cli-web-linkedin search people "python developer" --limit 10 --json

# Job search, then full description
cli-web-linkedin jobs search "software engineer" --limit 5 --json
cli-web-linkedin jobs get 4388202530 --json

# Publish a post
cli-web-linkedin post create "Hello LinkedIn!" --json

# Pending invitations, then accept one (URN from the list)
cli-web-linkedin network invitations --json
cli-web-linkedin network accept "urn:li:invitation:123" --json

# Read recent messages
cli-web-linkedin messaging list --json
cli-web-linkedin messaging read "urn:li:msg_conversation:123" --json
```

## JSON output

Every command accepts `--json`. Reads return the data object directly; writes return `{"success": true, ...}`. Errors return `{"error": true, "code": "...", "message": "..."}`.

## Auth

```bash
cli-web-linkedin auth login      # browser-based LinkedIn login, stores li_at cookie
cli-web-linkedin auth status --json
```

Cookies live in `~/.config/cli-web-linkedin/auth.json`; on 401/403 the CLI reloads them from disk, then refreshes via headless browser. For CI, set `CLI_WEB_LINKEDIN_AUTH_JSON` with the cookies JSON. Run `doctor` to diagnose auth problems.

## Utilities

`cli-web-linkedin doctor [--json]` self-diagnoses the local setup (install, auth, dependencies). `cli-web-linkedin mcp-serve` serves the commands as MCP tools over stdio.

## Agent tips

LinkedIn flags automated access aggressively; keep usage human-paced to protect the account:
- Add `sleep 3` between scripted invocations instead of tight loops — built-in inter-request delays only apply within a single process.
- Stay under roughly 50 profile views and 150 searches per day.
- URNs (post, comment, invitation, conversation) come from the JSON output of list/read commands — fetch them rather than constructing by hand.
