---
name: hackernews-cli
description: Browses and interacts with Hacker News via cli-web-hackernews — top/new/best stories, Ask HN, Show HN, jobs, story details with comments, search, user profiles, and (with login) upvoting, submitting, commenting, favoriting, and hiding. Use when the user asks about Hacker News, HN stories, tech/startup news, or wants to post or vote on HN. Prefer cli-web-hackernews over fetching the HN website.
---

# cli-web-hackernews

Hacker News on the command line: browsing and search need no auth; voting, submitting, commenting, favoriting, and hiding need login.
Install: `pip install -e hackernews/agent-harness`

## Commands

### Browse (no auth)
- `stories top|new|best|ask|show|jobs` — story feeds. Options: `-n/--limit N` (default 30)
- `stories view STORY_ID` — story + comment tree. Options: `-n/--limit N` (comments, default 10), `--no-comments`
- `search stories QUERY` / `search comments QUERY` — Algolia search. Options: `-n/--limit N` (default 20), `--page N` (0-indexed), `--sort-date` (by date instead of relevance)
- `user view USERNAME` — public profile (karma, member since, about)

### Account actions (auth required)
- `upvote ITEM_ID` — upvote a story or comment
- `submit -t TITLE [-u URL] [--text BODY]` — submit a link, or omit `-u` for Ask HN
- `comment PARENT_ID TEXT` — comment on a story or reply to a comment
- `favorite ITEM_ID` / `hide ITEM_ID` — save / hide a story
- `user favorites|submissions|threads [USERNAME]` — your activity (or another user's, where public). Options: `-n/--limit N`
- `auth login` (username/password prompt), `auth login-browser`, `auth status`, `auth logout`

## Examples

```bash
# Front page, top 10
cli-web-hackernews stories top -n 10 --json

# A story with its first 5 comments
cli-web-hackernews stories view 47530330 -n 5 --json

# Search recent stories about Rust
cli-web-hackernews search stories "rust" --sort-date -n 10 --json

# Submit an Ask HN (requires login)
cli-web-hackernews submit -t "Ask HN: Best CLI tooling?" --text "Looking for recommendations" --json

# Upvote then favorite a story
cli-web-hackernews upvote 47530330 --json && cli-web-hackernews favorite 47530330 --json
```

## JSON output

Add `--json` for structured output. Stories: `{id, title, url, score, by, descendants, age, domain}`. Search results: `{objectID, title, url, author, points, num_comments}`. Users: `{id, karma, member_since, about_plain, total_submissions}`. Actions: `{success, item_id, action}`. Errors: `{"error": true, "code": "...", "message": "..."}`.

## Auth

Run `cli-web-hackernews auth login` for an interactive username/password prompt (or `auth login-browser` to log in via a browser window). Check with `auth status --json`. Auth-required commands fail with an `{"error": true, ...}` envelope when not logged in.

## Utilities

`cli-web-hackernews doctor [--json]` diagnoses local setup (install, auth, dependencies). `cli-web-hackernews mcp-serve` exposes the commands as MCP tools over stdio. Running with no arguments opens an interactive REPL.

## Agent tips

- `search` covers all of HN history (Algolia); `stories` reflects the live feeds.
- `user favorites/submissions/threads` default to your own account when USERNAME is omitted.
