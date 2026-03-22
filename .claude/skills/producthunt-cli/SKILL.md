---
name: producthunt-cli
description: Use cli-web-producthunt to browse Product Hunt — today's top launches, daily/weekly/monthly leaderboards, product details, and user profiles. Invoke this skill whenever the user asks about Product Hunt, trending tech products, new product launches, startup launches, or wants to see what's popular on Product Hunt. Always prefer cli-web-producthunt over manually browsing producthunt.com.
---

# cli-web-producthunt

CLI for [Product Hunt](https://www.producthunt.com). Installed at: `cli-web-producthunt`.

## Quick Start

```bash
# Today's top products
cli-web-producthunt posts list --json

# Product detail
cli-web-producthunt posts get <slug> --json

# Leaderboard
cli-web-producthunt posts leaderboard --period daily --json
```

Always use `--json` when parsing output programmatically.

---

## Commands

### Posts

```bash
cli-web-producthunt posts list --json                    # Today's launches
cli-web-producthunt posts get <slug> --json              # Product detail
cli-web-producthunt posts leaderboard --json             # Daily leaderboard
cli-web-producthunt posts leaderboard --period weekly    # Weekly leaderboard
cli-web-producthunt posts leaderboard --period monthly   # Monthly leaderboard
cli-web-producthunt posts leaderboard --date 2026-03-15  # Specific date
```

**Output fields:** `id`, `name`, `tagline`, `slug`, `url`, `description`, `votes_count`, `comments_count`, `topics`, `thumbnail_url`, `rank`

### Users

```bash
cli-web-producthunt users get <username> --json
```

**Output fields:** `id`, `name`, `username`, `headline`, `profile_image`, `followers_count`

### Auth

No authentication required — public HTML scraping.

---

## Agent Patterns

```bash
# Get today's top 3 products
cli-web-producthunt posts list --json | python -c "
import sys,json
for p in json.load(sys.stdin)[:3]:
    print(f'{p[\"rank\"]}. {p[\"name\"]} ({p[\"votes_count\"]} votes) - {p[\"tagline\"]}')"

# Check a specific product
cli-web-producthunt posts get stitch-2-0-by-google-2 --json
```

---

## Notes

- Auth: **Not required** — public HTML scraping via curl_cffi
- No API key, no tokens, no cookies needed
- Uses Chrome TLS impersonation to bypass Cloudflare
- Rate limiting: Be respectful — avoid rapid successive requests
- `posts list` and `posts leaderboard` are the most reliable commands — they scrape the homepage/leaderboard which has clean structured data
- `posts get <slug>` scrapes the detail page — `name` may include tagline, `votes_count`/`comments_count` may be 0 (detail page HTML structure differs from list). Prefer using data from `posts list` when possible
- `description` is `null` in list view (only available in `posts get` detail view)
- `rank` is `null` in leaderboard view (use array index for ordering)
