---
name: reddit-cli
description: Browses and interacts with Reddit via the cli-web-reddit command-line tool — feeds, subreddits, post search, post details with full comment trees, user profiles, and (after login) voting, commenting, submitting posts, saving, and subscriptions. Use when the user asks about Reddit, subreddits, Reddit posts or comments, or wants to act on Reddit from the terminal. Prefer this CLI over fetching the Reddit website.
---

# cli-web-reddit

Browse Reddit without auth; vote, comment, submit, and manage subscriptions after `auth login`.
Install: `pip install -e reddit/agent-harness`

## Commands

Read (no auth):

| Command | Purpose | Key options |
|---------|---------|-------------|
| `feed hot\|new\|top\|rising\|popular` | Front-page feeds | `--limit N` (max 100), `--after CURSOR`; `top` adds `--time hour\|day\|week\|month\|year\|all` |
| `sub hot\|new\|top NAME` | Subreddit posts | same as feed |
| `sub info NAME` / `sub rules NAME` | Subreddit metadata | |
| `sub search NAME QUERY` | Search within a subreddit | `--sort relevance\|hot\|top\|new\|comments`, `--limit`, `--after` |
| `search posts QUERY` | Search all of Reddit | `--sort`, `--time`, `--limit`, `--after` |
| `search subs QUERY` | Find subreddits | `--limit`, `--after` |
| `post get URL_OR_ID` | Post + full comment tree (expands nested threads) | `--sub NAME` (required with bare ID), `--comments N` |
| `user info\|posts\|comments USERNAME` | User profiles and activity | `--sort hot\|new\|top\|controversial`, `--time`, `--limit` |

Write (requires login). THING_ID is a fullname: `t3_xxx` (post) or `t1_xxx` (comment):

| Command | Purpose |
|---------|---------|
| `vote up\|down\|unvote THING_ID` | Vote |
| `comment add THING_ID TEXT` / `comment edit` / `comment delete` | Comment, reply, edit, delete |
| `submit text SUB TITLE BODY [--flair ID]` / `submit link SUB TITLE URL [--flair ID]` | Submit posts; `submit flairs SUB` lists flair IDs first |
| `saved save\|unsave THING_ID` | Save items |
| `sub join\|leave NAME` | Manage subscriptions |
| `me profile\|saved\|upvoted\|subscriptions\|inbox` | Your account (`--limit`, `--after` on lists) |

## Examples

```bash
# Top posts this week in r/python
cli-web-reddit sub top python --time week --limit 10 --json | jq '.posts[] | {title, score, url}'

# Search posts, then read one with comments
cli-web-reddit search posts "fastapi tutorial" --limit 3 --json
cli-web-reddit post get https://www.reddit.com/r/python/comments/abc123/my_post/ --json

# Submit a flaired text post (get flair IDs first)
cli-web-reddit submit flairs ClaudeCode --json
cli-web-reddit submit text ClaudeCode "My Title" "Body here" --flair abc123 --json

# Upvote a post
cli-web-reddit vote up t3_abc123 --json
```

## JSON output

Every command accepts `--json`. List reads return `{"posts": [...], "after": "cursor"}` (pass `after` back via `--after` to paginate); writes return `{"success": true, ...}`. Errors return `{"error": true, "code": "...", "message": "..."}`.

## Auth

```bash
cli-web-reddit auth login      # opens a Playwright browser, extracts the token_v2 cookie
cli-web-reddit auth status --json
cli-web-reddit auth logout
```

When `token_v2` expires (~15-30 min) the CLI refreshes it silently via a headless browser — no manual re-login. For CI, set `CLI_WEB_REDDIT_AUTH_JSON` with the cookies JSON. Run `doctor` to diagnose auth problems.

## Utilities

`cli-web-reddit doctor [--json]` self-diagnoses the local setup (install, auth, dependencies). `cli-web-reddit mcp-serve` serves the commands as MCP tools over stdio.

## Agent tips

- An HTTP 403 on a specific endpoint (e.g. flair fetch on some subreddits) means "permission denied" for that resource, not expired auth.
- Public rate limit is roughly 60 requests/minute — space out scripted reads.
