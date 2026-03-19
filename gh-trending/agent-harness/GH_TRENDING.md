# GITHUB.md — GitHub Trending API Map

## Site Overview

**URL:** https://github.com/trending
**Type:** SSR (server-side rendered HTML — Ruby on Rails)
**Auth required:** No (public data) — read-only site
**Protocol:** HTTP GET with query parameters; response is HTML (BeautifulSoup4 scraping)

## Endpoints

### Trending Repositories

```
GET https://github.com/trending
GET https://github.com/trending?language={language}&since={since}&spoken_language_code={spoken}
```

**Query Parameters:**
| Param | Type | Values | Description |
|-------|------|--------|-------------|
| `language` | string | `python`, `javascript`, `typescript`, `rust`, `go`, etc. | Filter by programming language |
| `since` | string | `daily` (default), `weekly`, `monthly` | Time range |
| `spoken_language_code` | string | ISO 639-1 codes: `en`, `zh`, `es`, etc. | Filter by spoken language |

**Response:** HTML page with `article.Box-row` elements

**HTML Selectors — Repository:**
```
article.Box-row
  h2 a[href]              → /{owner}/{name}
  p                       → description text
  [itemprop="programmingLanguage"] → language name
  a[href*="/stargazers"]  → total stars (e.g., "4,859")
  a[href*="/forks"]       → total forks (e.g., "366")
  .float-sm-right         → stars today (e.g., "1,394 stars today")
  .Link--muted img[alt]   → contributor avatars (built by)
```

### Trending Developers

```
GET https://github.com/trending/developers
GET https://github.com/trending/developers?language={language}&since={since}
```

**Query Parameters:**
| Param | Type | Values | Description |
|-------|------|--------|-------------|
| `language` | string | Same as repos | Filter by programming language |
| `since` | string | `daily`, `weekly`, `monthly` | Time range |

**Response:** HTML page with `article.Box-row.d-flex` elements

**HTML Selectors — Developer:**
```
article.Box-row.d-flex
  a[href^="#pa-"]         → rank number (1-25)
  img[class*="avatar"]    → avatar URL
  h1 a[href]              → /{login} (profile URL)
  h1 a text               → display name
  p.f4 a[href]            → /{login} (username link)
  p.f4 a text             → username/login
  article a[href]         → popular repo path
  article a text          → popular repo name
  article p               → popular repo description
```

## Data Models

### TrendingRepo
```python
@dataclass
class TrendingRepo:
    owner: str           # e.g., "langchain-ai"
    name: str            # e.g., "open-swe"
    full_name: str       # e.g., "langchain-ai/open-swe"
    description: str     # e.g., "An Open-Source Asynchronous Coding Agent"
    language: str | None # e.g., "Python" (None if not shown)
    stars: int           # Total stars
    forks: int           # Total forks
    stars_today: int     # Stars gained in the period
    url: str             # Full GitHub URL
    rank: int            # Position in trending list (1-25)
```

### TrendingDeveloper
```python
@dataclass
class TrendingDeveloper:
    login: str           # e.g., "njbrake"
    name: str | None     # e.g., "Nathan Brake"
    rank: int            # Position (1-25)
    avatar_url: str      # Avatar image URL
    profile_url: str     # e.g., "https://github.com/njbrake"
    popular_repo: str | None     # e.g., "njbrake/agent-of-empires"
    popular_repo_desc: str | None  # Popular repo description
```

## Auth Scheme

**Authentication:** Not required for public trending data.

Optional session (for future features like starring):
- Storage: `~/.config/cli-web-github/auth.json` (chmod 600)
- Format: playwright-cli storage state (cookies + localStorage)
- Login: `cli-web-github auth login` → opens browser → user logs in → saves state

## CLI Commands

### repos list
```
cli-web-github repos list [OPTIONS]
```
Options:
- `--language TEXT` — Filter by programming language (e.g., python, javascript)
- `--since [daily|weekly|monthly]` — Time range (default: daily)
- `--spoken-language TEXT` — Filter by spoken language (ISO 639-1 code)
- `--json` — Output JSON instead of table

### developers list
```
cli-web-github developers list [OPTIONS]
```
Options:
- `--language TEXT` — Filter by programming language
- `--since [daily|weekly|monthly]` — Time range (default: daily)
- `--json` — Output JSON instead of table

## Rate Limiting

GitHub does not expose an official trending API and may rate-limit scrapers.
- Use `time.sleep()` between requests if making many calls
- Respect HTTP 429 responses with exponential backoff
- Default: no retries (single request)
