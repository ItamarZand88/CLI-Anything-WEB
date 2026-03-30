# cli-web-reddit

CLI for Reddit browsing and search. Browse feeds, subreddits, search posts, view user profiles, and read comments — all from the command line.

## Installation

```bash
cd reddit/agent-harness
pip install -e .
```

## Quick Start

```bash
# Hot posts on the front page
cli-web-reddit feed hot --limit 10

# Top posts this week
cli-web-reddit feed top --time week --json

# Browse a subreddit
cli-web-reddit sub hot python --limit 10

# Subreddit info
cli-web-reddit sub info programming --json

# Search posts
cli-web-reddit search posts "machine learning" --sort top --json

# Search subreddits
cli-web-reddit search subs "python" --json

# User profile
cli-web-reddit user info spez --json

# Post detail with comments (auto-expands deeply nested threads)
cli-web-reddit post get https://www.reddit.com/r/python/comments/abc123/my_post/ --json

# Interactive REPL mode
cli-web-reddit
```

## Commands

| Group | Command | Description |
|-------|---------|-------------|
| `feed` | `hot`, `new`, `top`, `rising`, `popular` | Global Reddit feeds |
| `sub` | `hot`, `new`, `top`, `info`, `rules`, `search` | Subreddit operations |
| `search` | `posts`, `subs` | Search posts and subreddits |
| `user` | `info`, `posts`, `comments` | User profiles and activity |
| `post` | `get` | Post detail with comments (auto-expands deep threads) |
| `vote` | `up`, `down`, `unvote` | Vote on posts/comments (auth required) |
| `submit` | `text`, `link` | Submit new posts (auth required) |
| `comment` | `add`, `edit`, `delete` | Comment on posts (auth required) |
| `saved` | `save`, `unsave` | Save/unsave items (auth required) |
| `me` | `profile`, `saved`, `upvoted`, `subscriptions`, `inbox` | Authenticated user data (auth required) |
| `auth` | `login`, `logout`, `status` | OAuth authentication management |

All commands support `--json` for structured output and `--limit N` for pagination.

## Notes

- **Reading is public** — feeds, subreddits, search, and user profiles work without auth
- **Writing requires auth** — vote, comment, submit, save, and inbox commands need OAuth login (`cli-web-reddit auth login`)
- Uses `curl_cffi` with Chrome impersonation (Reddit blocks plain HTTP clients)
- Pagination via `--after` cursor (shown in output)
- Time filters: `hour`, `day`, `week`, `month`, `year`, `all`
