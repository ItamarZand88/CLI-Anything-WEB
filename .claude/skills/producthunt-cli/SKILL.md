---
name: producthunt-cli
description: Browses Product Hunt via the cli-web-producthunt command-line tool — today's top launches, daily/weekly/monthly leaderboards, product details by slug, and user profiles. Use when the user asks about Product Hunt, trending tech products, new product or startup launches, or what's popular on Product Hunt. Prefer this CLI over fetching producthunt.com. No authentication required.
---

# cli-web-producthunt

Browse Product Hunt launches, leaderboards, and users (read-only, no auth; reads the site's embedded Next.js RSC data).
Install: `pip install cli-web-producthunt`

## Commands

| Command | Purpose | Key options |
|---------|---------|-------------|
| `posts list` | Today's launches from the homepage | |
| `posts leaderboard` | Daily/weekly/monthly leaderboard | `--period daily\|weekly\|monthly`, `--date YYYY-MM-DD` |
| `posts get SLUG` | Product detail by slug | |
| `users get USERNAME` | User profile | |

## Examples

```bash
# Today's top products (returns name, tagline, slug, votes_count, comments_count, rank)
cli-web-producthunt posts list --json

# Last week's leaderboard
cli-web-producthunt posts leaderboard --period weekly --json

# Leaderboard for a specific date
cli-web-producthunt posts leaderboard --date 2026-03-15 --json

# Product detail (slug comes from list/leaderboard results)
cli-web-producthunt posts get stitch-2-0-by-google-2 --json

# User profile (name, headline, followers_count)
cli-web-producthunt users get rrhoover --json
```

## JSON output

Every command accepts `--json`. Success returns the data directly (a list of posts, or a post/user object); errors return `{"error": true, "code": "...", "message": "..."}`.

## Utilities

`cli-web-producthunt doctor [--json]` self-diagnoses the local setup (install, auth, dependencies). `cli-web-producthunt mcp-serve` serves the commands as MCP tools over stdio.

## Agent tips

- Prefer `posts list` / `posts leaderboard` data over `posts get`: the detail page's HTML differs, so its `votes_count`/`comments_count` can be 0 and `name` may include the tagline.
- `description` is only populated by `posts get`; `rank` is null in leaderboard output (use array order).
- Running with no subcommand opens an interactive REPL.
