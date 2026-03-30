# REDDIT.md — API Map & Software-Specific SOP

## Overview
- **Site**: reddit.com
- **Protocol**: REST JSON API (public: `.json` suffix, authenticated: OAuth via `oauth.reddit.com`)
- **Auth**: Optional — public read-only access without login, full CRUD with login
- **HTTP Client**: `curl_cffi` with `impersonate='chrome'` (Reddit blocks plain httpx)
- **Site Profile**: Optional-auth + Read/Write (read-only without auth, full CRUD with auth)

## API Bases
- **Public**: `https://www.reddit.com` with `.json` suffix
- **OAuth**: `https://oauth.reddit.com` with `Bearer {token_v2}` header

## Auth
- Login via Python Playwright (`auth login` command)
- Token stored at `~/.config/cli-web-reddit/auth.json`
- Bearer token extracted from `token_v2` cookie
- Env var override: `CLI_WEB_REDDIT_AUTH_JSON`

## Data Model

### Post (t3)
- `id`, `name` (fullname like t3_xxx), `title`, `author`, `subreddit`
- `score`, `upvote_ratio`, `num_comments`, `created_utc`
- `url`, `permalink`, `selftext`, `thumbnail`
- `is_self`, `over_18`, `stickied`, `locked`
- `link_flair_text`, `author_flair_text`

### Comment (t1)
- `id`, `author`, `body`, `score`, `created_utc`
- `parent_id`, `depth`, `is_submitter`
- `replies` (nested Listing)

### Subreddit (t5)
- `display_name`, `title`, `public_description`
- `subscribers`, `active_user_count`, `created_utc`
- `over18`, `subreddit_type`

### User (t2)
- `name`, `link_karma`, `comment_karma`, `created_utc`
- `is_gold`, `is_mod`, `has_verified_email`

## Endpoints

### Feed (global) — public
| Command | Endpoint | Params |
|---------|----------|--------|
| `feed hot` | `/hot/.json` | `limit`, `after` |
| `feed new` | `/new/.json` | `limit`, `after` |
| `feed top` | `/top/.json` | `limit`, `after`, `t` |
| `feed rising` | `/rising/.json` | `limit`, `after` |
| `feed popular` | `/r/popular/.json` | `limit`, `after` |

### Subreddit — public + auth
| Command | Endpoint | Params |
|---------|----------|--------|
| `sub hot <name>` | `/r/{name}/.json` | `limit`, `after` |
| `sub new <name>` | `/r/{name}/new/.json` | `limit`, `after` |
| `sub top <name>` | `/r/{name}/top/.json` | `limit`, `after`, `t` |
| `sub info <name>` | `/r/{name}/about.json` | — |
| `sub rules <name>` | `/r/{name}/about/rules.json` | — |
| `sub search <name>` | `/r/{name}/search.json` | `q`, `restrict_sr=on`, `limit`, `sort` |
| `sub join <name>` | `POST /api/subscribe` (OAuth) | `sr_name`, `action=sub` |
| `sub leave <name>` | `POST /api/subscribe` (OAuth) | `sr_name`, `action=unsub` |

### Search — public
| Command | Endpoint | Params |
|---------|----------|--------|
| `search posts <query>` | `/search.json` | `q`, `limit`, `sort`, `t`, `after` |
| `search subs <query>` | `/subreddits/search.json` | `q`, `limit`, `after` |

### User — public
| Command | Endpoint | Params |
|---------|----------|--------|
| `user info <name>` | `/user/{name}/about.json` | — |
| `user posts <name>` | `/user/{name}/submitted.json` | `limit`, `after`, `sort`, `t` |
| `user comments <name>` | `/user/{name}/comments.json` | `limit`, `after`, `sort`, `t` |

### Post — public
| Command | Endpoint | Params |
|---------|----------|--------|
| `post get <permalink>` | `/{permalink}.json` | `limit`, `depth` (comments) |

Deep comment expansion: automatically fetches collapsed "more" objects via
`/api/morechildren.json` and "continue this thread" chains via
`/comments/{id}/_/{comment_id}.json`. No comments are silently dropped.

### Auth — CLI only
| Command | Description |
|---------|-------------|
| `auth login` | Browser login via Playwright |
| `auth logout` | Remove saved credentials |
| `auth status` | Verify login + show username |

### Me — OAuth (requires auth)
| Command | Endpoint | Params |
|---------|----------|--------|
| `me profile` | `GET /api/v1/me` | — |
| `me saved` | `GET /user/{me}/saved` | `limit`, `after` |
| `me upvoted` | `GET /user/{me}/upvoted` | `limit`, `after` |
| `me subscriptions` | `GET /subreddits/mine/subscriber` | `limit`, `after` |
| `me inbox` | `GET /message/inbox` | `limit`, `after` |

### Vote — OAuth (requires auth)
| Command | Endpoint | Params |
|---------|----------|--------|
| `vote up <id>` | `POST /api/vote` | `id`, `dir=1` |
| `vote down <id>` | `POST /api/vote` | `id`, `dir=-1` |
| `vote unvote <id>` | `POST /api/vote` | `id`, `dir=0` |

### Submit — OAuth (requires auth)
| Command | Endpoint | Params |
|---------|----------|--------|
| `submit flairs <sub>` | `GET /r/{sub}/api/link_flair_v2` | — |
| `submit text <sub> <title> <body> [--flair ID]` | `POST /api/submit` | `sr`, `kind=self`, `title`, `text`, `flair_id` |
| `submit link <sub> <title> <url> [--flair ID]` | `POST /api/submit` | `sr`, `kind=link`, `title`, `url`, `flair_id` |

### Comment — OAuth (requires auth)
| Command | Endpoint | Params |
|---------|----------|--------|
| `comment add <id> <text>` | `POST /api/comment` | `thing_id`, `text` |
| `comment edit <id> <text>` | `POST /api/editusertext` | `thing_id`, `text` |
| `comment delete <id>` | `POST /api/del` | `id` |

### Saved — OAuth (requires auth)
| Command | Endpoint | Params |
|---------|----------|--------|
| `saved save <id>` | `POST /api/save` | `id` |
| `saved unsave <id>` | `POST /api/unsave` | `id` |

## CLI Command Structure
```
cli-web-reddit
├── feed          # Global feeds (hot, new, top, rising, popular)
├── sub           # Subreddit operations (hot, new, top, info, rules, search, join, leave)
├── search        # Search posts and subreddits
├── user          # User profiles and activity
├── post          # Post detail with comments
├── auth          # Login, logout, status
├── me            # Own profile, saved, upvoted, subscriptions, inbox
├── vote          # Upvote, downvote, unvote
├── submit        # Submit text or link posts
├── comment       # Comment, edit, delete
└── saved         # Save and unsave posts
```

## Pagination
- `limit`: 1-100 (default 25)
- `after`: fullname cursor (e.g., `t3_abc123`)

## Sort/Time Options
- Sort: `hot`, `new`, `top`, `rising`, `controversial`
- Time (`t`): `hour`, `day`, `week`, `month`, `year`, `all`
- Search sort: `relevance`, `hot`, `top`, `new`, `comments`
