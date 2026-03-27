# HACKERNEWS.md — API Map & Data Model

## Site Profile
- **Type**: Read-only (public) + auth-enabled write actions
- **Protocol**: REST JSON API (Firebase + Algolia) + HN web forms (auth actions)
- **HTTP Client**: httpx (no anti-bot protection)
- **Auth**: Cookie-based (`user` cookie from news.ycombinator.com)

## Authentication

HN uses a `user` cookie for auth (format: `username&hash`).
- **Login**: POST `/login` with `acct` + `pw` → sets `user` cookie
- **CSRF**: Write operations need auth tokens scraped from page HTML
- **Submit**: Requires `fnid` from `/submit` page, POST to `/r`
- **Comment**: Requires `hmac` from item page, POST to `/comment`
- **Vote/Fave/Hide**: GET requests with `auth=` token from page HTML
- **Config dir**: `~/.config/cli-web-hackernews/auth.json`
- **Env var**: `CLI_WEB_HACKERNEWS_AUTH_JSON`

## API Endpoints

### Firebase API (`hacker-news.firebaseio.com/v0`) — Public

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/topstories.json` | Top 500 story IDs (ranked) |
| GET | `/newstories.json` | Newest 500 story IDs |
| GET | `/beststories.json` | Best 500 story IDs |
| GET | `/askstories.json` | Ask HN story IDs |
| GET | `/showstories.json` | Show HN story IDs |
| GET | `/jobstories.json` | Job story IDs |
| GET | `/item/{id}.json` | Single item (story/comment/job/poll) |
| GET | `/user/{username}.json` | User profile |
| GET | `/maxitem.json` | Current max item ID |
| GET | `/updates.json` | Recently changed items/profiles |

### Algolia Search API (`hn.algolia.com/api/v1`) — Public

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/search?query=X&tags=story` | Search by relevance |
| GET | `/search_by_date?query=X` | Search by date |

**Params**: `query`, `tags` (story/comment/ask_hn/show_hn), `hitsPerPage`, `page`, `numericFilters`

### HN Web Endpoints (`news.ycombinator.com`) — Auth Required

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | Login (acct + pw) → sets user cookie |
| GET | `/vote?id=X&how=up&auth=Y` | Upvote story/comment |
| POST | `/r` | Submit story (fnid + fnop + title + url/text) |
| POST | `/comment` | Post comment (parent + hmac + text) |
| GET | `/fave?id=X&auth=Y` | Favorite/save a story |
| GET | `/hide?id=X&auth=Y` | Hide a story |
| GET | `/favorites?id=USERNAME` | View user's favorites (HTML) |
| GET | `/submitted?id=USERNAME` | View user's submissions (HTML) |
| GET | `/threads?id=USERNAME` | View comment replies/threads (HTML) |

## Data Models

### Story
`id`, `title`, `url`, `score`, `by`, `time`, `descendants`, `type`
Computed: `age` (human-readable), `domain` (extracted from URL)

### Comment
`id`, `by`, `text`, `time`, `parent`, `kids[]`, `dead`, `deleted`
Computed: `text_plain` (HTML stripped), `age`

### User
`id`, `karma`, `created`, `about`, `submitted[]`
Computed: `about_plain`, `member_since`, `total_submissions`

### SearchResult
`objectID`, `title`, `url`, `author`, `points`, `num_comments`, `created_at`, `story_id`

## CLI Commands

### Read-Only (no auth)

| Command | Description |
|---------|-------------|
| `stories top [-n N] [--json]` | Front page stories |
| `stories new [-n N] [--json]` | Newest stories |
| `stories best [-n N] [--json]` | Best stories |
| `stories ask [-n N] [--json]` | Ask HN |
| `stories show [-n N] [--json]` | Show HN |
| `stories jobs [-n N] [--json]` | Job listings |
| `stories view ID [-n N] [--json]` | View story + comments |
| `search stories QUERY [-n N] [--sort-date] [--json]` | Search stories |
| `search comments QUERY [-n N] [--sort-date] [--json]` | Search comments |
| `user view USERNAME [--json]` | User profile |

### Auth-Enabled (requires login)

| Command | Description |
|---------|-------------|
| `auth login -u USER -p PASS` | Login with credentials |
| `auth login-browser` | Login via browser window |
| `auth status [--json]` | Check login status |
| `auth logout` | Remove stored credentials |
| `upvote ID [--json]` | Upvote a story or comment |
| `submit -t TITLE [-u URL] [--text TEXT] [--json]` | Submit a new story |
| `comment PARENT_ID TEXT [--json]` | Post a comment or reply |
| `favorite ID [--json]` | Favorite/save a story |
| `hide ID [--json]` | Hide a story from feed |
| `user favorites [USERNAME] [-n N] [--json]` | View favorite stories |
| `user submissions [USERNAME] [-n N] [--json]` | View submitted stories |
| `user threads [USERNAME] [-n N] [--json]` | View comment replies/threads |

## Performance Notes
- Story feeds return IDs only; items fetched in parallel via asyncio
- Default limit: 30 stories per feed, 10 comments per view, 20 search results
- No rate limiting observed on Firebase API (generous limits)
- Algolia has rate limits but very generous for read-only use
- Auth actions scrape page HTML for CSRF tokens (2 requests per action)
